"""Eval commands, run from the repo root with `uv run python -m pisa_engine.evaluation`:

    synth                                  render the free synthetic set and its manifest
    run --manifest M --name N              run every clip through the pipeline (resumable)
    score --manifest M --name N            write eval/reports/N.json and N.md
    calibrate --manifest M --name N        suggest per-test thresholds, write N-calibration.md
    frame CLIP --at SECONDS --out IMAGE    save one frame, to seed a video generator

`run` uses the segmenter and planner configured in `.env` (PISA_SEGMENTER, PISA_PLANNER) and
stops at the paid-calls switch. Runs go to eval/runs/N/, which git ignores because the
evidence videos show the clips.
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from datetime import UTC, datetime
from functools import cache
from pathlib import Path

from pisa_engine.evaluation.calibration import calibrate
from pisa_engine.evaluation.manifest import load_manifest
from pisa_engine.evaluation.markdown import calibration_markdown, report_markdown
from pisa_engine.evaluation.runner import RunInfo, RunStoppedError, load_runs, run_manifest
from pisa_engine.evaluation.scoring import outcomes, score
from pisa_engine.evaluation.synthetic_set import write_synthetic_set
from pisa_engine.render.store import LocalEvidenceStore
from pisa_engine.settings import REPO_ROOT, Settings
from pisa_engine.wiring import meta_client_for, planner_for, segmenter_for

RUNS_DIR = REPO_ROOT / "eval" / "runs"
REPORTS_DIR = REPO_ROOT / "eval" / "reports"


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    command: int = args.command(args)
    return command


def _synth(args: argparse.Namespace) -> int:
    path = write_synthetic_set(args.out)
    print(f"Synthetic set written. Manifest: {_shown(path)}")
    return 0


def _run(args: argparse.Namespace) -> int:
    settings = Settings()
    manifest = load_manifest(args.manifest)
    client = cache(lambda: meta_client_for(settings))
    info = RunInfo(
        manifest=_shown(args.manifest),
        segmenter=settings.sam_model if settings.segmenter == "sam" else "color-offline",
        planner=settings.muse_spark_model if settings.planner == "muse_spark" else "whole-clip",
        data_policy="internal" if args.allow_contributor else "user",
        started_at=datetime.now(UTC),
    )
    paid = "on" if settings.paid_calls_enabled else "off"
    print(
        f"{len(manifest.clips)} clips. Segmenter {info.segmenter}, planner {info.planner}, "
        f"data policy {info.data_policy}, paid calls {paid}."
    )
    out_dir = RUNS_DIR / args.name
    try:
        asyncio.run(
            run_manifest(
                args.manifest,
                manifest,
                out_dir,
                info,
                segmenter=segmenter_for(settings, client),
                planner=planner_for(settings, client),
                evidence=LocalEvidenceStore(out_dir / "evidence"),
                force=args.force,
            )
        )
    except RunStoppedError as stopped:
        print(f"Stopped before the next clip: {stopped}. Clips already run are saved.")
        return 2
    print(f"Done. Results in {_shown(out_dir)}")
    return 0


def _score(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest)
    info, runs = load_runs(RUNS_DIR / args.name)
    report = score(manifest, runs, info, name=args.name, created_at=datetime.now(UTC))
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path, md_path = REPORTS_DIR / f"{args.name}.json", REPORTS_DIR / f"{args.name}.md"
    json_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    md_path.write_text(report_markdown(report), encoding="utf-8")
    fp, detection = report.false_positive_rate, report.detection_rate
    print(f"False positives: {fp.count} of {fp.total} real clips.")
    print(f"Detection: {detection.count} of {detection.total} generated clips.")
    print(f"Report: {_shown(md_path)}")
    return 0


def _calibrate(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest)
    _, runs = load_runs(RUNS_DIR / args.name)
    found = outcomes(manifest, runs)
    text = calibration_markdown(
        args.name, calibrate(found, max_false_positives=args.max_false_positives)
    )
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / f"{args.name}-calibration.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


def _frame(args: argparse.Namespace) -> int:
    """ffmpeg applies the phone's rotation, like the pipeline's ingest does."""
    command = [
        "ffmpeg", "-v", "error", "-y", "-ss", f"{args.at}", "-i", str(args.clip),
        "-frames:v", "1", str(args.out),
    ]  # fmt: skip
    subprocess.run(command, check=True)  # noqa: S603
    print(f"Frame at {args.at} s saved to {args.out}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m pisa_engine.evaluation")
    commands = parser.add_subparsers(required=True)

    synth = commands.add_parser("synth", help="Render the synthetic set and its manifest.")
    synth.add_argument("--out", type=Path, default=REPO_ROOT / "eval" / "raw" / "synthetic")
    synth.set_defaults(command=_synth)

    for name, handler, text in (
        ("run", _run, "Run every clip through the pipeline; skips clips already run."),
        ("score", _score, "Score a run against the truth and write the report."),
        ("calibrate", _calibrate, "Suggest per-test thresholds from a run."),
    ):
        sub = commands.add_parser(name, help=text)
        sub.add_argument("--manifest", type=Path, required=True)
        sub.add_argument("--name", required=True, help="Run name, such as phone-v1.")
        sub.set_defaults(command=handler)
        if name == "run":
            sub.add_argument("--force", action="store_true", help="Run every clip again.")
            sub.add_argument(
                "--allow-contributor",
                action="store_true",
                help="Our own clips only: allow the cheaper contributor tier, whose inputs "
                "Meta may use for training.",
            )
        if name == "calibrate":
            sub.add_argument("--max-false-positives", type=int, default=0)

    frame = commands.add_parser("frame", help="Save one frame of a clip as an image.")
    frame.add_argument("clip", type=Path)
    frame.add_argument("--at", type=float, default=0.0, help="Seconds into the clip.")
    frame.add_argument("--out", type=Path, required=True)
    frame.set_defaults(command=_frame)
    return parser


def _shown(path: Path) -> str:
    resolved = path.resolve()
    return str(resolved.relative_to(REPO_ROOT)) if resolved.is_relative_to(REPO_ROOT) else str(path)


if __name__ == "__main__":
    sys.exit(main())
