"""What the explainer may say, and the check that it said nothing else.

The facts are a small JSON of the verdict and the measurements people can understand (no
pixels, no fit statistics), each number already rounded the way it may be quoted. The check
reads every number written in the text, in the conventions of its language, and accepts it
only if it is one of the facts, rounded no more finely than given.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from typing import Any

from pisa_contracts import Locale, Plan, TestResult, Verdict
from pisa_engine.physics.implied_g import EARTH_G

# Comma decimals: "1,64" is one point six four, and "3.921" is three thousand nine hundred.
_COMMA_DECIMAL_LOCALES = frozenset({"es", "pt-BR"})
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


def explanation_facts(
    verdict: Verdict, results: Sequence[TestResult], plan: Plan
) -> dict[str, Any]:
    tests = [_test_facts(r) for r in results if r.outcome in ("pass", "violation")]
    return {
        "verdict": verdict.label,
        "verdict_reason": verdict.reason_code,
        "decisive_tests": list(verdict.decisive_tests),
        "tests": tests,
        "not_measured_because": sorted(
            {r.reason_code for r in results if r.outcome == "insufficient_data" and r.reason_code}
        ),
        "moving_objects": sorted({p for e in plan.events for p in e.object_phrases}),
        "slow_motion_suspected": plan.camera.slow_motion_suspected,
        "constants": {
            "earth_gravity_m_s2": EARTH_G,
            "highest_possible_speed_kept_after_bounce_percent": 100,
            "ratio_real_physics_gives": 1,
        },
    }


def _test_facts(test: TestResult) -> dict[str, Any]:
    values = {m.name: m for m in test.measurements}
    facts: dict[str, Any] = {"test": test.test, "outcome": test.outcome, "reason": test.reason_code}
    if test.test == "bounce_energy" and "restitution" in values:
        facts["speed_kept_after_bounce_percent"] = round(values["restitution"].value * 100)
    if test.test in ("galileo_pair", "time_base_consistency") and "acceleration_ratio" in values:
        ratio = values["acceleration_ratio"].value
        facts["acceleration_ratio"] = round(max(ratio, 1 / ratio) if ratio > 0 else ratio, 2)
    if test.test == "implied_g" and "implied_g" in values:
        g = values["implied_g"]
        facts["gravity_m_s2"] = round(g.value, 1)
        if g.ci_low is not None and g.ci_high is not None:
            facts["gravity_range_m_s2"] = [round(g.ci_low, 1), round(g.ci_high, 1)]
        if "earth_g_ratio" in values and values["earth_g_ratio"].value > 0:
            ratio = values["earth_g_ratio"].value
            facts["times_weaker_than_earth"] = round(ratio, 1) if ratio >= 1 else None
            facts["times_stronger_than_earth"] = round(1 / ratio, 1) if ratio < 1 else None
    if test.test == "time_base_consistency" and "flights" in values:
        facts["flights_compared"] = int(values["flights"].value)
    return facts


def numbers_in(text: str, locale: Locale) -> list[tuple[float, int]]:
    """Every number written in `text`, as (value, decimals shown)."""
    found = []
    for token in _NUMBER.findall(text):
        normalized = _normalize(token, comma_decimal=locale in _COMMA_DECIMAL_LOCALES)
        decimals = len(normalized.split(".")[1]) if "." in normalized else 0
        found.append((float(normalized), decimals))
    return found


def unsupported_numbers(text: str, facts: dict[str, Any], locale: Locale) -> list[float]:
    """Numbers in `text` that are not facts, allowing only coarser rounding of a fact."""
    allowed = list(_leaves(facts))
    return [
        value
        for value, decimals in numbers_in(text, locale)
        if not any(abs(value - fact) <= 0.5 * 10**-decimals + 1e-9 for fact in allowed)
    ]


def _normalize(token: str, *, comma_decimal: bool) -> str:
    decimal, group = (",", ".") if comma_decimal else (".", ",")
    if decimal in token:
        whole, _, fraction = token.rpartition(decimal)
        return whole.replace(group, "") + "." + fraction
    if re.fullmatch(rf"\d{{1,3}}(?:\{group}\d{{3}})+", token):
        return token.replace(group, "")  # Grouped thousands.
    return token.replace(group, ".")  # The other convention's decimal point.


def _leaves(node: Any) -> Iterator[float]:
    if isinstance(node, bool) or node is None or isinstance(node, str):
        return
    if isinstance(node, int | float):
        yield float(node)
    elif isinstance(node, dict):
        for value in node.values():
            yield from _leaves(value)
    elif isinstance(node, list):
        for value in node:
            yield from _leaves(value)
