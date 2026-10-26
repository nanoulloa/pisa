"""The offline path end to end: render a fall with known g, normalize, track, recover g."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from pisa_engine.ingest.normalize import normalize
from pisa_engine.synthetic import BallScene, render
from pisa_engine.tracking.fake import ColorSegmenter

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("g", [9.81, 1.62])  # Earth, and the Moon (what a fake might show).
async def test_recovers_gravity_from_pixels(g: float, tmp_path: Path) -> None:
    scene = BallScene(g_mps2=g, vx_mps=0.8)
    raw = tmp_path / "scene.mp4"
    render(scene, raw)
    ingest = normalize(raw, tmp_path / "normalized.mp4")
    assert ingest.timebase.frame_count == scene.frame_count

    (track,) = await ColorSegmenter().track(
        tmp_path / "normalized.mp4", "ball", ingest.timebase, policy="internal"
    )
    t = np.array([s.t_s for s in track.samples])
    x = np.array([s.centroid.x for s in track.samples])
    y = np.array([s.centroid.y for s in track.samples])

    truth = scene.true_trajectory()
    assert len(t) == scene.frame_count
    assert np.abs(y - truth[:, 2]).max() < 0.5  # pixels
    curvature, _, _ = np.polyfit(t, y, 2)
    assert 2 * curvature / scene.pixels_per_meter == pytest.approx(g, rel=0.01)
    assert np.polyfit(t, x, 1)[0] / scene.pixels_per_meter == pytest.approx(0.8, rel=0.01)
