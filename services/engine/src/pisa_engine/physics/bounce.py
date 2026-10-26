"""T3, bounce energy: a bounce never leaves an object faster than it arrived.

The coefficient of restitution e = speed out / speed in at the contact is at most 1 for any
real bounce: some energy always goes into sound, heat and deformation. Both speeds come from
the constant-acceleration fits on either side of the contact, measured in the same pixels
and seconds, so the test needs no scale and no true frame rate.

The contact happens between frames. Reading both speeds at the lowest frame would bias e by
up to g / fps on each side, so the contact time is where the two fitted parabolas meet.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from pisa_contracts import TestResult
from pisa_engine.physics.fit import FreeFallFit, fit_free_fall
from pisa_engine.physics.results import measurement, result, z_confidence
from pisa_engine.physics.trajectory import Bounce


@dataclass(frozen=True, slots=True)
class BounceThresholds:
    min_samples: int = 8
    # Restitution above 1 + this, by at least min_z standard errors, convicts.
    restitution_tolerance: float = 0.05
    min_z: float = 4.0
    # An object arriving slower than this (px/s) gives no meaningful ratio.
    min_speed_in_px_s: float = 30.0


def bounce_energy(bounce: Bounce, thresholds: BounceThresholds | None = None) -> TestResult:
    limits = thresholds or BounceThresholds()
    if min(len(bounce.before), len(bounce.after)) < limits.min_samples:
        return result("bounce_energy", "insufficient_data", 0.0, [], "too_few_samples")

    before, after = fit_free_fall(bounce.before), fit_free_fall(bounce.after)
    contact_t = contact_time(before, after, bounce)
    v_in, se_in = before.velocity(contact_t)
    v_out, se_out = after.velocity(contact_t)
    # Image y points down: arriving means moving down (positive), leaving means moving up.
    if v_in < limits.min_speed_in_px_s or v_out >= 0:
        return result("bounce_energy", "insufficient_data", 0.0, [], "no_clear_bounce")

    speed_in, speed_out = v_in, -v_out
    restitution = speed_out / speed_in
    # Standard error of a ratio, propagated from both speeds.
    se = restitution * math.hypot(se_in / speed_in, se_out / speed_out)
    excess = restitution - (1 + limits.restitution_tolerance)
    measurements = [
        measurement("restitution", restitution, "1"),
        measurement("speed_in_px_s", speed_in, "px/s"),
        measurement("speed_out_px_s", speed_out, "px/s"),
        measurement("restitution_se", se, "1"),
    ]
    if excess > 0 and excess / se >= limits.min_z:
        return result(
            "bounce_energy",
            "violation",
            z_confidence(excess / se),
            measurements,
            "bounce_gains_energy",
        )
    if excess <= 0:
        return result("bounce_energy", "pass", z_confidence(-excess / se), measurements)
    return result("bounce_energy", "insufficient_data", 0.0, measurements, "too_noisy")


def contact_time(before: FreeFallFit, after: FreeFallFit, bounce: Bounce) -> float:
    """Where the parabolas cross between the last frame before and the first frame after."""
    low, high = float(bounce.before.t[-1]), float(bounce.after.t[0])
    roots = np.roots(before.polynomial() - after.polynomial())
    inside = [float(r.real) for r in roots if abs(r.imag) < 1e-9 and low <= r.real <= high]
    if not inside:
        return bounce.contact_t
    return min(inside, key=lambda t: abs(t - bounce.contact_t))
