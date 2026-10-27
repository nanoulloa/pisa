"""Phases, the T1 shape test and the verdict policy on trajectories with known motion."""

from __future__ import annotations

import numpy as np
import pytest

import pisa_contracts as contracts
from pisa_engine.physics.shape import free_fall_shape
from pisa_engine.physics.trajectory import Trajectory, flight_phases
from pisa_engine.synthetic import BallScene, MotionProfile
from pisa_engine.verdict import POLICY_VERSION, decide

FPS = 60


def _scene_trajectory(
    profile: MotionProfile, *, hold_s: float = 0.0, g: float = 9.81
) -> Trajectory:
    rows = BallScene(profile=profile, hold_s=hold_s, g_mps2=g, vx_mps=0.8).true_trajectory()
    return Trajectory(t=rows[:, 0], x=rows[:, 1], y=rows[:, 2])


def _with_noise(trajectory: Trajectory, sigma_px: float, seed: int) -> Trajectory:
    rng = np.random.default_rng(seed)
    n = len(trajectory)
    return Trajectory(
        t=trajectory.t,
        x=trajectory.x + rng.normal(0, sigma_px, n),
        y=trajectory.y + rng.normal(0, sigma_px, n),
    )


def _measurement(result: contracts.TestResult, name: str) -> float:
    return next(m.value for m in result.measurements if m.name == name)


# Phases


def test_rest_before_release_is_dropped_but_the_release_frame_kept() -> None:
    trajectory = _scene_trajectory("free_fall", hold_s=0.2)
    (phase,) = flight_phases(trajectory)
    assert phase.t[0] == pytest.approx(0.2)  # The release frame.
    assert phase.t[-1] == pytest.approx(trajectory.t[-1])


def test_a_bounce_splits_the_track_into_two_phases() -> None:
    t = np.arange(48) / FPS
    impact = 0.4
    down = 100 + 0.5 * 9.81 * t**2 * 400
    floor_y = 100 + 0.5 * 9.81 * impact**2 * 400
    after = t - impact
    up = floor_y - (0.6 * 9.81 * impact * after - 0.5 * 9.81 * after**2) * 400
    y = np.where(t <= impact, down, up)
    phases = flight_phases(Trajectory(t=t, x=np.full_like(t, 300.0), y=y))
    assert len(phases) == 2
    assert phases[0].t[-1] < impact <= phases[1].t[0] + 1 / FPS


@pytest.mark.parametrize("sigma_px", [0.5, 1.0, 2.0])
def test_a_jittery_hold_is_still_a_rest(sigma_px: float) -> None:
    """Trackers jitter on real footage, so a held ball is never perfectly still."""
    trajectory = _scene_trajectory("free_fall", hold_s=0.2)
    for seed in range(50):
        (phase,) = flight_phases(_with_noise(trajectory, sigma_px, seed))
        assert phase.t[0] == pytest.approx(0.2, abs=2.5 / FPS)


@pytest.mark.parametrize("sigma_px", [0.5, 1.0, 2.0])
def test_a_jittery_throw_from_the_hand_is_not_called_impossible(sigma_px: float) -> None:
    """Found by the synthetic eval: with the hold left in, the jump to throwing speed looked
    like acceleration that grows, and real throws were judged impossible."""
    rows = BallScene(
        hold_s=0.1, duration_s=0.9, x0_px=120.0, y0_px=600.0, vx_mps=1.0, vy_mps=-3.5
    ).true_trajectory()
    throw = Trajectory(t=rows[:, 0], x=rows[:, 1], y=rows[:, 2])
    for seed in range(100):
        phases = flight_phases(_with_noise(throw, sigma_px, seed))
        assert decide([free_fall_shape(p) for p in phases]).label != "physically_impossible"


def test_a_still_object_has_no_phases() -> None:
    t = np.arange(30) / FPS
    still = Trajectory(t=t, x=np.full_like(t, 10.0), y=np.full_like(t, 50.0))
    assert flight_phases(still) == []


# T1


def test_real_fall_passes_with_earth_and_with_slow_motion_gravity() -> None:
    for g in (9.81, 2.0):  # A perfect parabola with low g is what slow motion looks like.
        (phase,) = flight_phases(_scene_trajectory("free_fall", g=g))
        result = free_fall_shape(phase)
        assert result.outcome == "pass", g
        assert _measurement(result, "acceleration_px_s2") == pytest.approx(g * 400, rel=1e-6)


def test_eased_motion_violates_constant_acceleration() -> None:
    (phase,) = flight_phases(_scene_trajectory("eased"))
    result = free_fall_shape(phase)
    assert result.outcome == "violation"
    assert result.reason_code == "slows_down_while_falling"
    assert result.confidence > 0.99


def test_air_drag_is_not_a_violation() -> None:
    """Linear drag: acceleration shrinks from g toward zero as the object speeds up."""
    g, k = 9.81, 3.0  # Terminal speed g/k = 3.3 m/s, reached partly within the clip.
    t = np.arange(45) / FPS
    fallen = (g / k) * t - (g / k**2) * (1 - np.exp(-k * t))
    phase = Trajectory(t=t, x=np.full_like(t, 300.0), y=80 + fallen * 400)
    assert free_fall_shape(phase).outcome == "pass"


def test_acceleration_that_grows_during_the_fall_is_a_violation() -> None:
    t = np.arange(40) / FPS
    phase = Trajectory(t=t, x=np.full_like(t, 300.0), y=80 + 6000 * t**3)
    result = free_fall_shape(phase)
    assert (result.outcome, result.reason_code) == ("violation", "acceleration_grows")


def test_an_object_changing_size_is_not_judged() -> None:
    trajectory = _scene_trajectory("eased")
    growing = Trajectory(
        t=trajectory.t, x=trajectory.x, y=trajectory.y, area=np.linspace(400, 900, len(trajectory))
    )
    (phase,) = flight_phases(growing)
    result = free_fall_shape(phase)
    assert (result.outcome, result.reason_code) == ("insufficient_data", "depth_change")


def test_constant_velocity_has_no_measurable_acceleration() -> None:
    (phase,) = flight_phases(_scene_trajectory("constant_velocity"))
    result = free_fall_shape(phase)
    assert result.outcome == "insufficient_data"
    assert result.reason_code == "no_measurable_acceleration"


def test_rising_object_that_accelerates_upward_is_a_violation() -> None:
    trajectory = _scene_trajectory("free_fall")
    flipped = Trajectory(t=trajectory.t, x=trajectory.x, y=2000 - trajectory.y)
    (phase,) = flight_phases(flipped)
    result = free_fall_shape(phase)
    assert result.outcome == "violation"
    assert result.reason_code == "accelerates_upward"


@pytest.mark.parametrize("sigma_px", [0.3, 1.0, 2.0])
def test_noisy_real_falls_are_never_called_impossible(sigma_px: float) -> None:
    """The false positive rate on real videos is the number that matters most."""
    clean = _scene_trajectory("free_fall")
    verdicts = []
    for seed in range(200):
        phases = flight_phases(_with_noise(clean, sigma_px, seed))
        verdicts.append(decide([free_fall_shape(p) for p in phases]).label)
    assert "physically_impossible" not in verdicts
    assert verdicts.count("consistent_with_real_physics") >= 190


def test_noisy_eased_motion_is_still_caught() -> None:
    clean = _scene_trajectory("eased")
    labels = {
        decide([free_fall_shape(p) for p in flight_phases(_with_noise(clean, 1.0, seed))]).label
        for seed in range(50)
    }
    assert labels == {"physically_impossible"}


# Verdict policy


def _result(outcome: str, confidence: float) -> contracts.TestResult:
    return contracts.TestResult.model_validate(
        {
            "test": "free_fall_shape",
            "outcome": outcome,
            "confidence": confidence,
            "measurements": [],
            "reason_code": None,
        }
    )


@pytest.mark.parametrize(
    ("results", "label", "reason"),
    [
        ([], "inconclusive", "no_measurable_events"),
        ([_result("insufficient_data", 0.0)], "inconclusive", "no_measurable_events"),
        ([_result("pass", 0.9)], "consistent_with_real_physics", None),
        ([_result("pass", 0.9), _result("violation", 0.95)], "physically_impossible", None),
        ([_result("pass", 0.9), _result("violation", 0.7)], "inconclusive", "weak_violation"),
    ],
)
def test_policy(results: list[contracts.TestResult], label: str, reason: str | None) -> None:
    verdict = decide(results)
    assert (verdict.label, verdict.reason_code) == (label, reason)
    assert verdict.policy_version == POLICY_VERSION


def test_implied_g_alone_never_convicts() -> None:
    t4 = _result("violation", 0.99).model_copy(update={"test": "implied_g"})
    assert decide([t4]).label == "inconclusive"
