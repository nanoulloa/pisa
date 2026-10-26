"""T2 to T5 on trajectories with known physics: they pass real motion and catch the rest."""

from __future__ import annotations

import numpy as np
import pytest

import pisa_contracts as contracts
from pisa_engine.physics.bounce import bounce_energy
from pisa_engine.physics.consistency import time_base_consistency
from pisa_engine.physics.fit import fit_free_fall
from pisa_engine.physics.implied_g import EARTH_G, Scale, implied_gravity
from pisa_engine.physics.pair import galileo_pair
from pisa_engine.physics.trajectory import Bounce, Trajectory, flight_phases, segment_flight
from pisa_engine.synthetic import BallScene

PX_PER_M = 400.0


def _trajectory(rows: np.ndarray) -> Trajectory:
    return Trajectory(t=rows[:, 0], x=rows[:, 1], y=rows[:, 2])


def _noisy(trajectory: Trajectory, sigma_px: float, rng: np.random.Generator) -> Trajectory:
    n = len(trajectory)
    return Trajectory(
        t=trajectory.t,
        x=trajectory.x + rng.normal(0, sigma_px, n),
        y=trajectory.y + rng.normal(0, sigma_px, n),
    )


def _measurement(result: contracts.TestResult, name: str) -> float:
    return next(m.value for m in result.measurements if m.name == name)


def _pair(g_first: float, g_second: float, *, hold_s: float = 0.1) -> tuple[Trajectory, Trajectory]:
    scene = BallScene(g_mps2=g_first, companion_g_mps2=g_second, hold_s=hold_s, duration_s=0.7)
    companion = scene.companion_trajectory()
    assert companion is not None
    (first,) = flight_phases(_trajectory(scene.true_trajectory()))
    (second,) = flight_phases(_trajectory(companion))
    return first, second


def _bouncing(restitution: float, *, y0_px: float = 80.0, duration_s: float = 1.4) -> Trajectory:
    scene = BallScene(
        profile="bounce", restitution=restitution, y0_px=y0_px, duration_s=duration_s, vx_mps=0.5
    )
    return _trajectory(scene.true_trajectory())


# Fit


def test_fit_recovers_acceleration_and_an_honest_standard_error() -> None:
    clean = _trajectory(BallScene(duration_s=0.5).true_trajectory())
    rng = np.random.default_rng(7)
    fits = [fit_free_fall(_noisy(clean, 1.0, rng)) for _ in range(400)]
    accelerations = np.array([fit.acceleration for fit in fits])
    assert accelerations.mean() == pytest.approx(EARTH_G * PX_PER_M, rel=0.01)
    # The reported standard error matches the spread across repeated noisy clips.
    reported = np.median([fit.acceleration_se for fit in fits])
    assert reported == pytest.approx(accelerations.std(), rel=0.15)


def test_fit_polynomial_is_the_same_parabola() -> None:
    fit = fit_free_fall(_trajectory(BallScene(hold_s=0.0).true_trajectory()))
    t = np.linspace(0.1, 0.5, 5)
    tau = t - fit.t_mid
    assert np.polyval(fit.polynomial(), t) == pytest.approx(np.polyval(fit.coefficients, tau))


# T2 Galileo pair


@pytest.mark.parametrize("g", [EARTH_G, 2.0])  # Earth, and the same pair in slow motion.
def test_pair_falling_together_passes(g: float) -> None:
    result = galileo_pair(*_pair(g, g))
    assert result.outcome == "pass"
    assert _measurement(result, "acceleration_ratio") == pytest.approx(1.0, abs=1e-6)
    assert result.confidence > 0.9


def test_pair_falling_apart_is_a_violation() -> None:
    result = galileo_pair(*_pair(EARTH_G, 6.0))
    assert (result.outcome, result.reason_code) == ("violation", "pair_falls_apart")
    assert _measurement(result, "acceleration_ratio") == pytest.approx(EARTH_G / 6.0, rel=1e-6)
    assert result.confidence > 0.9


def test_objects_released_at_different_times_are_not_a_pair() -> None:
    early, _ = _pair(EARTH_G, EARTH_G, hold_s=0.0)
    _, late = _pair(EARTH_G, EARTH_G, hold_s=0.2)
    result = galileo_pair(early, late)
    assert (result.outcome, result.reason_code) == ("not_applicable", "not_released_together")


def test_noisy_real_pairs_are_never_called_impossible() -> None:
    first, second = _pair(EARTH_G, EARTH_G)
    rng = np.random.default_rng(11)
    outcomes = [
        galileo_pair(_noisy(first, 1.0, rng), _noisy(second, 1.0, rng)).outcome for _ in range(300)
    ]
    assert "violation" not in outcomes
    assert outcomes.count("pass") >= 285


# T3 bounce energy


def test_a_real_bounce_passes_and_measures_restitution() -> None:
    (bounce,) = segment_flight(_bouncing(0.7)).bounces
    result = bounce_energy(bounce)
    assert result.outcome == "pass"
    assert _measurement(result, "restitution") == pytest.approx(0.7, abs=0.01)


def test_a_bounce_that_gains_energy_is_a_violation() -> None:
    (bounce,) = segment_flight(_bouncing(1.2, y0_px=400.0, duration_s=1.0)).bounces
    result = bounce_energy(bounce)
    assert (result.outcome, result.reason_code) == ("violation", "bounce_gains_energy")
    assert _measurement(result, "restitution") == pytest.approx(1.2, abs=0.02)
    assert result.confidence > 0.9


@pytest.mark.parametrize("restitution", [0.85, 1.0])  # A superball, and the ideal limit.
def test_noisy_lively_bounces_are_never_called_impossible(restitution: float) -> None:
    clean = _bouncing(restitution, y0_px=400.0, duration_s=1.0)
    rng = np.random.default_rng(13)
    outcomes: list[str] = []
    for _ in range(200):
        bounces = segment_flight(_noisy(clean, 1.0, rng)).bounces
        outcomes.extend(bounce_energy(bounce).outcome for bounce in bounces)
    assert len(outcomes) >= 190  # The bounce is found despite the noise.
    assert "violation" not in outcomes


def test_an_object_arriving_too_slowly_gives_no_ratio() -> None:
    t = np.arange(10) / 60
    before = Trajectory(t=t, x=100 + 300 * t, y=500 + 10 * t)  # 10 px/s: barely moving.
    t_after = t + 0.2
    after = Trajectory(t=t_after, x=100 + 300 * t_after, y=502 - 200 * t)
    result = bounce_energy(Bounce(before, after, contact_t=0.18, contact_y=502.0))
    assert (result.outcome, result.reason_code) == ("insufficient_data", "no_clear_bounce")


# T5 time-base consistency


def test_every_flight_of_a_real_bounce_shows_the_same_gravity() -> None:
    result = time_base_consistency(segment_flight(_bouncing(0.7)).phases)
    assert result.outcome == "pass"
    assert _measurement(result, "flights") == 2
    assert _measurement(result, "acceleration_ratio") == pytest.approx(1.0, abs=1e-6)


def test_gravity_that_changes_between_flights_is_a_violation() -> None:
    t = np.arange(40) / 60
    first = Trajectory(t=t, x=100 + 50 * t, y=100 + 0.5 * EARTH_G * PX_PER_M * t**2)
    t2 = 1.0 + t
    second = Trajectory(t=t2, x=100 + 50 * t2, y=100 - 900 * t + 0.5 * 4.0 * PX_PER_M * t**2)
    result = time_base_consistency([first, second])
    assert (result.outcome, result.reason_code) == ("violation", "gravity_changes")
    assert _measurement(result, "acceleration_ratio") == pytest.approx(EARTH_G / 4.0, rel=1e-6)


def test_one_flight_cannot_be_compared() -> None:
    (phase,) = flight_phases(_trajectory(BallScene().true_trajectory()))
    result = time_base_consistency([phase])
    assert (result.outcome, result.reason_code) == ("not_applicable", "fewer_than_two_flights")


def test_noisy_real_bounces_keep_one_gravity() -> None:
    clean = _bouncing(0.7)
    rng = np.random.default_rng(17)
    outcomes = [
        time_base_consistency(segment_flight(_noisy(clean, 1.0, rng)).phases).outcome
        for _ in range(200)
    ]
    assert "violation" not in outcomes
    assert outcomes.count("pass") >= 190


# T4 implied g


def test_earth_gravity_with_a_known_scale_passes() -> None:
    fit = fit_free_fall(_trajectory(BallScene().true_trajectory()))
    result = implied_gravity(fit, Scale(low_px_per_m=380.0, high_px_per_m=420.0))
    assert result.outcome == "pass"
    g = next(m for m in result.measurements if m.name == "implied_g")
    assert g.value == pytest.approx(EARTH_G, rel=0.02)
    assert g.ci_low is not None
    assert g.ci_high is not None
    assert g.ci_low < EARTH_G < g.ci_high


def test_moon_gravity_with_a_known_scale_is_too_weak() -> None:
    fit = fit_free_fall(_trajectory(BallScene(g_mps2=1.62).true_trajectory()))
    result = implied_gravity(fit, Scale(low_px_per_m=380.0, high_px_per_m=420.0))
    assert (result.outcome, result.reason_code) == ("violation", "gravity_too_weak")
    assert _measurement(result, "implied_g") == pytest.approx(1.62, rel=0.02)
    assert _measurement(result, "earth_g_ratio") == pytest.approx(EARTH_G / 1.62, rel=0.02)


def test_implied_g_needs_a_scale_and_is_deterministic() -> None:
    fit = fit_free_fall(_trajectory(BallScene().true_trajectory()))
    assert implied_gravity(fit, None).reason_code == "no_scale"
    scale = Scale(low_px_per_m=300.0, high_px_per_m=500.0)
    assert implied_gravity(fit, scale) == implied_gravity(fit, scale)
