"""Runs one job through the stages, recording each stage as it starts so clients show real progress.

Day-2 slice: ingest, track, measure, test and verdict. The planner (day 4) will choose the
event windows and phrases; until then the whole clip is one event tracked with one phrase.
Explanations are templated by the client from the verdict and measurements.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

from pisa_contracts import AnalysisResult, ErrorInfo, Job, Stage, TestResult, TrackSet
from pisa_engine.ingest.normalize import IngestError, normalize
from pisa_engine.jobs import JobStore
from pisa_engine.model_api.spend import PaidCallsDisabledError, SpendCapExceededError
from pisa_engine.physics.shape import free_fall_shape
from pisa_engine.physics.trajectory import flight_phases, from_track
from pisa_engine.tracking.segmenter import Segmenter
from pisa_engine.verdict import decide

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

        await progress.enter("measure")
        phases = [phase for obj in objects for phase in flight_phases(from_track(obj))]

        await progress.enter("test")
        results: list[TestResult] = [free_fall_shape(phase) for phase in phases]

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
        tests=results,
        verdict=verdict,
        costs=[],
    )
    await asyncio.to_thread(deps.store.save_result, result)
    return await progress.finish()


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
