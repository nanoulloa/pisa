"""T1, free-fall shape: does the object accelerate the way only gravity and air allow?

Scale-free: it needs no meters and no true frame rate, only the shape of y(t). Three
polynomial models compete on each flight phase, compared with BIC:

- constant velocity (degree 1): nothing measurable is accelerating it;
- constant acceleration (degree 2): gravity alone;
- changing acceleration (degree 3): gravity with air drag, or motion that no physics allows.

Changing acceleration is not a violation by itself. Air drag can only shrink the downward
acceleration toward zero as the object speeds up. So the test convicts only when the
acceleration does what drag cannot: the object slows down while still moving down, or the
acceleration grows during the fall. Eased animation and many generated clips do both.

A perfect parabola with the wrong g still passes: slow motion makes real falls look like
that, so the strength of gravity is left to T4 and T5. When the object changes size a lot
it is moving toward or away from the camera, perspective bends the projected path, and the
test declines to judge.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from pisa_contracts import Measurement, TestOutcome, TestResult
from pisa_engine.physics.trajectory import FloatArray, Trajectory

# Residuals below this (pixels RMS) are tracking quantization, not signal. Keeps BIC finite.
NOISE_FLOOR_PX = 0.05


@dataclass(frozen=True, slots=True)
class ShapeThresholds:
    min_samples: int = 8
    # Constant acceleration must beat constant velocity by this much BIC to count as measurable.
    min_bic_gain_acceleration: float = 6.0
    # Changing acceleration must beat constant acceleration by this much BIC to be considered.
    min_bic_gain_changing: float = 10.0
    # "Slows down while falling": acceleration below -this x the largest |acceleration| ...
    min_deceleration_share: float = 0.2
    # ... while the object still moves down faster than this x its largest speed.
    min_speed_share: float = 0.1
    # "Acceleration grows": the rise across the phase, as a share of the largest |acceleration|.
    min_acceleration_rise: float = 0.6
    # Largest over smallest mask area beyond which perspective is not trusted.
    max_area_ratio: float = 1.5


@dataclass(frozen=True, slots=True)
class _Fit:
    coefficients: FloatArray
    rss: float
    bic: float


def free_fall_shape(phase: Trajectory, thresholds: ShapeThresholds | None = None) -> TestResult:
    limits = thresholds or ShapeThresholds()
    n = len(phase)
    if n < limits.min_samples:
        return _result("insufficient_data", 0.0, [_m("samples", n, "1")], "too_few_samples")

    t = phase.t - phase.t.mean()  # Centered time keeps the fits well conditioned.
    linear, quadratic, cubic = (_fit(t, phase.y, degree) for degree in (1, 2, 3))
    acceleration = 2 * float(quadratic.coefficients[0])
    gain_acceleration = linear.bic - quadratic.bic
    gain_changing = quadratic.bic - cubic.bic
    velocity_t = np.polyval(np.polyder(cubic.coefficients, 1), t)
    acceleration_t = np.polyval(np.polyder(cubic.coefficients, 2), t)
    peak_acceleration = float(np.abs(acceleration_t).max()) or 1.0
    peak_speed = float(np.abs(velocity_t).max()) or 1.0
    area_ratio = _area_ratio(phase)
    measurements = [
        _m("acceleration_px_s2", acceleration, "px/s^2"),
        _m("acceleration_start_px_s2", float(acceleration_t[0]), "px/s^2"),
        _m("acceleration_end_px_s2", float(acceleration_t[-1]), "px/s^2"),
        _m("bic_gain_constant_acceleration", gain_acceleration, "1"),
        _m("bic_gain_changing_acceleration", gain_changing, "1"),
        _m("residual_rms_px", math.sqrt(quadratic.rss / n), "px"),
        _m("area_ratio", area_ratio, "1"),
        _m("samples", n, "1"),
        _m("duration_s", float(phase.t[-1] - phase.t[0]), "s"),
    ]

    if area_ratio > limits.max_area_ratio:
        return _result("insufficient_data", 0.0, measurements, "depth_change")
    if gain_changing >= limits.min_bic_gain_changing:
        slowing_down = (acceleration_t < -limits.min_deceleration_share * peak_acceleration) & (
            velocity_t > limits.min_speed_share * peak_speed
        )
        if slowing_down.any():
            return _violation(gain_changing, measurements, "slows_down_while_falling")
        rise = float(acceleration_t[-1] - acceleration_t[0]) / peak_acceleration
        if rise >= limits.min_acceleration_rise:
            return _violation(gain_changing, measurements, "acceleration_grows")
    if gain_acceleration < limits.min_bic_gain_acceleration:
        return _result("insufficient_data", 0.0, measurements, "no_measurable_acceleration")
    if acceleration < 0:
        return _violation(gain_acceleration, measurements, "accelerates_upward")
    return _result("pass", _confidence(gain_acceleration), measurements, None)


def _fit(t: FloatArray, y: FloatArray, degree: int) -> _Fit:
    coefficients = np.polyfit(t, y, degree)
    residuals = y - np.polyval(coefficients, t)
    n = t.size
    rss = max(float(residuals @ residuals), n * NOISE_FLOOR_PX**2)
    parameters = degree + 1
    return _Fit(coefficients, rss, n * math.log(rss / n) + parameters * math.log(n))


def _area_ratio(phase: Trajectory) -> float:
    if phase.area is None or phase.area.size == 0 or float(phase.area.min()) <= 0:
        return 1.0
    return float(phase.area.max() / phase.area.min())


def _confidence(bic_gain: float) -> float:
    """Maps BIC evidence to 0..1. A gain of 10, "very strong" for Kass and Raftery, is 0.63."""
    return round(1 - math.exp(-max(bic_gain, 0.0) / 10), 4)


def _m(name: str, value: float, unit: str) -> Measurement:
    return Measurement(name=name, value=float(value), unit=unit, ci_low=None, ci_high=None)


def _violation(gain: float, measurements: list[Measurement], reason: str) -> TestResult:
    return _result("violation", _confidence(gain), measurements, reason)


def _result(
    outcome: TestOutcome, confidence: float, measurements: list[Measurement], reason: str | None
) -> TestResult:
    return TestResult(
        test="free_fall_shape",
        outcome=outcome,
        confidence=confidence,
        measurements=measurements,
        reason_code=reason,
    )
