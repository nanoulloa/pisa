"""The planner: plan checks, the strict output schema and the Muse Spark request, offline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from pisa_contracts import IngestResult, Plan, Timebase, VideoProbe
from pisa_engine.model_api import costs
from pisa_engine.model_api.client import MetaModelApiClient
from pisa_engine.model_api.responses import ModelOutputError
from pisa_engine.model_api.spend import InMemorySpendLedger, PaidCallsDisabledError, SpendGuard
from pisa_engine.planning.muse_spark import MuseSparkPlanner
from pisa_engine.planning.planner import WholeClipPlanner, checked, strict_schema

pytestmark = pytest.mark.anyio


def _ingest(duration_s: float = 2.0, fps: int = 60) -> IngestResult:
    probe = VideoProbe(
        width=640,
        height=960,
        duration_s=duration_s,
        fps_num=fps,
        fps_den=1,
        is_vfr=False,
        rotation_deg=0,
        frame_count=round(duration_s * fps),
        codec="h264",
        has_audio=False,
        size_bytes=10_000,
    )
    timebase = Timebase(fps_num=fps, fps_den=1, start_s=0.0, frame_count=round(duration_s * fps))
    return IngestResult(source=probe, normalized=probe, timebase=timebase, scene_cuts_s=[])


def _plan(**overrides: Any) -> Plan:
    plan: dict[str, Any] = {
        "measurable": True,
        "reason": None,
        "events": [
            {"type": "fall", "start_s": 0.5, "end_s": 1.5, "object_phrases": ["Tennis Ball."]}
        ],
        "references": [
            {"phrase": "tennis ball", "dimension": "diameter", "size_min_m": 0.065,
             "size_max_m": 0.069}
        ],
        "camera": {"motion": "handheld", "has_cuts": False, "slow_motion_suspected": False},
    }  # fmt: skip
    return Plan.model_validate({**plan, **overrides})


# Plan checks


def test_windows_are_clipped_and_pulled_inside_the_free_flight() -> None:
    plan = _plan(
        events=[
            {"type": "throw", "start_s": -0.2, "end_s": 0.9, "object_phrases": ["ball"]},
            {"type": "fall", "start_s": 1.2, "end_s": 9.0, "object_phrases": ["ball"]},
        ]
    )
    first, second = checked(plan, _ingest(2.0), margin_s=0.0625).events
    assert (first.start_s, first.end_s) == pytest.approx((0.0625, 0.8375))
    assert (second.start_s, second.end_s) == pytest.approx((1.2625, 1.9375))


def test_phrases_are_normalized_deduplicated_and_short() -> None:
    long_phrase = "the small round object that someone is about to drop"
    plan = _plan(
        events=[
            {
                "type": "pair_drop",
                "start_s": 0.2,
                "end_s": 1.0,
                "object_phrases": ["  Red  Ball ", "red ball", long_phrase, "blue ball"],
            }
        ]
    )
    (event,) = checked(plan, _ingest()).events
    assert event.object_phrases == ["red ball", "blue ball"]


def test_a_plan_whose_events_are_all_unusable_is_too_unclear() -> None:
    plan = _plan(events=[{"type": "fall", "start_s": 0.5, "end_s": 0.6, "object_phrases": ["x"]}])
    result = checked(plan, _ingest())
    assert (result.measurable, result.reason, result.events) == (False, "too_unclear", [])


def test_an_unmeasurable_plan_keeps_no_events() -> None:
    plan = _plan(measurable=False, reason=None)
    result = checked(plan, _ingest())
    assert (result.measurable, result.reason, result.events, result.references) == (
        False,
        "no_free_flight",
        [],
        [],
    )


def test_implausible_references_are_dropped() -> None:
    plan = _plan(
        references=[
            {"phrase": "door", "dimension": "height", "size_min_m": 2.1, "size_max_m": 1.9},
            {"phrase": "planet", "dimension": "diameter", "size_min_m": 1e6, "size_max_m": 2e6},
            {"phrase": "Door", "dimension": "height", "size_min_m": 1.9, "size_max_m": 2.2},
        ]
    )
    (reference,) = checked(plan, _ingest()).references
    assert (reference.phrase, reference.size_min_m) == ("door", 1.9)


async def test_the_offline_planner_covers_the_whole_clip(tmp_path: Path) -> None:
    plan = await WholeClipPlanner("ball").plan(tmp_path / "clip.mp4", _ingest(1.5), policy="user")
    (event,) = plan.events
    assert (event.start_s, event.end_s, event.object_phrases) == (0.0, 1.5, ["ball"])
    assert plan.references == []


# Structured output schema


def _strict_violations(node: Any, path: str = "$") -> list[str]:
    """Muse Spark's strict subset: closed objects, every key required, no oneOf or allOf."""
    problems: list[str] = []
    if isinstance(node, dict):
        if "oneOf" in node or "allOf" in node:
            problems.append(f"{path}: oneOf/allOf")
        if node.get("type") == "object":
            if node.get("additionalProperties") is not False:
                problems.append(f"{path}: not closed")
            if sorted(node.get("required", [])) != sorted(node.get("properties", {})):
                problems.append(f"{path}: not every key required")
        for key, value in node.items():
            problems.extend(_strict_violations(value, f"{path}.{key}"))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            problems.extend(_strict_violations(value, f"{path}[{index}]"))
    return problems


def test_the_plan_schema_is_inside_the_strict_subset() -> None:
    schema = strict_schema("Plan")
    assert _strict_violations(schema) == []
    assert schema["type"] == "object"
    assert "anyOf" not in schema
    assert set(schema["$defs"]) == {
        "PlanReason",
        "PlanEvent",
        "EventType",
        "ReferenceObject",
        "CameraNotes",
        "CameraMotion",
    }
    # Every reference resolves inside the schema itself.
    text = json.dumps(schema)
    for name in schema["$defs"]:
        assert f'"#/$defs/{name}"' in text


# Muse Spark planner


def _answer(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "completed",
        "output": [
            {"type": "reasoning", "id": "rs_1", "summary": []},
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": json.dumps(plan)}],
            },
        ],
        "usage": {"input_tokens": 9000, "output_tokens": 400},
    }


class FakeMetaApi:
    """Answers the four calls a plan makes, recording each request."""

    def __init__(self, answer: dict[str, Any], *, input_tokens: int = 9000) -> None:
        self.requests: list[httpx.Request] = []
        self._answer = answer
        self._input_tokens = input_tokens

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if request.method == "DELETE":
            return httpx.Response(200, json={"id": "file-7", "object": "file", "deleted": True})
        if path.endswith("/files"):
            return httpx.Response(200, json={"id": "file-7", "expires_at": 1793050000})
        if path.endswith("/responses/input_tokens"):
            return httpx.Response(
                200, json={"object": "response.input_tokens", "input_tokens": self._input_tokens}
            )
        return httpx.Response(200, json=self._answer)


def _planner(api: FakeMetaApi, *, enabled: bool = True) -> tuple[MuseSparkPlanner, SpendGuard]:
    guard = SpendGuard(enabled=enabled, cap_usd=1.0, ledger=InMemorySpendLedger())
    client = MetaModelApiClient(
        api_key=SecretStr("LLM_000_not-a-real-key"),
        base_url="https://api.meta.ai/v1",
        guard=guard,
        transport=httpx.MockTransport(api),
    )
    return MuseSparkPlanner(client), guard


async def test_muse_spark_planner_request_and_answer(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"\x00")
    api = FakeMetaApi(_answer(_plan().model_dump()))
    planner, guard = _planner(api)

    with costs.collecting() as spent:
        plan = await planner.plan(video, _ingest(2.0, fps=60), policy="user")

    upload, count, create, delete = api.requests
    assert upload.url.path == "/v1/files"
    body = json.loads(create.content)
    assert json.loads(count.content) == body  # The worst case is counted on the exact request.
    assert body["model"] == "muse-spark-1.3"  # A user's video never goes to the contributor tier.
    assert body["text"]["format"] == {
        "type": "json_schema",
        "name": "plan",
        "schema": strict_schema("Plan"),
        "strict": True,
    }
    assert body["reasoning"] == {"effort": "low"}
    assert body["store"] is False
    assert "Never judge whether the video is real" in body["instructions"]
    prompt, video_part = body["input"][0]["content"]
    assert video_part == {"type": "input_video", "file_id": "file-7", "fps": 8.0}
    assert "2.00 s at 60 frames per second" in prompt["text"]
    assert (delete.method, delete.url.path) == ("DELETE", "/v1/files/file-7")

    # Windows come back half a sampling interval (1/16 s) inside, phrases normalized.
    (event,) = plan.events
    assert (event.start_s, event.end_s) == pytest.approx((0.5625, 1.4375))
    assert event.object_phrases == ["tennis ball"]
    assert [(e.stage, e.unit, e.quantity) for e in spent] == [
        ("plan", "input_tokens", 9000),
        ("plan", "output_tokens", 400),
    ]
    assert guard.spent_usd() == pytest.approx(9000 * 1.25e-6 + 400 * 4.25e-6)


async def test_internal_clips_use_the_contributor_tier(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"\x00")
    api = FakeMetaApi(_answer(_plan().model_dump()))
    planner, _ = _planner(api)
    await planner.plan(video, _ingest(), policy="internal")
    assert json.loads(api.requests[2].content)["model"] == "muse-spark-1.3-contributor"


async def test_long_clips_are_sampled_more_sparsely(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"\x00")
    api = FakeMetaApi(_answer(_plan(events=[]).model_dump()))
    planner, _ = _planner(api)
    await planner.plan(video, _ingest(60.0, fps=30), policy="user")
    video_part = json.loads(api.requests[2].content)["input"][0]["content"][1]
    assert video_part["fps"] == 4.0  # 240 frames over 60 s.


async def test_nothing_is_sent_when_paid_calls_are_off(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"\x00")
    api = FakeMetaApi(_answer(_plan().model_dump()))
    planner, _ = _planner(api, enabled=False)
    with pytest.raises(PaidCallsDisabledError):
        await planner.plan(video, _ingest(), policy="user")
    assert api.requests == []


@pytest.mark.parametrize(
    "answer",
    [
        {"status": "completed", "output": [{"type": "message", "role": "assistant",
         "content": [{"type": "refusal", "refusal": "no"}]}]},
        {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"},
         "output": []},
        {"status": "completed", "output": [{"type": "message", "role": "assistant",
         "content": [{"type": "output_text", "text": '{"measurable": true}'}]}]},
    ],
)  # fmt: skip
async def test_unusable_answers_fail_and_still_delete_the_upload(
    answer: dict[str, Any], tmp_path: Path
) -> None:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"\x00")
    api = FakeMetaApi(answer)
    planner, _ = _planner(api)
    with pytest.raises(ModelOutputError):
        await planner.plan(video, _ingest(), policy="user")
    assert api.requests[-1].method == "DELETE"
