"""Which tests run on which parts of a clip. Pure: flights in, test results out.

- T1 free-fall shape on every flight phase.
- T3 bounce energy on every bounce.
- T5 time-base consistency on every object with two or more flights.
- T2 Galileo pair on the first flight of every two objects released together.
- T4 implied g waits for a scale from the planner, so it does not run here yet.
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import combinations

from pisa_contracts import TestResult
from pisa_engine.physics.bounce import bounce_energy
from pisa_engine.physics.consistency import time_base_consistency
from pisa_engine.physics.pair import galileo_pair
from pisa_engine.physics.shape import free_fall_shape
from pisa_engine.physics.trajectory import Flight


def run_tests(flights: Sequence[Flight]) -> list[TestResult]:
    """`flights` holds one entry per object and shot."""
    results: list[TestResult] = []
    for flight in flights:
        results.extend(free_fall_shape(phase) for phase in flight.phases)
        results.extend(bounce_energy(bounce) for bounce in flight.bounces)
        if len(flight.phases) >= 2:
            results.append(time_base_consistency(flight.phases))
    first_phases = [flight.phases[0] for flight in flights if flight.phases]
    for first, second in combinations(first_phases, 2):
        pair = galileo_pair(first, second)
        if pair.outcome != "not_applicable":  # Most pairs of objects are not a Galileo drop.
            results.append(pair)
    return results
