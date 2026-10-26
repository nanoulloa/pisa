"""Every law through the whole pipeline: rendered clip in, verdict and decisive tests out."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from pisa_engine.api import create_app
from pisa_engine.settings import Settings
from pisa_engine.synthetic import BallScene, render

SCENES = {
    "bounce": BallScene(profile="bounce", restitution=0.7, duration_s=1.4, vx_mps=0.5),
    "bounce_gains_energy": BallScene(
        profile="bounce", restitution=1.2, y0_px=400.0, duration_s=1.0, vx_mps=0.5
    ),
    "pair": BallScene(companion_g_mps2=9.81, hold_s=0.1, duration_s=0.7),
    "pair_falls_apart": BallScene(companion_g_mps2=6.0, hold_s=0.1, duration_s=0.7),
    "shaky_fall": BallScene(
        textured=True, camera_shake_px=8.0, hold_s=0.1, duration_s=0.7, vx_mps=0.8
    ),
    "shaky_eased": BallScene(
        profile="eased", textured=True, camera_shake_px=8.0, hold_s=0.1, duration_s=0.7
    ),
}


@pytest.fixture(scope="module")
def client(tmp_path_factory: pytest.TempPathFactory) -> TestClient:
    data = tmp_path_factory.mktemp("data")
    return TestClient(create_app(Settings(_env_file=None, PISA_DATA_DIR=str(data))))


@pytest.fixture(scope="module")
def clips(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    folder = tmp_path_factory.mktemp("clips")
    for name, scene in SCENES.items():
        render(scene, folder / f"{name}.mp4")
    return {name: folder / f"{name}.mp4" for name in SCENES}


def _analyze(client: TestClient, clip: Path) -> dict[str, Any]:
    with clip.open("rb") as video:
        created = client.post("/jobs", files={"video": ("clip.mp4", video, "video/mp4")})
    assert created.status_code == 202, created.text
    result: dict[str, Any] = client.get(f"/jobs/{created.json()['id']}/result").json()
    return result


def _outcomes(result: dict[str, Any], test: str) -> list[str]:
    return [t["outcome"] for t in result["tests"] if t["test"] == test]


def test_a_real_bounce(client: TestClient, clips: dict[str, Path]) -> None:
    result = _analyze(client, clips["bounce"])
    assert result["verdict"]["label"] == "consistent_with_real_physics"
    assert _outcomes(result, "bounce_energy") == ["pass"]
    assert _outcomes(result, "time_base_consistency") == ["pass"]
    assert _outcomes(result, "free_fall_shape") == ["pass", "pass"]


def test_a_bounce_that_gains_energy(client: TestClient, clips: dict[str, Path]) -> None:
    result = _analyze(client, clips["bounce_gains_energy"])
    assert result["verdict"]["label"] == "physically_impossible"
    assert result["verdict"]["decisive_tests"] == ["bounce_energy"]


def test_two_balls_falling_together(client: TestClient, clips: dict[str, Path]) -> None:
    result = _analyze(client, clips["pair"])
    assert len(result["tracks"]["objects"]) == 2
    assert result["verdict"]["label"] == "consistent_with_real_physics"
    assert _outcomes(result, "galileo_pair") == ["pass"]


def test_two_balls_falling_apart(client: TestClient, clips: dict[str, Path]) -> None:
    """Each ball alone is a perfect parabola. Only the pair gives the fake away."""
    result = _analyze(client, clips["pair_falls_apart"])
    assert _outcomes(result, "free_fall_shape") == ["pass", "pass"]
    assert result["verdict"]["label"] == "physically_impossible"
    assert result["verdict"]["decisive_tests"] == ["galileo_pair"]


@pytest.mark.parametrize(
    ("scene", "label"),
    [("shaky_fall", "consistent_with_real_physics"), ("shaky_eased", "physically_impossible")],
)
def test_handheld_clips_are_stabilized_first(
    client: TestClient, clips: dict[str, Path], scene: str, label: str
) -> None:
    result = _analyze(client, clips[scene])
    stabilization = result["stabilization"]
    assert stabilization["applied"] is True
    assert stabilization["max_motion_px"] > 4
    assert stabilization["unreliable_frames"] == 0
    assert result["verdict"]["label"] == label
