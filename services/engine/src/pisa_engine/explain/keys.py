"""Which templated sentence explains a verdict. The same rule as the web app's
explanationKey (apps/web/src/lib/result.ts), so the page and WhatsApp say the same thing."""

from __future__ import annotations

from collections.abc import Sequence

from pisa_contracts import TestResult, Verdict

EXPLANATIONS = frozenset(
    {
        "slows_down_while_falling",
        "acceleration_grows",
        "accelerates_upward",
        "pair_falls_apart",
        "bounce_gains_energy",
        "gravity_changes",
        "gravity_too_weak",
        "gravity_too_strong",
        "impossible",
        "consistent",
        "weak_violation",
        "no_measurable_acceleration",
        "depth_change",
        "camera_motion",
        "too_few_samples",
        "no_free_flight",
        "too_unclear",
        "no_measurable_events",
    }
)


def explanation_key(verdict: Verdict, tests: Sequence[TestResult]) -> str:
    if verdict.label == "consistent_with_real_physics":
        return "consistent"
    if verdict.label == "physically_impossible":
        # The strongest violation among the tests that decided the verdict.
        decisive = [
            t for t in tests if t.outcome == "violation" and t.test in verdict.decisive_tests
        ]
        strongest = max(decisive, key=lambda t: t.confidence, default=None)
        code = strongest.reason_code if strongest else None
        return code if code in EXPLANATIONS else "impossible"
    if verdict.reason_code == "weak_violation":
        # Gravity of the wrong strength is also what slow or fast playback looks like.
        gravity = next(
            (t for t in tests if t.test == "implied_g" and t.outcome == "violation"), None
        )
        code = gravity.reason_code if gravity else None
        return code if code in EXPLANATIONS else "weak_violation"
    # The tests' own reasons are more specific than the verdict's, so they come first.
    reasons = [t.reason_code for t in tests] + [verdict.reason_code]
    return next((r for r in reasons if r in EXPLANATIONS), "no_measurable_events")
