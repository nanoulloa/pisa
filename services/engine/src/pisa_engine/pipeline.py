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
        progress.enter("ingest")
        ingest = await asyncio.to_thread(normalize, source, work_dir / "normalized.mp4")

        progress.enter("track")
        objects = await deps.segmenter.track(
            work_dir / "normalized.mp4", deps.phrase, ingest.timebase, policy=job.data_policy
        )
        tracks = TrackSet(
            width=ingest.normalized.width,
            height=ingest.normalized.height,
            timebase=ingest.timebase,
            objects=objects,
        )

        progress.enter("measure")
        phases = [phase for obj in objects for phase in flight_phases(from_track(obj))]

        progress.enter("test")
        results: list[TestResult] = [free_fall_shape(phase) for phase in phases]

        progress.enter("verdict")
        verdict = decide(results)
    except IngestError as error:
        return progress.fail(error.code)
    except PaidCallsDisabledError:
        return progress.fail("paid_calls_disabled")
    except SpendCapExceededError:
        return progress.fail("spend_cap_reached")
    except Exception:
        logger.exception("Job failed", extra={"job_id": str(job.id), "stage": progress.stage})
        return progress.fail("internal_error")

    done = progress.finish()
    deps.store.save_result(
        AnalysisResult(
            job=done,
            ingest=ingest,
            plan=None,
            tracks=tracks,
            tests=results,
            verdict=verdict,
            costs=[],
        )
    )
    return done


class _Progress:
    def __init__(self, job: Job, store: JobStore) -> None:
        self.job = job
        self.stage: Stage | None = None
        self._store = store

    def enter(self, stage: Stage) -> None:
        self.stage = stage
        self._save(self.job.model_copy(update={"status": "running", "stage": stage}))

    def fail(self, code: str) -> Job:
        error = ErrorInfo(code=code, stage=self.stage)
        return self._save(self.job.model_copy(update={"status": "failed", "error": error}))

    def finish(self) -> Job:
        return self._save(self.job.model_copy(update={"status": "done"}))

    def _save(self, job: Job) -> Job:
        self.job = job
        self._store.save(job)
        return job
