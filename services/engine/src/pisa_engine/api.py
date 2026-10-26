"""HTTP API of the engine. Jobs arrive here from the web app and, later, the WhatsApp webhook."""

from __future__ import annotations

import asyncio
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, FastAPI, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pisa_contracts import Job, Locale
from pisa_engine import __version__
from pisa_engine.jobs import JobStore, StorageJobStore, SupabaseJobStore
from pisa_engine.limits import AdmissionMiddleware, BodySizeLimitMiddleware, RateLimiter
from pisa_engine.model_api.client import MetaModelApiClient
from pisa_engine.model_api.spend import JsonlSpendLedger, SpendGuard
from pisa_engine.pipeline import PipelineDeps, run_job
from pisa_engine.settings import Settings, get_settings
from pisa_engine.storage import LocalStorage
from pisa_engine.tracking.fake import ColorSegmenter
from pisa_engine.tracking.sam import Sam31Segmenter
from pisa_engine.tracking.segmenter import Segmenter

_CHUNK_BYTES = 1 << 20
# Room for multipart boundaries and form fields around the video itself.
_FORM_OVERHEAD_BYTES = 64 * 1024


def create_app(settings: Settings | None = None, segmenter: Segmenter | None = None) -> FastAPI:
    config = settings or get_settings()
    store = _job_store(config)
    deps = PipelineDeps(
        segmenter=segmenter or _segmenter(config), store=store, phrase=config.default_phrase
    )
    rate = RateLimiter(config.jobs_per_hour, window_s=3600, global_limit=config.jobs_per_hour_total)
    slots = asyncio.Semaphore(config.max_concurrent_jobs)

    async def run_when_free(job: Job, source: Path, work_dir: Path) -> None:
        try:
            async with slots:
                await run_job(job, source, work_dir, deps)
        finally:
            # Privacy: the uploaded video and its normalized copy are deleted as soon as the
            # job ends. Only derived measurements are kept.
            shutil.rmtree(work_dir, ignore_errors=True)

    app = FastAPI(title="Pisa engine", version=__version__)
    app.add_middleware(
        BodySizeLimitMiddleware, max_bytes=config.max_upload_bytes + _FORM_OVERHEAD_BYTES
    )
    # Runs before the size check and the app, so refused requests never send their body.
    app.add_middleware(
        AdmissionMiddleware,
        token=config.engine_token.get_secret_value(),
        limiter=rate,
        trust_proxy=config.trust_proxy,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in config.web_origins.split(",") if origin],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.post("/jobs", status_code=202, response_model=None)
    async def create_job(
        video: UploadFile,
        background: BackgroundTasks,
        locale: Annotated[Locale, Form()] = "en",
    ) -> Job | JSONResponse:
        job = Job(
            id=uuid4(),
            created_at=datetime.now(UTC),
            source="web",
            locale=locale,
            data_policy="user",
            status="queued",
            stage=None,
            error=None,
        )
        work_dir = config.data_dir / "work" / str(job.id)
        work_dir.mkdir(parents=True, exist_ok=True)
        source = work_dir / "source"
        if not await _save_upload(video, source, config.max_upload_bytes):
            shutil.rmtree(work_dir, ignore_errors=True)
            return _error(413, "file_too_large")
        store.save(job)
        background.add_task(run_when_free, job, source, work_dir)
        return job

    @app.get("/jobs/{job_id}", response_model=None)
    def get_job(job_id: UUID) -> Job | JSONResponse:
        job = store.get(job_id)
        return job if job is not None else _error(404, "job_not_found")

    @app.get("/jobs/{job_id}/result", response_model=None)
    def get_result(job_id: UUID) -> Any:
        result = store.get_result(job_id)
        if result is None:
            return _error(404, "result_not_ready")
        return result

    return app


def _job_store(config: Settings) -> JobStore:
    key = config.supabase_secret_key
    if config.supabase_url and key.get_secret_value():
        return SupabaseJobStore(config.supabase_url, key)
    return StorageJobStore(LocalStorage(config.data_dir))


def _segmenter(config: Settings) -> Segmenter:
    if config.segmenter == "fake":
        return ColorSegmenter()
    guard = SpendGuard(
        enabled=config.paid_calls_enabled,
        cap_usd=config.spend_cap_usd,
        ledger=JsonlSpendLedger(config.spend_ledger_path),
    )
    client = MetaModelApiClient(
        api_key=config.meta_api_key, base_url=config.meta_api_base_url, guard=guard
    )
    return Sam31Segmenter(client, model=config.sam_model)


async def _save_upload(upload: UploadFile, path: Path, limit: int) -> bool:
    """Streams the upload to disk. False, and nothing kept, if it exceeds `limit` bytes."""
    written = 0
    with path.open("wb") as file:
        while chunk := await upload.read(_CHUNK_BYTES):
            written += len(chunk)
            if written > limit:
                break
            file.write(chunk)
    if written > limit:
        path.unlink(missing_ok=True)
        return False
    return True


def _error(status: int, code: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "stage": None}})


app = create_app()
