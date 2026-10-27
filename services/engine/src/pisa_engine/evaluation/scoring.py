"""Scores saved runs against the truth. Pure: manifest and saved results in, report out.

Verdicts are decided again from the saved test results, so a different verdict policy can be
scored without running a model again (that is how calibration works). With the policy the run
used, the verdicts are the ones the pipeline gave.

A job that failed counts as inconclusive, with its error code as the reason: for someone who
forwarded the clip, Pisa had no answer.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import get_args

from pisa_contracts import (
    EvalClip,
    EvalGroup,
    EvalRate,
    EvalReport,
    EvalSummary,
    EvalTestStats,
    EvalTruth,
    EvalTruthCounts,
    EvalVerdictCounts,
    TestId,
    TestResult,
    Verdict,
    VerdictLabel,
)
from pisa_engine import __version__
from pisa_engine.evaluation.manifest import Clip, Manifest
from pisa_engine.evaluation.runner import ClipRun, RunInfo
from pisa_engine.verdict import POLICY_VERSION, PolicyConfig, verdict_for

TRUTHS: tuple[EvalTruth, ...] = get_args(EvalTruth.__value__)
TEST_IDS: tuple[TestId, ...] = get_args(TestId.__value__)
_Z95 = 1.959964


@dataclass(frozen=True, slots=True)
class Outcome:
    """One clip as the scorer sees it."""

    clip: Clip
    verdict: Verdict
    tests: Sequence[TestResult]
    latency_s: float | None
    cost_usd: float


def outcomes(
    manifest: Manifest, runs: Mapping[str, ClipRun], policy: PolicyConfig | None = None
) -> list[Outcome]:
    not_run = [clip.id for clip in manifest.clips if clip.id not in runs]
    if not_run:
        raise ValueError(f"clips without a saved run: {', '.join(not_run)}")
    found = []
    for clip in manifest.clips:
        run = runs[clip.id]
        result = run.result
        if result is None or result.plan is None:
            verdict = Verdict(
                label="inconclusive",
                policy_version=POLICY_VERSION,
                decisive_tests=[],
                reason_code=f"error:{run.error or 'unknown'}",
            )
            found.append(Outcome(clip, verdict, [], run.latency_s, 0.0))
            continue
        verdict = verdict_for(result.plan, result.tests, policy)
        cost = sum(entry.usd for entry in result.costs)
        found.append(Outcome(clip, verdict, result.tests, run.latency_s, cost))
    return found


def score(
    manifest: Manifest,
    runs: Mapping[str, ClipRun],
    info: RunInfo,
    *,
    name: str,
    created_at: datetime,
    policy: PolicyConfig | None = None,
) -> EvalReport:
    found = outcomes(manifest, runs, policy)
    real = [o for o in found if o.clip.truth == "real"]
    generated = [o for o in found if o.clip.truth == "generated"]
    conclusive = [o for o in found if o.verdict.label != "inconclusive"]
    tags = sorted({tag for o in found for tag in o.clip.tags})
    costs = [o.cost_usd for o in found]
    return EvalReport(
        name=name,
        created_at=created_at,
        engine_version=__version__,
        policy_version=POLICY_VERSION,
        synthetic=manifest.synthetic,
        segmenter=info.segmenter,
        planner=info.planner,
        confusion=_confusion(found),
        false_positive_rate=rate(_count(real, "physically_impossible"), len(real)),
        detection_rate=rate(_count(generated, "physically_impossible"), len(generated)),
        inconclusive_rate=rate(_count(found, "inconclusive"), len(found)),
        conclusive_accuracy=rate(sum(_correct(o) for o in conclusive), len(conclusive)),
        by_tag=[
            EvalGroup(tag=tag, rows=_confusion([o for o in found if tag in o.clip.tags]))
            for tag in tags
        ],
        tests=[_test_stats(test, found) for test in TEST_IDS],
        latency_s=summary([o.latency_s for o in found if o.latency_s is not None]),
        cost_usd=round(sum(costs), 6),
        cost_usd_per_clip=summary(costs),
        clips=[
            EvalClip(
                id=o.clip.id,
                truth=o.clip.truth,
                tags=o.clip.tags,
                verdict=o.verdict.label,
                reason_code=o.verdict.reason_code,
                decisive_tests=o.verdict.decisive_tests,
                latency_s=o.latency_s,
                cost_usd=round(o.cost_usd, 6),
            )
            for o in found
        ],
    )


def rate(count: int, total: int) -> EvalRate:
    """`count` of `total` with its 95% Wilson interval. Zero false positives in 10 clips
    still allows a true rate up to 28%, and the report should say so."""
    if total == 0:
        return EvalRate(count=0, total=0, value=None, ci_low=None, ci_high=None)
    p = count / total
    z2 = _Z95**2
    center = (p + z2 / (2 * total)) / (1 + z2 / total)
    half = _Z95 * math.sqrt(p * (1 - p) / total + z2 / (4 * total**2)) / (1 + z2 / total)
    return EvalRate(
        count=count,
        total=total,
        value=round(p, 4),
        ci_low=round(max(0.0, center - half), 4),
        ci_high=round(min(1.0, center + half), 4),
    )


def summary(values: Sequence[float]) -> EvalSummary:
    """Median, 90th percentile (nearest rank) and maximum."""
    if not values:
        return EvalSummary(median=None, p90=None, max=None)
    ordered = sorted(values)
    middle = len(ordered) // 2
    median = ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2
    p90 = ordered[max(0, math.ceil(0.9 * len(ordered)) - 1)]
    return EvalSummary(median=round(median, 4), p90=round(p90, 4), max=round(ordered[-1], 4))


def _correct(outcome: Outcome) -> bool:
    expected: VerdictLabel = (
        "consistent_with_real_physics" if outcome.clip.truth == "real" else "physically_impossible"
    )
    return outcome.verdict.label == expected


def _count(found: Sequence[Outcome], label: VerdictLabel) -> int:
    return sum(o.verdict.label == label for o in found)


def _confusion(found: Sequence[Outcome]) -> list[EvalVerdictCounts]:
    rows = []
    for truth in TRUTHS:
        mine = [o for o in found if o.clip.truth == truth]
        rows.append(
            EvalVerdictCounts(
                truth=truth,
                physically_impossible=_count(mine, "physically_impossible"),
                consistent_with_real_physics=_count(mine, "consistent_with_real_physics"),
                inconclusive=_count(mine, "inconclusive"),
            )
        )
    return rows


def _test_stats(test: TestId, found: Sequence[Outcome]) -> EvalTestStats:
    def clips(matches: Callable[[Outcome], bool]) -> EvalTruthCounts:
        return EvalTruthCounts(
            real=sum(matches(o) for o in found if o.clip.truth == "real"),
            generated=sum(matches(o) for o in found if o.clip.truth == "generated"),
        )

    def results(o: Outcome) -> list[TestResult]:
        return [r for r in o.tests if r.test == test]

    false_alarms = [
        r.confidence
        for o in found
        if o.clip.truth == "real"
        for r in results(o)
        if r.outcome == "violation"
    ]
    return EvalTestStats(
        test=test,
        measured=clips(lambda o: any(r.outcome in ("pass", "violation") for r in results(o))),
        violated=clips(lambda o: any(r.outcome == "violation" for r in results(o))),
        decisive=clips(
            lambda o: (
                o.verdict.label == "physically_impossible" and test in o.verdict.decisive_tests
            )
        ),
        closest_call_real=max(false_alarms, default=None),
    )
