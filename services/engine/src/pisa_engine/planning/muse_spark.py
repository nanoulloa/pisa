"""The planner on Muse Spark 1.3: native video input and structured output.

One upload (deleted when the call ends), then one Responses call whose answer must match
the `Plan` contract. The video is sampled at a few frames per second; before paying, the
request's input tokens are counted so the spend guard can hold the true worst case.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any

from pisa_contracts import DataPolicy, IngestResult, Plan
from pisa_engine.model_api.client import MetaModelApiClient
from pisa_engine.model_api.pricing import token_cost_usd
from pisa_engine.model_api.responses import ModelOutputError, json_schema_format, output_text
from pisa_engine.planning.planner import checked, strict_schema

logger = logging.getLogger(__name__)

INSTRUCTIONS = """\
You plan a physics measurement of a video. Pisa tracks objects that move freely under \
gravity and checks their motion against the laws of mechanics. Your job is only to say what \
moves freely, when, and what has a known size. Never judge whether the video is real, \
generated or edited.

Events. List each stretch of time in which one or two objects move under gravity alone:
- fall: an object let go from rest;
- throw: an object launched by a hand, foot or tool;
- bounce: an object that falls and bounces off the ground one or more times (the bounces \
belong to the event);
- pair_drop: two objects let go together, side by side.
start_s is the first moment nothing holds or pushes the object. end_s is the last moment \
before it is caught, comes to rest, leaves the frame or is hidden. Times are seconds from \
the start of the clip. When unsure, choose a window slightly inside the free motion rather \
than one that includes a hand, a catch or a landing. Objects that fly under their own power \
or are carried (birds, drones, cars, people walking) are not events.

Object phrases. For each event, give one short noun phrase per kind of moving object, as \
an open-vocabulary segmenter would need it: 1 to 3 words, concrete and visual ("tennis \
ball", "red apple", "glass bottle"). Two identical objects share one phrase; two different \
objects get one phrase each, distinct enough to tell them apart ("red ball", "blue ball").

References. List up to three objects of known real size close to the plane of the motion, \
to convert pixels to meters. Prefer the moving object itself when its size is standard (a \
tennis ball is 0.065 to 0.069 m across). Give an honest range in meters for the dimension \
you name; leave the list empty when nothing has a reliable size.

Camera. motion is static, handheld, pan or unknown. has_cuts is true when the clip jumps \
between shots. slow_motion_suspected is true when cues other than the moving objects \
suggest slowed playback: water, smoke, fire, hair or people moving unnaturally slowly, or \
an on-screen slow-motion label.

When no event qualifies, set measurable to false, events to an empty list, and reason to \
no_free_flight (nothing moves freely) or too_unclear (something does, but it is too small, \
blurred, hidden, brief or cut to follow). Otherwise set measurable to true and reason to null.
"""

# The video is sampled at up to this rate; the planner's times are only as precise as that.
MAX_SAMPLE_FPS = 8.0
# Long clips are sampled more sparsely so the frames sent stay bounded.
MAX_SAMPLED_FRAMES = 240
MAX_OUTPUT_TOKENS = 4000
# Headroom over the counted input tokens when holding the worst case.
INPUT_TOKEN_MARGIN = 1.2


class MuseSparkPlanner:
    def __init__(
        self,
        client: MetaModelApiClient,
        *,
        model: str = "muse-spark-1.3",
        contributor_model: str = "muse-spark-1.3-contributor",
        reasoning_effort: str = "low",
    ) -> None:
        self._client = client
        self._model = model
        self._contributor_model = contributor_model
        self._effort = reasoning_effort

    async def plan(self, video: Path, ingest: IngestResult, *, policy: DataPolicy) -> Plan:
        duration, fps, sample_fps = sampling(ingest)
        # Only internal test clips may use the contributor tier (Meta may train on its inputs).
        model = self._contributor_model if policy == "internal" else self._model

        async with self._client.uploaded(video) as file_id:
            body = self._request(model, file_id, duration=duration, fps=fps, sample_fps=sample_fps)
            input_tokens = await self._client.count_input_tokens(body, policy=policy)
            worst_case = token_cost_usd(
                model, math.ceil(input_tokens * INPUT_TOKEN_MARGIN), MAX_OUTPUT_TOKENS
            )
            payload = await self._client.create_response(
                body, policy=policy, worst_case_usd=worst_case, stage="plan"
            )
        plan = parse_plan(payload)
        logger.info(
            "Plan received",
            extra={"stage": "plan", "events": len(plan.events), "input_tokens": input_tokens},
        )
        # Half a sampling interval inside each end keeps hands and landings out of the window.
        return checked(plan, ingest, margin_s=0.5 / sample_fps)

    def _request(
        self, model: str, file_id: str, *, duration: float, fps: float, sample_fps: float
    ) -> dict[str, Any]:
        prompt = (
            f"Plan the measurement for this clip. It lasts {duration:.2f} s at "
            f"{fps:.3g} frames per second; you see it at {sample_fps:.3g} frames per second."
        )
        return {
            "model": model,
            "instructions": INSTRUCTIONS,
            "input": [
                {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_video", "file_id": file_id, "fps": round(sample_fps, 3)},
                    ],
                }
            ],
            "text": {"format": json_schema_format("plan", strict_schema("Plan"))},
            "reasoning": {"effort": self._effort},
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "store": False,
        }


def sampling(ingest: IngestResult) -> tuple[float, float, float]:
    """The clip's duration and frame rate, and the rate Muse Spark sees it at."""
    timebase = ingest.timebase
    duration = timebase.frame_count * timebase.fps_den / timebase.fps_num
    fps = timebase.fps_num / timebase.fps_den
    return duration, fps, min(MAX_SAMPLE_FPS, fps, MAX_SAMPLED_FRAMES / max(duration, 1e-6))


def parse_plan(payload: dict[str, Any]) -> Plan:
    text = output_text(payload)
    try:
        return Plan.model_validate(json.loads(text))
    except ValueError as error:  # Invalid JSON or a plan outside the contract.
        raise ModelOutputError(f"the plan does not match the contract: {error}") from error
