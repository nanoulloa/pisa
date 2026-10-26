"""T2, Galileo pair: two objects released together fall with the same acceleration.

Scale-free and frame-rate-free: it compares two accelerations measured in the same pixels
and the same seconds, so neither the real size of anything nor slow motion matters. It
applies only when both objects leave their hold within a few frames of each other. Dense
objects side by side at a similar distance from the camera are the intended case; very
different depths change pixel accelerations, which is why the tolerance is wide.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from pisa_contracts import TestResult
from pisa_engine.physics.fit import fit_free_fall
from pisa_engine.physics.results import measurement, result, z_confidence
from pisa_engine.physics.trajectory import Trajectory


@dataclass(frozen=True, slots=True)
class PairThresholds:
    min_samples: int = 8
    # Releases further apart than this are two separate drops, not a pair.
    max_release_gap_s: float = 0.05
    # Accelerations within this fraction of each other pass...
    max_relative_difference: float = 0.2
    # ...and a larger difference convicts only when it stands this many standard errors out.
    min_z: float = 4.0


def galileo_pair(
    first: Trajectory, second: Trajectory, thresholds: PairThresholds | None = None
) -> TestResult:
    limits = thresholds or PairThresholds()
    gap = abs(float(first.t[0]) - float(second.t[0]))
    if gap > limits.max_release_gap_s:
        return result(
            "galileo_pair",
            "not_applicable",
            0.0,
            [measurement("release_gap_s", gap, "s")],
            "not_released_together",
        )
    if min(len(first), len(second)) < limits.min_samples:
        return result("galileo_pair", "insufficient_data", 0.0, [], "too_few_samples")

    a, b = fit_free_fall(first), fit_free_fall(second)
    mean = (abs(a.acceleration) + abs(b.acceleration)) / 2 or 1.0
    difference = abs(a.acceleration - b.acceleration)
    se = math.hypot(a.acceleration_se, b.acceleration_se)
    relative = difference / mean
    z = difference / se
    measurements = [
        measurement("acceleration_ratio", a.acceleration / b.acceleration, "1"),
        measurement("acceleration_first_px_s2", a.acceleration, "px/s^2"),
        measurement("acceleration_second_px_s2", b.acceleration, "px/s^2"),
        measurement("release_gap_s", gap, "s"),
        measurement("z_score", z, "1"),
    ]
    if relative >= limits.max_relative_difference and z >= limits.min_z:
        return result(
            "galileo_pair", "violation", z_confidence(z), measurements, "pair_falls_apart"
        )
    if relative < limits.max_relative_difference:
        # How many standard errors the difference sits inside the tolerance.
        margin = (limits.max_relative_difference - relative) * mean / se
        return result("galileo_pair", "pass", z_confidence(margin), measurements)
    return result("galileo_pair", "insufficient_data", 0.0, measurements, "too_noisy")
