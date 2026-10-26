"""Meta Model API client and SAM adapter against httpx.MockTransport: nothing leaves the machine."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pytest
from meta_sam_parser._mask_codec import _encode_raster  # Test-only: builds one_bit payloads.
from pydantic import SecretStr

from pisa_contracts import Timebase
from pisa_engine.model_api.client import MetaModelApiClient, ModelApiError
from pisa_engine.model_api.policy import ContributorTierForbiddenError
from pisa_engine.model_api.spend import InMemorySpendLedger, PaidCallsDisabledError, SpendGuard
from pisa_engine.tracking.sam import Sam31Segmenter

pytestmark = pytest.mark.anyio

FAKE_KEY = "LLM_000_not-a-real-key"
BASE_URL = "https://api.meta.ai/v1"


class Recorder:
    """A MockTransport handler that records every request it receives."""

    def __init__(self, respond: Callable[[httpx.Request], httpx.Response]) -> None:
        self.requests: list[httpx.Request] = []
        self._respond = respond

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._respond(request)


def _client(
    recorder: Recorder, *, enabled: bool = True, ledger: InMemorySpendLedger | None = None
) -> MetaModelApiClient:
    guard = SpendGuard(enabled=enabled, cap_usd=1.0, ledger=ledger or InMemorySpendLedger())
    return MetaModelApiClient(
        api_key=SecretStr(FAKE_KEY),
        base_url=BASE_URL,
        guard=guard,
        transport=httpx.MockTransport(recorder),
    )


def _sse(events: list[dict[str, Any]]) -> httpx.Response:
    body = "".join(f"data: {json.dumps(event)}\n\n" for event in events) + "data: [DONE]\n\n"
    return httpx.Response(200, text=body, headers={"Content-Type": "text/event-stream"})


async def test_kill_switch_blocks_before_any_request(tmp_path: Path) -> None:
    recorder = Recorder(lambda _: httpx.Response(200, json={}))
    client = _client(recorder, enabled=False)
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"\x00")

    with pytest.raises(PaidCallsDisabledError):
        await client.upload_file(video)
    with pytest.raises(PaidCallsDisabledError):
        await client.create_response(
            {"model": "muse-spark-1.3", "input": "hi"}, policy="internal", worst_case_usd=0.001
        )
    with pytest.raises(PaidCallsDisabledError):
        async for _ in client.stream_response(
            {"model": "sam-3.1", "input": []}, policy="internal", worst_case_usd=0.01
        ):
            pass
    assert recorder.requests == []


async def test_user_videos_never_reach_contributor_models() -> None:
    recorder = Recorder(lambda _: httpx.Response(200, json={}))
    client = _client(recorder)
    with pytest.raises(ContributorTierForbiddenError):
        await client.create_response(
            {"model": "muse-spark-1.3-contributor", "input": "hi"},
            policy="user",
            worst_case_usd=0.001,
        )
    assert recorder.requests == []


async def test_create_response_sends_bearer_key_to_responses_endpoint() -> None:
    recorder = Recorder(lambda _: httpx.Response(200, json={"status": "completed"}))
    client = _client(recorder)
    payload = await client.create_response(
        {"model": "muse-spark-1.3", "input": "hi"}, policy="user", worst_case_usd=0.001
    )
    assert payload == {"status": "completed"}
    (request,) = recorder.requests
    assert request.url == f"{BASE_URL}/responses"
    assert request.headers["Authorization"] == f"Bearer {FAKE_KEY}"
    assert json.loads(request.content) == {"model": "muse-spark-1.3", "input": "hi"}


async def test_http_errors_do_not_echo_the_key() -> None:
    recorder = Recorder(lambda _: httpx.Response(401, json={"error": {"code": "invalid_api_key"}}))
    client = _client(recorder)
    with pytest.raises(ModelApiError) as error:
        await client.create_response(
            {"model": "muse-spark-1.3", "input": "hi"}, policy="user", worst_case_usd=0.001
        )
    assert error.value.status_code == 401
    assert FAKE_KEY not in str(error.value)


def _one_bit_mask(height: int, width: int, rows: slice, cols: slice) -> str:
    raster = np.zeros((height, width), dtype=np.uint8)
    raster[rows, cols] = 1
    return _encode_raster([int(value) for value in raster.flatten()], width, height)


def _sam_events(lines: list[str]) -> list[dict[str, Any]]:
    lane = {"item_id": "msg_1", "output_index": 0, "content_index": 0}
    text = "".join(lines)
    return [
        *({"type": "response.output_text.delta", "delta": line, **lane} for line in lines),
        {"type": "response.output_text.done", "text": text, **lane},
        {"type": "response.completed", "response": {"status": "completed"}},
    ]


async def test_sam_segmenter_turns_streamed_masks_into_centroids(tmp_path: Path) -> None:
    # A 12x10 mask over a box with inclusive corners (100,200)-(124,220), so the box is 25x21 px.
    mask = _one_bit_mask(10, 12, slice(2, 8), slice(3, 9))
    lines = [
        f"<{frame}f>0<|box;x1=100;y1={200 + 10 * frame};x2=124;y2={220 + 10 * frame};"
        f"w=640;h=480;c=0.9|><|mask;x=0;y=0;data=10,12,{mask}|>\n"
        for frame in range(3)
    ]

    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/files"):
            return httpx.Response(200, json={"id": "file-test"})
        return _sse(_sam_events(lines))

    recorder = Recorder(respond)
    ledger = InMemorySpendLedger()
    segmenter = Sam31Segmenter(_client(recorder, ledger=ledger))
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"\x00")
    timebase = Timebase(fps_num=60, fps_den=1, start_s=1.0, frame_count=3)

    (track,) = await segmenter.track(video, "tennis ball", timebase, policy="user")

    assert [sample.frame for sample in track.samples] == [0, 1, 2]
    assert [sample.t_s for sample in track.samples] == pytest.approx([1.0, 1 + 1 / 60, 1 + 2 / 60])
    first = track.samples[0]
    # The mask is centered in its half-open 25x21 box, so the centroid is the box center.
    assert (first.centroid.x, first.centroid.y) == pytest.approx((112.5, 210.5))
    assert first.area_px == pytest.approx(36 * (25 / 12) * (21 / 10))
    assert first.confidence == pytest.approx(0.9)

    upload, stream = recorder.requests
    body = json.loads(stream.content)
    assert body["model"] == "sam-3.1"
    assert body["stream"] is True
    assert body["input"][0]["content"] == [
        {"type": "input_text", "text": "tennis ball"},
        {"type": "input_video", "file_id": "file-test"},
    ]
    assert upload.url.path == "/v1/files"
    assert [entry.quantity for entry in ledger.entries] == [50]  # Billed minimum.
