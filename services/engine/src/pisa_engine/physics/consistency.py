"""T5, time-base consistency: every free flight of one object shows the same gravity.

Slow motion stretches every moment of a clip equally, so it scales all accelerations by the
same factor: a real slowed-down clip still shows one acceleration. Generated clips often
change it from one flight to the next. Comparing flights of the same object keeps the camera
distance the same, so pixels compare directly.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from pisa_contracts import TestResult
from pisa_engine.physics.fit import fit_free_fall
from pisa_engine.physics.results import measurement, result, z_confidence
from pisa_engine.physics.trajectory import Trajectory


@dataclass(frozen=True, slots=True)
class ConsistencyThresholds:
    min_samples: int = 8
    # Accelerations may differ by up to this fraction (air drag differs between flights)...
    max_relative_difference: float = 0.25
    # ...and a larger difference convicts only this many standard errors out.
    min_z: float = 4.0


def time_base_consistency(
    phases: Sequence[Trajectory], thresholds: ConsistencyThresholds | None = None
) -> TestResult:
    limits = thresholds or ConsistencyThresholds()
    usable = [phase for phase in phases if len(phase) >= limits.min_samples]
    if len(usable) < 2:
        return result("time_base_consistency", "not_applicable", 0.0, [], "fewer_than_two_flights")

    fits = [fit_free_fall(phase) for phase in usable]
    strongest = max(fits, key=lambda fit: fit.acceleration)
    weakest = min(fits, key=lambda fit: fit.acceleration)
    difference = strongest.acceleration - weakest.acceleration
    mean = (abs(strongest.acceleration) + abs(weakest.acceleration)) / 2 or 1.0
    se = math.hypot(strongest.acceleration_se, weakest.acceleration_se)
    relative, z = difference / mean, difference / se
    measurements = [
        measurement("acceleration_ratio", strongest.acceleration / weakest.acceleration, "1"),
        measurement("acceleration_max_px_s2", strongest.acceleration, "px/s^2"),
        measurement("acceleration_min_px_s2", weakest.acceleration, "px/s^2"),
        measurement("flights", len(fits), "1"),
        measurement("z_score", z, "1"),
    ]
    if relative >= limits.max_relative_difference and z >= limits.min_z:
        return result(
            "time_base_consistency", "violation", z_confidence(z), measurements, "gravity_changes"
        )
    if relative < limits.max_relative_difference:
        margin = (limits.max_relative_difference - relative) * mean / se
        return result("time_base_consistency", "pass", z_confidence(margin), measurements)
    return result("time_base_consistency", "insufficient_data", 0.0, measurements, "too_noisy")
