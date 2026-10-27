"""Runs every clip of a manifest through the real pipeline and saves what came out.

This is the expensive half of the eval (with SAM and Muse Spark switched on it pays per
clip), so each clip's outcome is written as soon as it is known and a rerun skips the clips
already done. Scoring and calibration only read these files and never call a model.

The explainer is left out: the eval scores verdicts, and explanations would only add cost.
"""

from __future__ import annotations

import tempfile
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict

from pisa_contracts import AnalysisResult, DataPolicy, Job
from pisa_engine.evaluation.manifest import Manifest, clip_path
from pisa_engine.explain.explainer import NoExplainer
from pisa_engine.pipeline import PipelineDeps, run_job
from pisa_engine.planning.planner import Planner
from pisa_engine.render.store import EvidenceStore
from pisa_engine.tracking.segmenter import Segmenter

# Job errors that would repeat on every remaining clip: the run stops instead of recording them.
STOPPING_ERRORS = frozenset({"paid_calls_disabled", "spend_cap_reached"})


class RunInfo(BaseModel):
    """How a run was made. Results from different setups are never mixed in one run."""

    model_config = ConfigDict(extra="forbid")

    manifest: str
    segmenter: str
    planner: str
    data_policy: DataPolicy
    started_at: datetime


class ClipRun(BaseModel):
    """One clip's outcome: the full analysis, or the error code of a job that failed."""

    model_config = ConfigDict(extra="forbid")

    clip_id: str
    latency_s: float | None
    error: str | None
    result: AnalysisResult | None


class RunStoppedError(RuntimeError):
    """Every remaining clip would fail the same way, for example with paid calls switched off."""


class _MemoryJobStore:
    def __init__(self) -> None:
        self._jobs: dict[UUID, Job] = {}
        self._results: dict[UUID, AnalysisResult] = {}

    def save(self, job: Job) -> None:
        self._jobs[job.id] = job

    def get(self, job_id: UUID) -> Job | None:
        return self._jobs.get(job_id)

    def save_result(self, result: AnalysisResult) -> None:
        self._results[result.job.id] = result

    def get_result(self, job_id: UUID) -> AnalysisResult | None:
        return self._results.get(job_id)


async def run_manifest(
    manifest_path: Path,
    manifest: Manifest,
    out_dir: Path,
    info: RunInfo,
    *,
    segmenter: Segmenter,
    planner: Planner,
    evidence: EvidenceStore,
    force: bool = False,
    progress: Callable[[str], None] = print,
) -> dict[str, ClipRun]:
    """Runs the clips not run yet (all of them with `force`) and returns every clip's outcome."""
    missing = [c.file for c in manifest.clips if not clip_path(manifest_path, c).is_file()]
    if missing:  # Check before the first paid call, not halfway through.
        raise FileNotFoundError(f"clips not found: {', '.join(missing)}")
    results_dir = out_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    _check_same_setup(out_dir / "run.json", info, force=force)

    store = _MemoryJobStore()
    deps = PipelineDeps(
        segmenter=segmenter,
        store=store,
        planner=planner,
        explainer=NoExplainer(),
        evidence=evidence,
    )
    runs: dict[str, ClipRun] = {}
    for index, clip in enumerate(manifest.clips, start=1):
        saved = results_dir / f"{clip.id}.json"
        if saved.exists() and not force:
            runs[clip.id] = ClipRun.model_validate_json(saved.read_text(encoding="utf-8"))
            continue
        job = Job(
            id=uuid4(),
            created_at=datetime.now(UTC),
            source="eval",
            locale="en",
            data_policy=info.data_policy,
            status="queued",
            stage=None,
            error=None,
        )
        with tempfile.TemporaryDirectory(prefix="pisa-eval-") as work:
            started = time.perf_counter()
            final = await run_job(job, clip_path(manifest_path, clip), Path(work), deps)
            latency = time.perf_counter() - started
        error = final.error.code if final.error else None
        if error in STOPPING_ERRORS:
            raise RunStoppedError(error)
        run = ClipRun(
            clip_id=clip.id,
            latency_s=round(latency, 3),
            error=error,
            result=store.get_result(job.id),
        )
        saved.write_text(run.model_dump_json(indent=1), encoding="utf-8")
        runs[clip.id] = run
        verdict = run.result.verdict.label if run.result and run.result.verdict else error
        progress(f"[{index}/{len(manifest.clips)}] {clip.id}: {verdict} in {latency:.1f} s")
    return runs


def load_runs(out_dir: Path) -> tuple[RunInfo, dict[str, ClipRun]]:
    info = RunInfo.model_validate_json((out_dir / "run.json").read_text(encoding="utf-8"))
    runs = {}
    for path in sorted((out_dir / "results").glob("*.json")):
        run = ClipRun.model_validate_json(path.read_text(encoding="utf-8"))
        runs[run.clip_id] = run
    return info, runs


def _check_same_setup(path: Path, info: RunInfo, *, force: bool) -> None:
    if path.exists() and not force:
        saved = RunInfo.model_validate_json(path.read_text(encoding="utf-8"))
        same = (saved.manifest, saved.segmenter, saved.planner, saved.data_policy) == (
            info.manifest,
            info.segmenter,
            info.planner,
            info.data_policy,
        )
        if not same:
            raise ValueError(
                f"{path.parent.name} was run with another setup ({saved.segmenter}, "
                f"{saved.planner}, {saved.data_policy}); pick another name or pass --force"
            )
        return
    path.write_text(info.model_dump_json(indent=1), encoding="utf-8")
