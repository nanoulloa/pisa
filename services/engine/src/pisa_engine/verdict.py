"""Verdict policy: from test results to one of three answers. Deterministic and versioned.

- Physically impossible: at least one high-confidence violation of a scale-free test.
  Implied g (T4) alone never convicts in this version: it needs a known time base.
- Consistent with real physics: at least one measured test, and every measured test passes.
- Inconclusive otherwise, with the reason.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from pisa_contracts import TestId, TestResult, Verdict, VerdictLabel

POLICY_VERSION = "0.1.0"


@dataclass(frozen=True, slots=True)
class PolicyConfig:
    min_violation_confidence: float = 0.9
    convicting_tests: frozenset[TestId] = frozenset(
        {"free_fall_shape", "galileo_pair", "bounce_energy", "time_base_consistency"}
    )


def decide(results: Sequence[TestResult], config: PolicyConfig | None = None) -> Verdict:
    policy = config or PolicyConfig()
    convicting = [
        r
        for r in results
        if r.outcome == "violation"
        and r.test in policy.convicting_tests
        and r.confidence >= policy.min_violation_confidence
    ]
    if convicting:
        return _verdict("physically_impossible", _tests(convicting), None)

    measured = [r for r in results if r.outcome in ("pass", "violation")]
    if not measured:
        return _verdict("inconclusive", [], "no_measurable_events")
    if any(r.outcome == "violation" for r in measured):
        return _verdict("inconclusive", _tests(measured), "weak_violation")
    return _verdict("consistent_with_real_physics", _tests(measured), None)


def _tests(results: Sequence[TestResult]) -> list[TestId]:
    return sorted({r.test for r in results})


def _verdict(label: VerdictLabel, decisive: list[TestId], reason: str | None) -> Verdict:
    return Verdict(
        label=label, policy_version=POLICY_VERSION, decisive_tests=decisive, reason_code=reason
    )
