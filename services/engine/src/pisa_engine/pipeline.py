"""Runs one job through the stages, recording each stage as it starts so clients show real progress.

ingest → plan → track → stabilize → measure → test → verdict → explain → render. The planner
says which objects move freely and when; only those windows are tracked and measured. The
verdict always comes from the measurements. The explainer only words it, and when it cannot
(paid calls off, a failed call, a number it made up), clients fall back to their templated
copy. The render stage draws the evidence video, which is kept for 24 hours; like the
explanation, it never fails a job.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pisa_contracts import (
    AnalysisResult,
    CostEntry,
    ErrorInfo,
    Evidence,
    EvidenceVideo,
    Explanation,
    IngestResult,
    Job,
    Plan,
    Stabilization,
    Stage,
    TestResult,
    TrackedObject,
    TrackSample,
    TrackSet,
    Verdict,
)
from pisa_engine.explain.explainer import Explainer
from pisa_engine.ingest.normalize import IngestError, normalize
from pisa_engine.jobs import JobStore
from pisa_engine.model_api import costs
from pisa_engine.model_api.spend import PaidCallsDisabledError, SpendCapExceededError
from pisa_engine.physics.implied_g import Scale
from pisa_engine.physics.results import measurement, result
from pisa_engine.physics.scale import best_scale
from pisa_engine.physics.suite import run_tests
from pisa_engine.physics.trajectory import from_track, segment_flight
from pisa_engine.planning.planner import Planner
from pisa_engine.render.ghost import OwnedFlight, evidence_series, ghosts
from pisa_engine.render.store import EVIDENCE_TTL, EvidenceStore
from pisa_engine.render.video import render_evidence
from pisa_engine.tracking.segmenter import Segmenter, frame_time
from pisa_engine.tracking.windows import Window, event_windows, reference_windows, track_windows
from pisa_engine.verdict import verdict_for
from pisa_engine.vision.stabilize import (
    MAX_UNRELIABLE_SHARE,
    CameraPath,
    boxes_by_frame,
    estimate_camera_path,
    stabilize,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PipelineDeps:
    segmenter: Segmenter
    store: JobStore
    planner: Planner
    explainer: Explainer
    evidence: EvidenceStore


async def run_job(job: Job, source: Path, work_dir: Path, deps: PipelineDeps) -> Job:
    """Analyze `source`. Returns the final job; the result is saved to the store."""
    with costs.collecting() as spent:
        return await _run(job, source, work_dir, deps, spent)


async def _run(
    job: Job, source: Path, work_dir: Path, deps: PipelineDeps, spent: list[CostEntry]
) -> Job:
    progress = _Progress(job, deps.store)
    video = work_dir / "normalized.mp4"
    tracks: TrackSet | None = None
    stabilization: Stabilization | None = None
    results: list[TestResult] = []
    scene: _Scene | None = None
    try:
        await progress.enter("ingest")
        ingest = await asyncio.to_thread(normalize, source, video)

        await progress.enter("plan")
        plan = await deps.planner.plan(video, ingest, policy=job.data_policy)

        if plan.measurable:
            await progress.enter("track")
            events = event_windows(plan)
            windows = {**events, **reference_windows(plan, events)}
            objects = await track_windows(
                deps.segmenter, video, ingest.timebase, windows, work_dir, policy=job.data_policy
            )
            tracks = TrackSet(
                width=ingest.normalized.width,
                height=ingest.normalized.height,
                timebase=ingest.timebase,
                objects=objects,
            )

            await progress.enter("stabilize")
            path = await asyncio.to_thread(estimate_camera_path, video, boxes_by_frame(objects))
            cuts_s = [frame_time(ingest.timebase, cut) for cut in path.cuts]
            ingest = ingest.model_copy(update={"scene_cuts_s": cuts_s})
            stabilization = Stabilization(
                applied=not path.static,
                max_motion_px=round(path.max_motion_px, 2),
                frames=len(path.to_reference),
                unreliable_frames=path.unreliable_frames,
            )

            await progress.enter("measure")
            measured = _measure(objects, path, events, ingest)

            await progress.enter("test")
            scale = best_scale(plan.references, measured.samples_by_phrase)
            slow_motion = plan.camera.slow_motion_suspected
            flights = [owned.flight for owned in measured.flights]
            results = measured.unmeasured + run_tests(flights, scale=scale, slow_motion=slow_motion)
            scene = _Scene(objects, path, measured.flights, scale, slow_motion)

        await progress.enter("verdict")
        verdict = verdict_for(plan, results)

        await progress.enter("explain")
        explanation = await _explain(deps.explainer, job, verdict, results, plan)

        await progress.enter("render")
        evidence = await _evidence(deps.evidence, job, video, ingest, scene, work_dir)
    except IngestError as error:
        return await progress.fail(error.code)
    except PaidCallsDisabledError:
        return await progress.fail("paid_calls_disabled")
    except SpendCapExceededError:
        return await progress.fail("spend_cap_reached")
    except Exception:
        logger.exception("Job failed", extra={"job_id": str(job.id), "stage": progress.stage})
        return await progress.fail("internal_error")

    # Save the result before marking the job done, so a client that sees "done" finds it.
    done = progress.job.model_copy(update={"status": "done"})
    analysis = AnalysisResult(
        job=done,
        ingest=ingest,
        plan=plan,
        tracks=tracks,
        stabilization=stabilization,
        tests=results,
        verdict=verdict,
        explanation=explanation,
        evidence=evidence,
        costs=list(spent),
    )
    await asyncio.to_thread(deps.store.save_result, analysis)
    logger.info(
        "Job done",
        extra={"job_id": str(job.id), "usd": round(sum(e.usd for e in spent), 6)},
    )
    return await progress.finish()


@dataclass(frozen=True, slots=True)
class _Measured:
    flights: list[OwnedFlight]
    unmeasured: list[TestResult]
    samples_by_phrase: dict[str, list[TrackSample]]


@dataclass(frozen=True, slots=True)
class _Scene:
    """What the render stage needs from the measurement."""

    objects: list[TrackedObject]
    camera: CameraPath
    flights: list[OwnedFlight]
    scale: Scale | None
    slow_motion: bool


def _measure(
    objects: list[TrackedObject],
    path: CameraPath,
    events: dict[str, list[Window]],
    ingest: IngestResult,
) -> _Measured:
    """Flights per object, shot and event window, in stabilized coordinates.

    An object seen mostly on frames the camera path cannot place is not measured; it gets an
    insufficient-data result instead, so the verdict can say why. Reference objects that are
    not part of any event only lend their size.
    """
    flights: list[OwnedFlight] = []
    unmeasured: list[TestResult] = []
    samples_by_phrase: dict[str, list[TrackSample]] = defaultdict(list)
    start_s = ingest.timebase.start_s
    for obj in objects:
        share = path.unreliable_share(obj)
        if share > MAX_UNRELIABLE_SHARE:
            unmeasured.append(
                result(
                    "free_fall_shape",
                    "insufficient_data",
                    0.0,
                    [measurement("unreliable_share", share, "1")],
                    "camera_motion",
                )
            )
            continue
        for shot in stabilize(obj, path):
            samples_by_phrase[obj.phrase].extend(shot.samples)
            for window in events.get(obj.phrase, []):
                inside = [s for s in shot.samples if window.contains(s.t_s - start_s)]
                if inside:
                    piece = shot.model_copy(update={"samples": inside})
                    flight = segment_flight(from_track(piece))
                    flights.append(OwnedFlight(obj.phrase, obj.object_id, flight))
    return _Measured(flights, unmeasured, dict(samples_by_phrase))


async def _explain(
    explainer: Explainer, job: Job, verdict: Verdict, results: list[TestResult], plan: Plan
) -> Explanation | None:
    """Never fails the job: without an explanation, clients use their templated copy."""
    try:
        return await explainer.explain(
            verdict, results, plan, locale=job.locale, policy=job.data_policy
        )
    except Exception:
        logger.warning("No explanation; clients fall back to templates", exc_info=True)
        return None


async def _evidence(
    store: EvidenceStore,
    job: Job,
    video: Path,
    ingest: IngestResult,
    scene: _Scene | None,
    work_dir: Path,
) -> Evidence | None:
    """Ghosts for every measured flight and, while it lasts, the evidence video. Never fails
    the job: without a video, the result still has the measured flights and their ghosts."""
    if scene is None:
        return None
    found = ghosts(scene.flights, scale=scene.scale, slow_motion=scene.slow_motion)
    if not found:
        return None
    clip: EvidenceVideo | None = None
    try:
        rendered = await asyncio.to_thread(
            render_evidence,
            video,
            ingest.timebase,
            scene.camera,
            scene.objects,
            found,
            work_dir / "evidence.mp4",
        )
        if rendered is not None:
            await asyncio.to_thread(store.put, job.id, rendered.path)
            clip = EvidenceVideo(
                width=rendered.width,
                height=rendered.height,
                duration_s=rendered.duration_s,
                playback_rate=rendered.playback_rate,
                source_start_s=rendered.start_s,
                size_bytes=rendered.size_bytes,
                expires_at=datetime.now(UTC) + EVIDENCE_TTL,
            )
    except Exception:
        logger.warning("No evidence video", exc_info=True, extra={"job_id": str(job.id)})
    return Evidence(video=clip, series=evidence_series(found))


class _Progress:
    def __init__(self, job: Job, store: JobStore) -> None:
        self.job = job
        self.stage: Stage | None = None
        self._store = store

    async def enter(self, stage: Stage) -> None:
        self.stage = stage
        await self._save(self.job.model_copy(update={"status": "running", "stage": stage}))

    async def fail(self, code: str) -> Job:
        error = ErrorInfo(code=code, stage=self.stage)
        return await self._save(self.job.model_copy(update={"status": "failed", "error": error}))

    async def finish(self) -> Job:
        return await self._save(self.job.model_copy(update={"status": "done"}))

    async def _save(self, job: Job) -> Job:
        self.job = job
        await asyncio.to_thread(self._store.save, job)
        return job
