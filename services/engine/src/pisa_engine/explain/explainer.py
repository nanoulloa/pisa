"""The explainer interface and the Muse Spark explainer.

Muse Spark gets the facts, never the video, and writes two or three sentences in the job's
language. A text with a number that is not a fact is thrown away; the client then shows its
own templated copy, which exists in every language.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from typing import Any, Protocol

from pisa_contracts import DataPolicy, Explanation, Locale, Plan, TestResult, Verdict
from pisa_engine.explain.facts import explanation_facts, unsupported_numbers
from pisa_engine.model_api.client import MetaModelApiClient
from pisa_engine.model_api.pricing import token_cost_usd
from pisa_engine.model_api.responses import json_schema_format, output_text

logger = logging.getLogger(__name__)

LANGUAGES: dict[Locale, str] = {
    "en": "English",
    "es": "Latin American Spanish, with a decimal comma",
    "zh-CN": "Simplified Chinese",
    "pt-BR": "Brazilian Portuguese, with a decimal comma",
}

INSTRUCTIONS = """\
You write the short explanation shown under a verdict in Pisa, which checks whether the \
motion in a viral video is physically possible by measuring it. Write for someone who got \
the video in a family chat: two or three short sentences, plain words, no jargon (no test \
names or codes, no "restitution", "residual" or "BIC").

The verdict is already decided from the measurements. Explain it; never change, soften or \
strengthen it. Say what the motion does and whether real physics allows it; do not claim \
the video is fake or real. For an inconclusive verdict, say why it could not be measured.

Use only the facts given. Write every number with digits, and only numbers that appear in \
the facts, rounded as given or more coarsely. A count means only what its name says: a \
flight phase is one stretch of free flight between release, bounces and landing, so a ball \
that bounces twice has three. When a test passes, say in words that the motion matches real \
physics. No other numbers, no emoji, no exclamation marks, no dashes between clauses.
"""

MAX_OUTPUT_TOKENS = 1000
MAX_TEXT_CHARS = 600
_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["text"],
    "properties": {"text": {"type": "string", "description": "The explanation."}},
}


class Explainer(Protocol):
    async def explain(
        self,
        verdict: Verdict,
        results: Sequence[TestResult],
        plan: Plan,
        *,
        locale: Locale,
        policy: DataPolicy,
    ) -> Explanation | None: ...


class NoExplainer:
    """Offline: no explanation, so clients use their templated copy."""

    async def explain(
        self,
        verdict: Verdict,
        results: Sequence[TestResult],
        plan: Plan,
        *,
        locale: Locale,
        policy: DataPolicy,
    ) -> Explanation | None:
        return None


class MuseSparkExplainer:
    def __init__(
        self,
        client: MetaModelApiClient,
        *,
        model: str = "muse-spark-1.3",
        contributor_model: str = "muse-spark-1.3-contributor",
    ) -> None:
        self._client = client
        self._model = model
        self._contributor_model = contributor_model

    async def explain(
        self,
        verdict: Verdict,
        results: Sequence[TestResult],
        plan: Plan,
        *,
        locale: Locale,
        policy: DataPolicy,
    ) -> Explanation | None:
        facts = explanation_facts(verdict, results, plan)
        model = self._contributor_model if policy == "internal" else self._model
        body = self._request(model, facts, locale)
        # A token is at least one byte, so the request's size bounds its input tokens.
        input_bound = len(json.dumps(body, ensure_ascii=False).encode())
        payload = await self._client.create_response(
            body,
            policy=policy,
            worst_case_usd=token_cost_usd(model, input_bound, MAX_OUTPUT_TOKENS),
            stage="explain",
        )
        text = _tidy(str(json.loads(output_text(payload)).get("text", "")))
        unsupported = unsupported_numbers(text, facts, locale)
        if not text or len(text) > MAX_TEXT_CHARS or unsupported:
            logger.warning(
                "Explanation rejected",
                extra={"stage": "explain", "chars": len(text), "unsupported": unsupported},
            )
            return None
        return Explanation(locale=locale, text=text, model=model)

    def _request(self, model: str, facts: dict[str, Any], locale: Locale) -> dict[str, Any]:
        prompt = f"Write the explanation in {LANGUAGES[locale]}.\n\nFacts:\n" + json.dumps(
            facts, ensure_ascii=False, indent=1
        )
        return {
            "model": model,
            "instructions": INSTRUCTIONS,
            "input": prompt,
            "text": {"format": json_schema_format("explanation", _SCHEMA)},
            "reasoning": {"effort": "minimal"},
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "store": False,
        }


def _tidy(text: str) -> str:
    """Our copy uses no em or en dashes between clauses."""
    for dash in (" \u2014 ", "\u2014", " \u2013 "):  # Em dash, and en dash between clauses.
        text = text.replace(dash, ", ")
    return " ".join(text.split())
