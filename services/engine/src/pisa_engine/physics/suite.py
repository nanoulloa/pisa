"""Which tests run on which parts of a clip. Pure: flights in, test results out.

- T1 free-fall shape on every flight phase.
- T3 bounce energy on every bounce.
- T5 time-base consistency on every object with two or more flights.
- T2 Galileo pair on the first flight of every two objects released together.
- T4 implied g on every flight that passed T1, when the plan gave a scale. In slow motion the
  time base is unknown, so it is not applicable.
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import combinations

from pisa_contracts import TestResult
from pisa_engine.physics.bounce import bounce_energy
from pisa_engine.physics.consistency import time_base_consistency
from pisa_engine.physics.fit import fit_free_fall
from pisa_engine.physics.implied_g import Scale, implied_gravity
from pisa_engine.physics.pair import galileo_pair
from pisa_engine.physics.results import result
from pisa_engine.physics.shape import free_fall_shape
from pisa_engine.physics.trajectory import Flight


def run_tests(
    flights: Sequence[Flight], *, scale: Scale | None = None, slow_motion: bool = False
) -> list[TestResult]:
    """`flights` holds one entry per object, shot and event window."""
    results: list[TestResult] = []
    for flight in flights:
        for phase in flight.phases:
            shape = free_fall_shape(phase)
            results.append(shape)
            # Implied g means something only for a flight that is a clean parabola.
            if scale is not None and shape.outcome == "pass":
                results.append(
                    result("implied_g", "not_applicable", 0.0, [], "slow_motion")
                    if slow_motion
                    else implied_gravity(fit_free_fall(phase), scale)
                )
        results.extend(bounce_energy(bounce) for bounce in flight.bounces)
        if len(flight.phases) >= 2:
            results.append(time_base_consistency(flight.phases))
    first_phases = [flight.phases[0] for flight in flights if flight.phases]
    for first, second in combinations(first_phases, 2):
        pair = galileo_pair(first, second)
        if pair.outcome != "not_applicable":  # Most pairs of objects are not a Galileo drop.
            results.append(pair)
    return results
