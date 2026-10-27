"""The baseline: ask Muse Spark whether a clip is real or AI-generated, and compare its opinion
with Pisa's measurements.

The question is asked the way a person would ask a chatbot, with nothing about physics, so
the comparison is between an opinion and a measurement. The answer is structured (real,
generated or unsure, and one sentence why) only so it can be scored. The video goes in as
the planner sends it: the normalized clip, sampled at the same rate.

Like the run, the baseline saves each answer as soon as it has it, skips clips already
asked, and stops at the paid-calls switch.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict

from pisa_contracts import DataPolicy, EvalOpinion, IngestResult
from pisa_engine.evaluation.manifest import Manifest, clip_path
from pisa_engine.evaluation.runner import RunStoppedError
from pisa_engine.ingest.normalize import normalize
from pisa_engine.model_api import costs
from pisa_engine.model_api.client import MetaModelApiClient
from pisa_engine.model_api.pricing import token_cost_usd
from pisa_engine.model_api.responses import ModelOutputError, json_schema_format, output_text
from pisa_engine.model_api.spend import PaidCallsDisabledError, SpendCapExceededError
from pisa_engine.planning.muse_spark import INPUT_TOKEN_MARGIN, sampling

logger = logging.getLogger(__name__)

QUESTION = "Is this video real or AI-generated?"
INSTRUCTIONS = (
    "Answer the user's question about the video. Say real if it was filmed with a camera, "
    "generated if an AI model made it, or unsure if you cannot tell, and give one sentence "
    "of reasoning."
)
MAX_OUTPUT_TOKENS = 2000
_ANSWER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["answer", "reason"],
    "properties": {
        "answer": {"type": "string", "enum": ["real", "generated", "unsure"]},
        "reason": {"type": "string"},
    },
}


class Opinion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: EvalOpinion
    reason: str


class Baseline(Protocol):
    def model_for(self, policy: DataPolicy) -> str: ...

    async def ask(self, video: Path, ingest: IngestResult, *, policy: DataPolicy) -> Opinion: ...


class MuseSparkBaseline:
    def __init__(
        self,
        client: MetaModelApiClient,
        *,
        model: str = "muse-spark-1.3",
        contributor_model: str = "muse-spark-1.3-contributor",
        reasoning_effort: str = "medium",
    ) -> None:
        self._client = client
        self._model = model
        self._contributor_model = contributor_model
        # A fair baseline gets to think: more effort than the planner, which only lists events.
        self._effort = reasoning_effort

    def model_for(self, policy: DataPolicy) -> str:
        return self._contributor_model if policy == "internal" else self._model

    async def ask(self, video: Path, ingest: IngestResult, *, policy: DataPolicy) -> Opinion:
        _, _, sample_fps = sampling(ingest)
        model = self.model_for(policy)
        async with self._client.uploaded(video) as file_id:
            body = {
                "model": model,
                "instructions": INSTRUCTIONS,
                "input": [
                    {
                        "type": "message",
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": QUESTION},
                            {
                                "type": "input_video",
                                "file_id": file_id,
                                "fps": round(sample_fps, 3),
                            },
                        ],
                    }
                ],
                "text": {"format": json_schema_format("opinion", _ANSWER_SCHEMA)},
                "reasoning": {"effort": self._effort},
                "max_output_tokens": MAX_OUTPUT_TOKENS,
                "store": False,
            }
            input_tokens = await self._client.count_input_tokens(body, policy=policy)
            worst_case = token_cost_usd(
                model, math.ceil(input_tokens * INPUT_TOKEN_MARGIN), MAX_OUTPUT_TOKENS
            )
            payload = await self._client.create_response(
                body, policy=policy, worst_case_usd=worst_case, stage="baseline"
            )
        return parse_opinion(payload)


def parse_opinion(payload: dict[str, Any]) -> Opinion:
    try:
        return Opinion.model_validate(json.loads(output_text(payload)))
    except ValueError as error:
        raise ModelOutputError(f"the answer does not match the schema: {error}") from error


class BaselineRun(BaseModel):
    """One clip's answer, or why there is none. Failed calls count as unsure when scored."""

    model_config = ConfigDict(extra="forbid")

    clip_id: str
    model: str
    answer: EvalOpinion | None
    reason: str | None
    error: str | None
    cost_usd: float


async def run_baseline(
    manifest_path: Path,
    manifest: Manifest,
    out_dir: Path,
    baseline: Baseline,
    *,
    policy: DataPolicy,
    force: bool = False,
    progress: Callable[[str], None] = print,
) -> dict[str, BaselineRun]:
    missing = [c.file for c in manifest.clips if not clip_path(manifest_path, c).is_file()]
    if missing:
        raise FileNotFoundError(f"clips not found: {', '.join(missing)}")
    folder = out_dir / "baseline"
    folder.mkdir(parents=True, exist_ok=True)
    runs: dict[str, BaselineRun] = {}
    for index, clip in enumerate(manifest.clips, start=1):
        saved = folder / f"{clip.id}.json"
        if saved.exists() and not force:
            runs[clip.id] = BaselineRun.model_validate_json(saved.read_text(encoding="utf-8"))
            continue
        answer: Opinion | None = None
        error: str | None = None
        with costs.collecting() as spent, tempfile.TemporaryDirectory(prefix="pisa-eval-") as work:
            video = Path(work) / "normalized.mp4"
            try:
                ingest = await asyncio.to_thread(normalize, clip_path(manifest_path, clip), video)
                answer = await baseline.ask(video, ingest, policy=policy)
            except PaidCallsDisabledError as stop:
                raise RunStoppedError("paid_calls_disabled") from stop
            except SpendCapExceededError as stop:
                raise RunStoppedError("spend_cap_reached") from stop
            except Exception as failure:
                logger.warning("No baseline answer", exc_info=True, extra={"clip": clip.id})
                error = getattr(failure, "code", None) or type(failure).__name__
        run = BaselineRun(
            clip_id=clip.id,
            model=baseline.model_for(policy),
            answer=answer.answer if answer else None,
            reason=answer.reason if answer else None,
            error=error,
            cost_usd=round(sum(entry.usd for entry in spent), 6),
        )
        saved.write_text(run.model_dump_json(indent=1), encoding="utf-8")
        runs[clip.id] = run
        progress(f"[{index}/{len(manifest.clips)}] {clip.id}: {run.answer or run.error}")
    return runs


def load_baseline(out_dir: Path) -> dict[str, BaselineRun]:
    runs = {}
    for path in sorted((out_dir / "baseline").glob("*.json")):
        run = BaselineRun.model_validate_json(path.read_text(encoding="utf-8"))
        runs[run.clip_id] = run
    return runs
