"""Human-readable reports: the eval report and the calibration, as Markdown."""

from __future__ import annotations

from pisa_contracts import EvalRate, EvalReport, EvalTruthCounts, EvalVerdictCounts, TestId
from pisa_engine.evaluation.calibration import Calibration, Score
from pisa_engine.evaluation.scoring import TEST_IDS, rate

TEST_NAMES: dict[TestId, str] = {
    "free_fall_shape": "T1 Free-fall shape",
    "galileo_pair": "T2 Galileo pair",
    "bounce_energy": "T3 Bounce energy",
    "implied_g": "T4 Implied g",
    "time_base_consistency": "T5 Time-base consistency",
}
VERDICT_NAMES = {
    "physically_impossible": "Physically impossible",
    "consistent_with_real_physics": "Consistent with real physics",
    "inconclusive": "Inconclusive",
}
SYNTHETIC_NOTE = (
    "**Synthetic set.** Every clip was rendered by the engine's own generator with known "
    "physics. These numbers show that the pipeline and the scoring work end to end; they say "
    "nothing yet about real phone videos or real video generators."
)


def report_markdown(report: EvalReport) -> str:
    lines = [f"# Eval: {report.name}", ""]
    if report.synthetic:
        lines += [SYNTHETIC_NOTE, ""]
    lines += [
        f"Engine {report.engine_version}, verdict policy {report.policy_version}, segmenter "
        f"`{report.segmenter}`, planner `{report.planner}`. "
        f"Scored {report.created_at:%Y-%m-%d %H:%M} UTC.",
        "",
        "## Headline",
        "",
        "| Measure | Result |",
        "|---|---|",
        f"| False positives: real clips judged impossible | {_rate(report.false_positive_rate)} |",
        f"| Detection: generated clips judged impossible | {_rate(report.detection_rate)} |",
        f"| Inconclusive, all clips | {_rate(report.inconclusive_rate)} |",
        f"| Conclusive verdicts that match the truth | {_rate(report.conclusive_accuracy)} |",
        "",
        "Intervals are 95% Wilson intervals: with few clips they stay wide, as they should.",
        "",
        *_baseline(report),
        "## Confusion matrix",
        "",
        *_confusion(report.confusion),
        "",
    ]
    if report.by_tag:
        lines += ["## By tag", "", "| Tag | Truth | Impossible | Consistent | Inconclusive |"]
        lines += ["|---|---|--:|--:|--:|"]
        for group in report.by_tag:
            for row in group.rows:
                if _total(row):
                    lines.append(
                        f"| {group.tag} | {row.truth} | {row.physically_impossible} | "
                        f"{row.consistent_with_real_physics} | {row.inconclusive} |"
                    )
        lines.append("")
    lines += [
        "## Physics tests",
        "",
        "Counts are clips, as real / generated. A test is decisive when a clip was judged "
        "impossible on its evidence. The closest call is the highest confidence of a violation "
        "on a real clip: how near that test came to a false positive.",
        "",
        "| Test | Measured | Violated | Decisive | Closest call on a real clip |",
        "|---|--:|--:|--:|--:|",
    ]
    for stats in report.tests:
        closest = "none" if stats.closest_call_real is None else f"{stats.closest_call_real:.2f}"
        lines.append(
            f"| {TEST_NAMES[stats.test]} | {_pair(stats.measured)} | {_pair(stats.violated)} | "
            f"{_pair(stats.decisive)} | {closest} |"
        )
    latency, cost = report.latency_s, report.cost_usd_per_clip
    lines += [
        "",
        "## Time and cost",
        "",
        f"Seconds per clip, end to end: median {_number(latency.median)}, 90th percentile "
        f"{_number(latency.p90)}, slowest {_number(latency.max)}.",
        f"Paid model calls: ${report.cost_usd:.4f} for the whole set, "
        f"${cost.median or 0:.4f} median per clip.",
        "",
        "## Clips",
        "",
        "| Clip | Truth | Tags | Verdict | Tests behind it, or reason | Seconds | USD "
        "| Muse Spark |",
        "|---|---|---|---|---|--:|--:|---|",
    ]
    for clip in report.clips:
        why = ", ".join(TEST_NAMES[t].split()[0] for t in TEST_IDS if t in clip.decisive_tests)
        if clip.verdict == "inconclusive":
            why = clip.reason_code or ""
        lines.append(
            f"| {clip.id} | {clip.truth} | {' '.join(clip.tags)} | {VERDICT_NAMES[clip.verdict]} "
            f"| {why} | {_number(clip.latency_s)} | {clip.cost_usd:.4f} | {clip.baseline or ''} |"
        )
    return "\n".join(lines) + "\n"


def calibration_markdown(name: str, calibration: Calibration) -> str:
    current, recommended = calibration.current, calibration.recommended
    lines = [
        f"# Calibration: {name}",
        "",
        f"{calibration.real_clips} real and {calibration.generated_clips} generated clips. "
        f"Allowed false positives on real clips: {calibration.max_false_positives}.",
        "",
        "| Test | Current threshold | Recommended |",
        "|---|--:|--:|",
    ]
    for test in TEST_IDS:
        if test in current.convicting_tests:
            lines.append(
                f"| {TEST_NAMES[test]} | {current.threshold(test):.2f} | "
                f"{recommended.threshold(test):.2f} |"
            )
    lines += [
        "",
        "| Policy | False positives | Detections | Inconclusive |",
        "|---|--:|--:|--:|",
        _score_row("Current", calibration.current_score),
        _score_row("Recommended", calibration.recommended_score),
        "",
    ]
    if not calibration.feasible:
        lines += [
            "No threshold set in the grid keeps false positives within the limit, so the "
            "strictest one is shown. The physics tests themselves need attention.",
            "",
        ]
    ceiling = rate(0, calibration.real_clips).ci_high
    if ceiling is not None and ceiling > 0.1:
        lines += [
            f"With {calibration.real_clips} real clips, zero false positives is still "
            f"consistent with a true rate up to {ceiling:.0%}. Treat the recommendation as "
            "provisional until the set grows.",
            "",
        ]
    return "\n".join(lines)


def _baseline(report: EvalReport) -> list[str]:
    lines = ["## Compared with asking Muse Spark", ""]
    baseline = report.baseline
    if baseline is None:
        return [*lines, "Muse Spark has not been asked about this set yet.", ""]
    pisa_silent = report.inconclusive_rate
    return [
        *lines,
        f'`{baseline.model}` was asked "{baseline.question}" about the same clips. '
        f"Its opinions cost ${baseline.cost_usd:.4f} in all.",
        "",
        "| Measure | Pisa measures | Muse Spark answers |",
        "|---|---|---|",
        f"| Real clips called fake | {_rate(report.false_positive_rate)} | "
        f"{_rate(baseline.false_positive_rate)} |",
        f"| Generated clips caught | {_rate(report.detection_rate)} | "
        f"{_rate(baseline.detection_rate)} |",
        f"| No call (inconclusive, unsure) | {_rate(pisa_silent)} | "
        f"{_rate(baseline.unsure_rate)} |",
        "",
    ]


def _rate(value: EvalRate) -> str:
    if value.value is None or value.ci_low is None or value.ci_high is None:
        return "no clips"
    return (
        f"{value.count} of {value.total} ({value.value:.0%}; "
        f"95% interval {value.ci_low:.0%} to {value.ci_high:.0%})"
    )


def _confusion(rows: list[EvalVerdictCounts]) -> list[str]:
    lines = ["| Truth | Impossible | Consistent | Inconclusive |", "|---|--:|--:|--:|"]
    for row in rows:
        lines.append(
            f"| {row.truth} | {row.physically_impossible} | "
            f"{row.consistent_with_real_physics} | {row.inconclusive} |"
        )
    return lines


def _total(row: EvalVerdictCounts) -> int:
    return row.physically_impossible + row.consistent_with_real_physics + row.inconclusive


def _pair(counts: EvalTruthCounts) -> str:
    return f"{counts.real} / {counts.generated}"


def _number(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}"


def _score_row(label: str, score: Score) -> str:
    return f"| {label} | {score.false_positives} | {score.detections} | {score.inconclusive} |"
