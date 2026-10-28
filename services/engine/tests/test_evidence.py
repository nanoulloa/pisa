"""The evidence video, where it is kept, how it is served, and that it is gone after 24 hours."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import cv2
import httpx
import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from pisa_contracts import TrackedObject
from pisa_engine.api import create_app
from pisa_engine.ingest.normalize import normalize
from pisa_engine.jobs import StorageJobStore
from pisa_engine.physics.implied_g import Scale
from pisa_engine.physics.trajectory import Trajectory, from_track, segment_flight
from pisa_engine.render.ghost import Ghost, OwnedFlight, ghosts
from pisa_engine.render.store import LocalEvidenceStore, SupabaseEvidenceStore, delete_expired
from pisa_engine.render.video import PAPER, _draw_ghost, _to_frame, render_evidence
from pisa_engine.settings import Settings
from pisa_engine.storage import LocalStorage
from pisa_engine.synthetic import BallScene, render
from pisa_engine.tracking.fake import ColorSegmenter
from pisa_engine.vision.stabilize import CameraPath, boxes_by_frame, estimate_camera_path, stabilize

pytestmark = pytest.mark.anyio


async def _measure(
    scene: BallScene, folder: Path, scale: Scale | None
) -> tuple[Path, Any, CameraPath, list[TrackedObject], list[Ghost]]:
    render(scene, folder / "raw.mp4")
    ingest = normalize(folder / "raw.mp4", folder / "clip.mp4")
    objects = await ColorSegmenter().track(
        folder / "clip.mp4", "ball", ingest.timebase, policy="internal"
    )
    path = estimate_camera_path(folder / "clip.mp4", boxes_by_frame(objects))
    flights = [
        OwnedFlight(obj.phrase, obj.object_id, segment_flight(from_track(shot)))
        for obj in objects
        for shot in stabilize(obj, path)
    ]
    return (
        folder / "clip.mp4",
        ingest,
        path,
        objects,
        ghosts(flights, scale=scale, slow_motion=False),
    )


def _ball_center(frame: np.ndarray) -> tuple[float, float]:
    """Center of the orange ball, from all its pixels."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    rows, cols = np.nonzero(cv2.inRange(hsv, np.array((5, 150, 150)), np.array((25, 255, 255))))
    assert rows.size > 0, "ball not found"
    return float(cols.mean()), float(rows.mean())


def _ghost_center(frame: np.ndarray) -> tuple[float, float]:
    """Center of the roundest lime blob: the ghost, not the thin path behind it."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array((28, 60, 150)), np.array((45, 255, 255)))
    count, _, stats, centroids = cv2.connectedComponentsWithStats(mask)
    round_blobs = [
        i
        for i in range(1, count)
        if stats[i, cv2.CC_STAT_AREA] > 100
        and 0.7 < stats[i, cv2.CC_STAT_WIDTH] / stats[i, cv2.CC_STAT_HEIGHT] < 1.4
    ]
    assert round_blobs, "ghost not found"
    best = max(round_blobs, key=lambda i: stats[i, cv2.CC_STAT_AREA])
    return float(centroids[best][0]), float(centroids[best][1])


async def test_the_earth_ghost_falls_away_from_a_moon_fall(tmp_path: Path) -> None:
    scene = BallScene(g_mps2=1.62, hold_s=0.2, duration_s=0.8)
    clip, ingest, path, objects, found = await _measure(scene, tmp_path, Scale(380.0, 420.0))
    video = render_evidence(clip, ingest.timebase, path, objects, found, tmp_path / "evidence.mp4")
    assert video is not None
    assert video.playback_rate == 0.5  # A short fall plays at half speed.
    assert video.duration_s == pytest.approx(2 * 0.8, abs=0.1)
    assert video.size_bytes < 16 * 1024 * 1024

    capture = cv2.VideoCapture(str(video.path))
    capture.set(cv2.CAP_PROP_POS_FRAMES, int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) - 1)
    ok, last = capture.read()
    capture.release()
    assert ok
    ball = _ball_center(last)
    ghost = _ghost_center(last)
    assert abs(ghost[0] - ball[0]) < 2
    assert ghost[1] - ball[1] > 150  # Under Earth's gravity it would be far lower by now.


async def test_the_video_says_where_in_the_clip_it_starts(tmp_path: Path) -> None:
    scene = BallScene(hold_s=1.0, duration_s=1.5)
    clip, ingest, path, objects, found = await _measure(scene, tmp_path, None)
    video = render_evidence(clip, ingest.timebase, path, objects, found, tmp_path / "evidence.mp4")
    assert video is not None
    # Half a second before the fall, so captions written in clip time can be placed.
    assert video.start_s == pytest.approx(found[0].start_s - 0.5, abs=1 / scene.fps)


async def test_on_a_shaky_clip_the_ghost_is_drawn_where_the_object_is(tmp_path: Path) -> None:
    scene = BallScene(textured=True, camera_shake_px=10.0, hold_s=0.1, duration_s=0.7, vx_mps=0.8)
    _, ingest, path, objects, found = await _measure(scene, tmp_path, None)
    assert not path.static
    (ghost,) = found
    fps = ingest.timebase.fps_num / ingest.timebase.fps_den
    for sample in objects[0].samples[10::8]:
        if not ghost.start_s <= sample.t_s <= ghost.end_s:
            continue
        x, y = ghost.position(np.array([sample.t_s]))
        to_frame = _to_frame(path, round(sample.t_s * fps))
        drawn = to_frame @ np.array([x[0], y[0], 1.0])
        # Within a pixel of the ball in the shaken frame, not of the stabilized one.
        assert np.hypot(drawn[0] - sample.centroid.x, drawn[1] - sample.centroid.y) < 1.5


def test_after_a_bounce_the_earlier_ghost_leaves_only_its_path() -> None:
    scene = BallScene(profile="bounce", restitution=0.7, duration_s=1.4)
    rows = scene.true_trajectory()
    flight = segment_flight(Trajectory(t=rows[:, 0], x=rows[:, 1], y=rows[:, 2]))
    found = ghosts([OwnedFlight("ball", 0, flight)], scale=None, slow_motion=False)
    first = min(found, key=lambda g: g.start_s)
    assert first.gone_s is not None
    radius = scene.radius_px
    (x,), (y,) = first.position(np.array([first.end_s]))
    ys, xs = np.ogrid[: scene.height, : scene.width]
    inside = (xs - x) ** 2 + (ys - y) ** 2 <= (radius - 3) ** 2

    def drawn_share(t: float) -> float:
        frame = np.full((scene.height, scene.width, 3), PAPER, dtype=np.uint8)
        _draw_ghost(frame, first, t, np.eye(3)[:2], radius)
        return float((frame[inside] != PAPER).any(axis=1).mean())

    assert drawn_share(first.end_s) > 0.9  # Until the bounce, the ghost is there.
    # Once the ball has bounced, a ghost left on the floor would say it should not have.
    assert drawn_share(first.gone_s + 0.1) < 0.4


def test_nothing_measured_draws_nothing(tmp_path: Path) -> None:
    clip = tmp_path / "clip.mp4"
    assert render_evidence(clip, None, None, [], [], tmp_path / "out.mp4") is None  # type: ignore[arg-type]


# Stores


def test_local_store_keeps_and_expires_videos(tmp_path: Path) -> None:
    store = LocalEvidenceStore(tmp_path / "evidence")
    video = tmp_path / "v.mp4"
    video.write_bytes(b"mp4")
    fresh, stale = uuid4(), uuid4()
    store.put(fresh, video)
    store.put(stale, video)
    day_ago = (datetime.now(UTC) - timedelta(hours=25)).timestamp()
    stale_path = store.locate(stale)
    assert stale_path is not None
    os.utime(stale_path, (day_ago, day_ago))
    assert delete_expired(store) == 1
    assert store.locate(stale) is None
    assert store.locate(fresh) is not None


def test_supabase_store_reuses_a_signed_link_while_it_has_time_left() -> None:
    job = uuid4()
    signs: list[httpx.Request] = []
    now = [0.0]

    def respond(request: httpx.Request) -> httpx.Response:
        signs.append(request)
        return httpx.Response(
            200, json={"signedURL": f"/object/sign/evidence/{job}.mp4?t={len(signs)}"}
        )

    store = SupabaseEvidenceStore(
        "https://project.supabase.co",
        SecretStr("sb_secret_not-real"),
        httpx.MockTransport(respond),
        clock=lambda: now[0],
    )
    first = store.locate(job)
    now[0] = 49 * 60.0  # A shared link opened by the rest of the group within the hour.
    assert store.locate(job) == first
    assert len(signs) == 1
    now[0] = 51 * 60.0  # Under ten minutes left: a fresh link.
    assert store.locate(job) != first
    assert len(signs) == 2


def test_supabase_store_uses_the_storage_api() -> None:
    job, old, new = uuid4(), uuid4(), uuid4()
    requests: list[httpx.Request] = []
    now = datetime.now(UTC)

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        path = request.url.path
        if path.startswith("/storage/v1/object/sign/"):
            if str(job) in path:
                return httpx.Response(
                    200, json={"signedURL": f"/object/sign/evidence/{job}.mp4?token=t"}
                )
            return httpx.Response(400, json={"statusCode": "404", "error": "not_found"})
        if path == "/storage/v1/object/list/evidence":
            return httpx.Response(
                200,
                json=[
                    {"name": f"{old}.mp4", "created_at": (now - timedelta(hours=30)).isoformat()},
                    {"name": f"{new}.mp4", "created_at": (now - timedelta(hours=2)).isoformat()},
                ],
            )
        return httpx.Response(200, json={})

    store = SupabaseEvidenceStore(
        "https://project.supabase.co", SecretStr("sb_secret_not-real"), httpx.MockTransport(respond)
    )
    video = Path(__file__)  # Any file stands in for the video bytes.
    store.put(job, video)
    upload = requests[-1]
    assert (upload.method, upload.url.path) == ("POST", f"/storage/v1/object/evidence/{job}.mp4")
    assert upload.headers["content-type"] == "video/mp4"
    assert upload.headers["x-upsert"] == "true"
    assert upload.headers["apikey"] == "sb_secret_not-real"
    assert "authorization" not in upload.headers  # New secret keys go in apikey only.

    assert (
        store.locate(job)
        == f"https://project.supabase.co/storage/v1/object/sign/evidence/{job}.mp4?token=t"
    )
    assert json.loads(requests[-1].content) == {"expiresIn": 3600}
    assert store.locate(uuid4()) is None

    assert store.delete_older_than(now - timedelta(hours=24)) == 1
    delete = requests[-1]
    assert (delete.method, delete.url.path) == ("DELETE", "/storage/v1/object/evidence")
    assert json.loads(delete.content) == {"prefixes": [f"{old}.mp4"]}


# Through the API


@pytest.fixture(scope="module")
def eased_clip(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("clips") / "eased.mp4"
    render(BallScene(profile="eased", hold_s=0.15, duration_s=0.75, vx_mps=0.8), path)
    return path


def test_the_result_carries_evidence_and_the_engine_serves_the_video(
    eased_clip: Path, tmp_path: Path
) -> None:
    settings = Settings(_env_file=None, PISA_DATA_DIR=str(tmp_path / "data"))
    client = TestClient(create_app(settings))
    with eased_clip.open("rb") as video:
        job_id = client.post("/jobs", files={"video": ("c.mp4", video, "video/mp4")}).json()["id"]
    result = client.get(f"/jobs/{job_id}/result").json()
    assert result["job"]["stage"] == "render"
    evidence = result["evidence"]
    assert evidence["video"]["playback_rate"] == 0.5
    assert evidence["video"]["source_start_s"] == 0.0  # The padding reaches the clip's start.
    expires = datetime.fromisoformat(evidence["video"]["expires_at"])
    assert timedelta(hours=23) < expires - datetime.now(UTC) <= timedelta(hours=24)
    (series,) = evidence["series"]
    assert series["model"] == "fit"
    assert max(abs(a - b) for a, b in zip(series["y_px"], series["ghost_y_px"], strict=True)) > 10

    response = client.get(f"/jobs/{job_id}/evidence.mp4")
    assert response.status_code == 200
    assert response.headers["content-type"] == "video/mp4"
    assert response.content[4:8] == b"ftyp"

    # Past its expiry the video is not served, even before the sweep deletes the file.
    jobs = StorageJobStore(LocalStorage(tmp_path / "data"))
    stored = jobs.get_result(UUID(job_id))
    assert stored is not None
    assert stored.evidence is not None
    assert stored.evidence.video is not None
    past = stored.evidence.video.model_copy(
        update={"expires_at": datetime.now(UTC) - timedelta(seconds=1)}
    )
    jobs.save_result(
        stored.model_copy(update={"evidence": stored.evidence.model_copy(update={"video": past})})
    )
    expired = client.get(f"/jobs/{job_id}/evidence.mp4")
    assert (expired.status_code, expired.json()["error"]["code"]) == (404, "evidence_expired")
    assert client.get(f"/jobs/{uuid4()}/evidence.mp4").status_code == 404
