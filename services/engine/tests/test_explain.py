"""The explainer: which facts it gets, how numbers are read in each language, and the check."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

import pisa_contracts as contracts
from pisa_contracts import Locale, Plan, Verdict
from pisa_engine.explain.explainer import MuseSparkExplainer
from pisa_engine.explain.facts import explanation_facts, numbers_in, unsupported_numbers
from pisa_engine.model_api.client import MetaModelApiClient
from pisa_engine.model_api.spend import InMemorySpendLedger, SpendGuard
from pisa_engine.physics.results import measurement, result

pytestmark = pytest.mark.anyio

VERDICT = Verdict(
    label="physically_impossible",
    policy_version="0.1.0",
    decisive_tests=["galileo_pair"],
    reason_code=None,
)
PLAN = Plan.model_validate(
    {
        "measurable": True,
        "reason": None,
        "events": [
            {"type": "pair_drop", "start_s": 0.1, "end_s": 0.7, "object_phrases": ["red ball"]}
        ],
        "references": [],
        "camera": {"motion": "static", "has_cuts": False, "slow_motion_suspected": False},
    }
)
RESULTS = [
    result(
        "free_fall_shape",
        "pass",
        1.0,
        [measurement("acceleration_px_s2", 3924.0, "px/s^2"), measurement("samples", 36, "1")],
    ),
    result(
        "galileo_pair",
        "violation",
        1.0,
        [measurement("acceleration_ratio", 1 / 1.6354, "1"), measurement("z_score", 639.4, "1")],
        "pair_falls_apart",
    ),
    result("bounce_energy", "pass", 1.0, [measurement("restitution", 0.7012, "1")]),
    result(
        "implied_g",
        "violation",
        0.9,
        [
            measurement("implied_g", 1.618, "m/s^2", (1.52, 1.71)),
            measurement("earth_g_ratio", 6.063, "1"),
        ],
        "gravity_too_weak",
    ),
]


def test_facts_hold_what_people_understand_and_no_pixels() -> None:
    facts = explanation_facts(VERDICT, RESULTS, PLAN)
    text = json.dumps(facts)
    assert "px" not in text
    assert "3924" not in text  # Pixel accelerations mean nothing to a reader.
    assert "639" not in text  # Nor do standard scores.
    by_test = {t["test"]: t for t in facts["tests"]}
    assert by_test["galileo_pair"]["acceleration_ratio"] == 1.64  # Always the larger over smaller.
    assert by_test["bounce_energy"]["speed_kept_after_bounce_percent"] == 70
    assert by_test["implied_g"]["gravity_m_s2"] == 1.6
    assert by_test["implied_g"]["times_weaker_than_earth"] == 6.1
    assert "red ball" not in text  # No free text from the planner reaches the explainer.
    assert facts["constants"]["earth_gravity_m_s2"] == 9.81


@pytest.mark.parametrize(
    ("locale", "text", "numbers"),
    [
        ("en", "It falls 1.64 times faster, at 3,921 px/s².", [(1.64, 2), (3921.0, 0)]),
        ("es", "Cae 1,64 veces más rápido, a 3.921 px/s².", [(1.64, 2), (3921.0, 0)]),
        ("pt-BR", "Conserva 70% da velocidade.", [(70.0, 0)]),
        ("zh-CN", "重力只有地球的 1.6 倍之一。", [(1.6, 1)]),
        ("es", "La gravedad es 9.81 aquí.", [(9.81, 2)]),  # An English decimal in Spanish text.
    ],
)
def test_numbers_are_read_in_the_conventions_of_each_language(
    locale: Locale, text: str, numbers: list[tuple[float, int]]
) -> None:
    assert numbers_in(text, locale) == numbers


def test_only_facts_pass_rounded_no_finer_than_given() -> None:
    facts = explanation_facts(VERDICT, RESULTS, PLAN)
    ok = "Una cae 1,64 veces más rápido que la otra: unas 1,6 veces, casi 2. En la Tierra, 9,81."
    assert unsupported_numbers(ok, facts, "es") == []
    assert (
        unsupported_numbers("Conserva el 70 % de su velocidad, nunca más del 100 %.", facts, "es")
        == []
    )
    assert unsupported_numbers("It falls 1.9 times faster.", facts, "en") == [1.9]
    assert unsupported_numbers("A 5 meter drop.", facts, "en") == [5.0]


def _answer(text: str) -> dict[str, Any]:
    return {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": json.dumps({"text": text})}],
            }
        ],
        "usage": {"input_tokens": 700, "output_tokens": 90},
    }


def _explainer(text: str) -> tuple[MuseSparkExplainer, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=_answer(text))

    client = MetaModelApiClient(
        api_key=SecretStr("LLM_000_not-a-real-key"),
        base_url="https://api.meta.ai/v1",
        guard=SpendGuard(enabled=True, cap_usd=1.0, ledger=InMemorySpendLedger()),
        transport=httpx.MockTransport(respond),
    )
    return MuseSparkExplainer(client), requests


async def _explain(
    text: str, locale: Locale = "es", results: list[contracts.TestResult] = RESULTS
) -> Any:
    explainer, requests = _explainer(text)
    explanation = await explainer.explain(VERDICT, results, PLAN, locale=locale, policy="user")
    return explanation, requests


async def test_a_faithful_explanation_is_kept() -> None:
    text = "Dos pelotas soltadas juntas caen distinto: una acelera 1,64 veces más que la otra."
    explanation, (request,) = await _explain(text)
    assert explanation is not None
    assert (explanation.locale, explanation.text, explanation.model) == (
        "es",
        text,
        "muse-spark-1.3",
    )
    body = json.loads(request.content)
    assert body["model"] == "muse-spark-1.3"
    assert body["reasoning"] == {"effort": "minimal"}
    assert body["text"]["format"]["strict"] is True
    assert body["store"] is False
    assert "Latin American Spanish" in body["input"]
    assert "input_video" not in request.content.decode()  # Facts only, never the video.


async def test_an_explanation_with_a_made_up_number_is_thrown_away() -> None:
    explanation, _ = await _explain("Una pelota cae 3 veces más rápido que la otra.")
    assert explanation is None


async def test_dashes_between_clauses_become_commas() -> None:
    explanation, _ = await _explain("Caen distinto — una acelera 1,64 veces más.")
    assert explanation is not None
    assert explanation.text == "Caen distinto, una acelera 1,64 veces más."
