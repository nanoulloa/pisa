"""T4, implied gravity: the acceleration in meters per second squared.

Needs two things the other tests avoid: a scale (pixels per meter, from an object of roughly
known size in the plane of motion) and a true time base. The scale is a range, and the fit
has noise, so g comes out as an interval from a deterministic Monte Carlo. Slow motion
divides g by the square of the slow-down, so on its own this test can show that a fall looks
wrong but never proves it; the verdict policy does not let it convict alone.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pisa_contracts import TestResult
from pisa_engine.physics.fit import FreeFallFit
from pisa_engine.physics.results import measurement, result

EARTH_G = 9.81


@dataclass(frozen=True, slots=True)
class Scale:
    """Pixels per meter in the plane of motion, as a plausible range."""

    low_px_per_m: float
    high_px_per_m: float


def implied_gravity(
    fit: FreeFallFit, scale: Scale | None, *, draws: int = 4000, seed: int = 0
) -> TestResult:
    if scale is None:
        return result("implied_g", "not_applicable", 0.0, [], "no_scale")

    rng = np.random.default_rng(seed)  # Fixed seed: the same clip always gets the same interval.
    pixels_per_meter = rng.uniform(scale.low_px_per_m, scale.high_px_per_m, draws)
    acceleration = rng.normal(fit.acceleration, fit.acceleration_se, draws)
    g = acceleration / pixels_per_meter
    low, median, high = (float(v) for v in np.percentile(g, [5, 50, 95]))
    measurements = [
        measurement("implied_g", median, "m/s^2", (low, high)),
        measurement("earth_g_ratio", EARTH_G / median if median > 0 else 0.0, "1"),
    ]
    if low <= EARTH_G <= high:
        return result("implied_g", "pass", 0.9, measurements)
    width = high - low or 1.0
    distance = (low - EARTH_G if low > EARTH_G else EARTH_G - high) / width
    reason = "gravity_too_strong" if low > EARTH_G else "gravity_too_weak"
    return result("implied_g", "violation", min(0.99, 0.6 + distance), measurements, reason)
