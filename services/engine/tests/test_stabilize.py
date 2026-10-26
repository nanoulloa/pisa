"""Stabilization on rendered clips: camera shake is undone, still cameras are left alone."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from pisa_contracts import BBox, Point2, TrackedObject, TrackSample
from pisa_engine.ingest.normalize import normalize
from pisa_engine.physics.fit import fit_free_fall
from pisa_engine.physics.trajectory import flight_phases, from_track
from pisa_engine.synthetic import BallScene, render
from pisa_engine.tracking.fake import ColorSegmenter
from pisa_engine.vision.stabilize import (
    CameraPath,
    boxes_by_frame,
    estimate_camera_path,
    estimate_from_frames,
    stabilize,
)

pytestmark = pytest.mark.anyio

PX_PER_M = 400.0


async def _track(scene: BallScene, tmp_path: Path) -> tuple[list[TrackedObject], CameraPath]:
    render(scene, tmp_path / "raw.mp4")
    ingest = normalize(tmp_path / "raw.mp4", tmp_path / "clip.mp4")
    objects = await ColorSegmenter().track(
        tmp_path / "clip.mp4", "ball", ingest.timebase, policy="internal"
    )
    return objects, estimate_camera_path(tmp_path / "clip.mp4", boxes_by_frame(objects))


def _gravity(obj: TrackedObject) -> float:
    (phase,) = flight_phases(from_track(obj))
    return fit_free_fall(phase).acceleration / PX_PER_M


@pytest.mark.parametrize("shake_px", [6.0, 12.0])
async def test_handheld_shake_is_undone(shake_px: float, tmp_path: Path) -> None:
    scene = BallScene(
        textured=True, camera_shake_px=shake_px, hold_s=0.1, duration_s=0.7, vx_mps=0.8
    )
    (ball,), path = await _track(scene, tmp_path)
    assert not path.static
    assert path.unreliable_frames == 0
    assert path.cuts == []
    # Each frame maps onto the first: its shift is how far the camera moved since then.
    # Chaining frame to frame drifts by a few hundredths of a pixel per frame.
    camera = scene.camera_offsets()
    shifts = np.array([transform[:2, 2] for transform in path.to_reference])
    assert np.abs(shifts - (camera - camera[0])).max() < 1.0

    (steady,) = stabilize(ball, path)
    assert _gravity(steady) == pytest.approx(scene.g_mps2, rel=0.01)
    assert abs(_gravity(ball) / scene.g_mps2 - 1) > 0.03  # Without it, g is visibly off.


async def test_a_still_camera_is_left_alone(tmp_path: Path) -> None:
    scene = BallScene(textured=True, hold_s=0.1, duration_s=0.7, vx_mps=0.8)
    (ball,), path = await _track(scene, tmp_path)
    assert path.static  # The falling ball, masked out, does not read as camera motion.
    assert stabilize(ball, path) == [ball]


async def test_a_plain_background_has_nothing_to_follow(tmp_path: Path) -> None:
    (ball,), path = await _track(BallScene(), tmp_path)
    assert path.static
    assert path.unreliable_frames == 0
    assert stabilize(ball, path) == [ball]


def _textured(seed: int, shift_px: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    frame = np.full((480, 640, 3), 236, dtype=np.uint8)
    for _ in range(120):
        x, y = int(rng.integers(-40, 680)), int(rng.integers(-40, 520))
        shade = int(rng.integers(40, 200))
        size = int(rng.integers(8, 50))
        cv2.rectangle(frame, (x, y), (x + size, y + size), (shade, shade, shade), thickness=-1)
    return np.roll(frame, shift_px, axis=1)


def _sample(frame: int) -> TrackSample:
    return TrackSample(
        frame=frame,
        t_s=frame / 30,
        bbox=BBox(x1=300, y1=200 + frame, x2=320, y2=220 + frame),
        centroid=Point2(x=310, y=210 + frame),
        area_px=400,
        confidence=None,
    )


def test_a_scene_cut_starts_a_new_shot() -> None:
    frames = [_textured(1, shift) for shift in range(8)] + [_textured(2) for _ in range(8)]
    path = estimate_from_frames(frames, {})
    assert path.cuts == [8]
    assert path.unreliable_frames == 0

    obj = TrackedObject(phrase="ball", object_id=0, samples=[_sample(i) for i in range(16)])
    shots = stabilize(obj, path)
    assert [len(shot.samples) for shot in shots] == [8, 8]
    assert path.shot(7) == 0
    assert path.shot(8) == 1


def test_a_frame_that_cannot_be_linked_is_dropped_not_cut() -> None:
    frames = [_textured(1, shift) for shift in range(6)]
    frames[3] = cv2.GaussianBlur(frames[3], (0, 0), sigmaX=12)  # Motion blur, not a new shot.
    path = estimate_from_frames(frames, {})
    assert path.cuts == []
    assert path.reliable.tolist() == [True, True, True, False, True, True]
    # Frame 4 links back to frame 2, the last trusted one.
    assert path.to_reference[4][0, 2] == pytest.approx(-4.0, abs=0.2)

    obj = TrackedObject(phrase="ball", object_id=0, samples=[_sample(i) for i in range(6)])
    assert path.unreliable_share(obj) == pytest.approx(1 / 6)
    (shot,) = stabilize(obj, path)
    assert [s.frame for s in shot.samples] == [0, 1, 2, 4, 5]
