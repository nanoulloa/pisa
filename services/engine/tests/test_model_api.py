"""Meta Model API client and SAM adapter against httpx.MockTransport: nothing leaves the machine."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pytest
from meta_sam_parser import ResponsesStreamSourceError
from meta_sam_parser._mask_codec import _encode_raster  # Test-only: builds one_bit payloads.
from pydantic import SecretStr

from pisa_contracts import Timebase
from pisa_engine.model_api import costs
from pisa_engine.model_api.client import MetaModelApiClient, ModelApiError
from pisa_engine.model_api.policy import ContributorTierForbiddenError
from pisa_engine.model_api.spend import (
    InMemorySpendLedger,
    PaidCallsDisabledError,
    SpendCapExceededError,
    SpendGuard,
)
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
            {"model": "muse-spark-1.3", "input": "hi"},
            policy="internal",
            worst_case_usd=0.001,
            stage="plan",
        )
    with pytest.raises(PaidCallsDisabledError):
        async for _ in client.stream_response(
            {"model": "sam-3.1", "input": []}, policy="internal", worst_case_usd=0.01, charge=[]
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
            stage="plan",
        )
    assert recorder.requests == []


async def test_create_response_sends_bearer_key_and_records_token_cost() -> None:
    usage = {"input_tokens": 15, "output_tokens": 175}
    recorder = Recorder(lambda _: httpx.Response(200, json={"status": "completed", "usage": usage}))
    ledger = InMemorySpendLedger()
    client = _client(recorder, ledger=ledger)
    payload = await client.create_response(
        {"model": "muse-spark-1.3", "input": "hi"}, policy="user", worst_case_usd=0.01, stage="plan"
    )
    assert payload["status"] == "completed"
    assert [(e.unit, e.quantity) for e in ledger.entries] == [
        ("input_tokens", 15),
        ("output_tokens", 175),
    ]
    assert ledger.spent_usd() == pytest.approx(0.000763, abs=1e-6)
    (request,) = recorder.requests
    assert request.url == f"{BASE_URL}/responses"
    assert request.headers["Authorization"] == f"Bearer {FAKE_KEY}"
    assert json.loads(request.content) == {"model": "muse-spark-1.3", "input": "hi"}


async def test_http_errors_do_not_echo_the_key() -> None:
    recorder = Recorder(lambda _: httpx.Response(401, json={"error": {"code": "invalid_api_key"}}))
    client = _client(recorder)
    with pytest.raises(ModelApiError) as error:
        await client.create_response(
            {"model": "muse-spark-1.3", "input": "hi"},
            policy="user",
            worst_case_usd=0.001,
            stage="plan",
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
            return httpx.Response(200, json={"id": "file-test", "expires_at": 1793050000})
        if request.method == "DELETE":
            return httpx.Response(200, json={"id": "file-test", "object": "file", "deleted": True})
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

    upload, stream, delete = recorder.requests
    body = json.loads(stream.content)
    assert body["model"] == "sam-3.1"
    assert body["stream"] is True
    assert body["input"][0]["content"] == [
        {"type": "input_text", "text": "tennis ball"},
        {"type": "input_video", "file_id": "file-test"},
    ]
    assert upload.url.path == "/v1/files"
    form = upload.content.decode("latin-1")
    for field, value in [
        ("purpose", "user_data"),
        ("expires_after[anchor]", "created_at"),
        ("expires_after[seconds]", "3600"),
    ]:
        assert f'name="{field}"\r\n\r\n{value}\r\n' in form
    # Privacy: the video leaves Meta's storage as soon as SAM is done with it.
    assert (delete.method, delete.url.path) == ("DELETE", "/v1/files/file-test")
    assert [entry.quantity for entry in ledger.entries] == [50]  # Billed minimum.


async def test_uploads_are_deleted_even_when_the_call_fails(tmp_path: Path) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/files"):
            return httpx.Response(200, json={"id": "file-9", "expires_at": 1793050000})
        if request.method == "DELETE":
            return httpx.Response(200, json={"id": "file-9", "object": "file", "deleted": True})
        return httpx.Response(500, json={"error": {"code": "server_error"}})

    recorder = Recorder(respond)
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"\x00")
    timebase = Timebase(fps_num=30, fps_den=1, start_s=0.0, frame_count=10)
    with pytest.raises(ResponsesStreamSourceError) as error:  # The parser wraps stream errors.
        await Sam31Segmenter(_client(recorder)).track(video, "ball", timebase, policy="user")
    assert isinstance(error.value.__cause__, ModelApiError)
    assert [r.method for r in recorder.requests] == ["POST", "POST", "DELETE"]


async def test_token_counting_is_gated_and_reads_the_count() -> None:
    recorder = Recorder(
        lambda _: httpx.Response(200, json={"object": "response.input_tokens", "input_tokens": 812})
    )
    body = {"model": "muse-spark-1.3", "input": "hi"}
    with pytest.raises(PaidCallsDisabledError):
        await _client(recorder, enabled=False).count_input_tokens(body, policy="user")
    with pytest.raises(ContributorTierForbiddenError):
        await _client(recorder).count_input_tokens(
            {**body, "model": "muse-spark-1.3-contributor"}, policy="user"
        )
    assert recorder.requests == []
    assert await _client(recorder).count_input_tokens(body, policy="user") == 812
    (request,) = recorder.requests
    assert request.url.path == "/v1/responses/input_tokens"


async def test_a_job_collects_what_its_calls_cost() -> None:
    usage = {"input_tokens": 1000, "output_tokens": 100}
    recorder = Recorder(lambda _: httpx.Response(200, json={"status": "completed", "usage": usage}))
    client = _client(recorder)
    body = {"model": "muse-spark-1.3", "input": "hi"}
    await client.create_response(body, policy="user", worst_case_usd=0.01, stage="plan")
    with costs.collecting() as spent:
        await client.create_response(body, policy="user", worst_case_usd=0.01, stage="explain")
    assert [(e.stage, e.unit) for e in spent] == [
        ("explain", "input_tokens"),
        ("explain", "output_tokens"),
    ]
    assert sum(e.usd for e in spent) == pytest.approx(0.001675)


@pytest.mark.parametrize(
    ("failure", "charged_usd"),
    [
        (lambda _request: httpx.Response(429, json={}), 0.0),  # Refused: not billed.
        (lambda _request: httpx.Response(503, json={}), 0.01),  # May have run: worst case.
        (httpx.ReadTimeout, 0.01),  # Sent, then lost: worst case.
        (httpx.ConnectError, 0.0),  # Never left the machine.
    ],
)
async def test_failed_calls_are_charged_unless_they_provably_never_ran(
    failure: Callable[[httpx.Request], httpx.Response] | type[Exception], charged_usd: float
) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        if isinstance(failure, type):
            raise failure("simulated", request=request)
        return failure(request)

    ledger = InMemorySpendLedger()
    guard = SpendGuard(enabled=True, cap_usd=0.015, ledger=ledger)
    client = MetaModelApiClient(
        api_key=SecretStr(FAKE_KEY),
        base_url=BASE_URL,
        guard=guard,
        transport=httpx.MockTransport(respond),
    )
    with pytest.raises((ModelApiError, httpx.HTTPError)):
        await client.create_response(
            {"model": "muse-spark-1.3", "input": "hi"},
            policy="user",
            worst_case_usd=0.01,
            stage="plan",
        )
    assert ledger.spent_usd() == pytest.approx(charged_usd)
    # The reservation is closed either way: a second call fits again only if nothing was charged.
    if charged_usd == 0:
        guard.reserve(0.01)
    else:
        with pytest.raises(SpendCapExceededError):
            guard.reserve(0.01)
