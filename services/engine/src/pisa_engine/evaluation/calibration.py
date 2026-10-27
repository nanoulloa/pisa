"""Calibrates the verdict policy's per-test confidence thresholds on a scored eval set.

False positives on real videos matter most. Among the threshold sets that keep false positives
on real clips at or below the allowed count, the one that catches the most generated clips
wins; on a tie, the stricter one. A threshold that changes nothing on this set keeps its
current value, so a test the set never exercised is not tuned on no evidence.

Only the policy is tuned here, from saved test results. A violation the physics tests never
reported (they have their own detection limits) cannot be recovered by lowering a threshold.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from itertools import product

from pisa_contracts import TestId
from pisa_engine.evaluation.scoring import Outcome
from pisa_engine.verdict import PolicyConfig, decide

GRID = (0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.98, 0.99)


@dataclass(frozen=True, slots=True)
class Score:
    false_positives: int
    detections: int
    inconclusive: int


@dataclass(frozen=True, slots=True)
class Calibration:
    current: PolicyConfig
    current_score: Score
    recommended: PolicyConfig
    recommended_score: Score
    # False when even the strictest thresholds exceed the allowed false positives.
    feasible: bool
    real_clips: int
    generated_clips: int
    max_false_positives: int


def evaluate(found: Sequence[Outcome], policy: PolicyConfig) -> Score:
    labels = [(o.clip.truth, decide(o.tests, policy).label) for o in found]
    return Score(
        false_positives=sum(t == "real" and v == "physically_impossible" for t, v in labels),
        detections=sum(t == "generated" and v == "physically_impossible" for t, v in labels),
        inconclusive=sum(v == "inconclusive" for _, v in labels),
    )


def calibrate(
    found: Sequence[Outcome],
    current: PolicyConfig | None = None,
    *,
    max_false_positives: int = 0,
    grid: Sequence[float] = GRID,
) -> Calibration:
    base = current or PolicyConfig()
    tests = sorted(base.convicting_tests)

    def policy(thresholds: dict[TestId, float]) -> PolicyConfig:
        return replace(base, per_test=tuple(sorted(thresholds.items())))

    best: tuple[tuple[int, float], dict[TestId, float]] | None = None
    for values in product(grid, repeat=len(tests)):
        thresholds = dict(zip(tests, values, strict=True))
        found_score = evaluate(found, policy(thresholds))
        if found_score.false_positives > max_false_positives:
            continue
        key = (found_score.detections, sum(values))
        if best is None or key > best[0]:
            best = (key, thresholds)

    feasible = best is not None
    chosen = best[1] if best is not None else dict.fromkeys(tests, max(grid))
    target = evaluate(found, policy(chosen))
    for test in tests:  # Keep the current value wherever the set gives no reason to move.
        trial = {**chosen, test: base.threshold(test)}
        if evaluate(found, policy(trial)) == target:
            chosen = trial
    recommended = policy(chosen)
    return Calibration(
        current=base,
        current_score=evaluate(found, base),
        recommended=recommended,
        recommended_score=evaluate(found, recommended),
        feasible=feasible,
        real_clips=sum(o.clip.truth == "real" for o in found),
        generated_clips=sum(o.clip.truth == "generated" for o in found),
        max_false_positives=max_false_positives,
    )
