"""Runs one job through the stages, recording each stage as it starts so clients show real progress.

Stages so far: ingest, track, stabilize, measure, test and verdict. The planner (day 4) will
choose the event windows and phrases; until then the whole clip is one event tracked with one
phrase. Explanations are templated by the client from the verdict and measurements.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

from pisa_contracts import (
    AnalysisResult,
    ErrorInfo,
    Job,
    Stabilization,
    Stage,
    TestResult,
    TrackedObject,
    TrackSet,
)
from pisa_engine.ingest.normalize import IngestError, normalize
from pisa_engine.jobs import JobStore
from pisa_engine.model_api.spend import PaidCallsDisabledError, SpendCapExceededError
from pisa_engine.physics.results import measurement, result
from pisa_engine.physics.suite import run_tests
from pisa_engine.physics.trajectory import Flight, from_track, segment_flight
from pisa_engine.tracking.segmenter import Segmenter, frame_time
from pisa_engine.verdict import decide
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
    phrase: str = "ball"


async def run_job(job: Job, source: Path, work_dir: Path, deps: PipelineDeps) -> Job:
    """Analyze `source`. Returns the final job; the result is saved to the store."""
    progress = _Progress(job, deps.store)
    try:
        await progress.enter("ingest")
        ingest = await asyncio.to_thread(normalize, source, work_dir / "normalized.mp4")

        await progress.enter("track")
        objects = await deps.segmenter.track(
            work_dir / "normalized.mp4", deps.phrase, ingest.timebase, policy=job.data_policy
        )
        tracks = TrackSet(
            width=ingest.normalized.width,
            height=ingest.normalized.height,
            timebase=ingest.timebase,
            objects=objects,
        )

        await progress.enter("stabilize")
        path = await asyncio.to_thread(
            estimate_camera_path, work_dir / "normalized.mp4", boxes_by_frame(objects)
        )
        cuts_s = [frame_time(ingest.timebase, cut) for cut in path.cuts]
        ingest = ingest.model_copy(update={"scene_cuts_s": cuts_s})
        stabilization = Stabilization(
            applied=not path.static,
            max_motion_px=round(path.max_motion_px, 2),
            frames=len(path.to_reference),
            unreliable_frames=path.unreliable_frames,
        )

        await progress.enter("measure")
        flights, unmeasured = _measure(objects, path)

        await progress.enter("test")
        results = unmeasured + run_tests(flights)

        await progress.enter("verdict")
        verdict = decide(results)
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
    result = AnalysisResult(
        job=done,
        ingest=ingest,
        plan=None,
        tracks=tracks,
        stabilization=stabilization,
        tests=results,
        verdict=verdict,
        costs=[],
    )
    await asyncio.to_thread(deps.store.save_result, result)
    return await progress.finish()


def _measure(
    objects: list[TrackedObject], path: CameraPath
) -> tuple[list[Flight], list[TestResult]]:
    """Flights per object and shot, in stabilized coordinates.

    An object seen mostly on frames the camera path cannot place is not measured; it gets an
    insufficient-data result instead, so the verdict can say why.
    """
    flights: list[Flight] = []
    unmeasured: list[TestResult] = []
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
        flights.extend(segment_flight(from_track(shot)) for shot in stabilize(obj, path))
    return flights, unmeasured


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
