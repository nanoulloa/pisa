"""Building TestResults the same way in every test."""

from __future__ import annotations

import math

from pisa_contracts import Measurement, TestId, TestOutcome, TestResult


def measurement(
    name: str,
    value: float,
    unit: str,
    ci: tuple[float, float] | None = None,
) -> Measurement:
    low, high = ci if ci is not None else (None, None)
    return Measurement(name=name, value=float(value), unit=unit, ci_low=low, ci_high=high)


def result(
    test: TestId,
    outcome: TestOutcome,
    confidence: float,
    measurements: list[Measurement],
    reason: str | None = None,
) -> TestResult:
    return TestResult(
        test=test,
        outcome=outcome,
        confidence=round(min(max(confidence, 0.0), 1.0), 4),
        measurements=measurements,
        reason_code=reason,
    )


def bic_confidence(bic_gain: float) -> float:
    """BIC evidence to 0..1. A gain of 10, "very strong" for Kass and Raftery, is 0.63."""
    return 1 - math.exp(-max(bic_gain, 0.0) / 10)


def z_confidence(z: float) -> float:
    """Standard scores to 0..1 on the same curve: z = 4 is 0.63, z = 9.2 reaches 0.9."""
    return 1 - math.exp(-max(z, 0.0) / 4)
