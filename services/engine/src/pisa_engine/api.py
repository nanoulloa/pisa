"""HTTP API of the engine. Jobs arrive here from the web app and, later, the WhatsApp webhook."""

from __future__ import annotations

import asyncio
import logging
import shutil
import time
from collections.abc import Callable
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, FastAPI, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from pisa_contracts import Job, Locale
from pisa_engine import __version__
from pisa_engine.explain.explainer import Explainer, MuseSparkExplainer, NoExplainer
from pisa_engine.jobs import JobStore, StorageJobStore, SupabaseJobStore
from pisa_engine.limits import AdmissionMiddleware, BodySizeLimitMiddleware, RateLimiter
from pisa_engine.logs import configure_logging
from pisa_engine.model_api.client import MetaModelApiClient
from pisa_engine.model_api.spend import JsonlSpendLedger, SpendGuard
from pisa_engine.pipeline import PipelineDeps, run_job
from pisa_engine.planning.muse_spark import MuseSparkPlanner
from pisa_engine.planning.planner import Planner, WholeClipPlanner
from pisa_engine.render.store import (
    EvidenceStore,
    LocalEvidenceStore,
    SupabaseEvidenceStore,
    delete_expired,
)
from pisa_engine.settings import Settings, get_settings
from pisa_engine.storage import LocalStorage
from pisa_engine.tracking.fake import ColorSegmenter
from pisa_engine.tracking.sam import Sam31Segmenter
from pisa_engine.tracking.segmenter import Segmenter

logger = logging.getLogger(__name__)

_CHUNK_BYTES = 1 << 20
# Room for multipart boundaries and form fields around the video itself.
_FORM_OVERHEAD_BYTES = 64 * 1024
# Expired evidence is also swept when jobs arrive, at most this often per process.
_SWEEP_EVERY_S = 600.0


def create_app(
    settings: Settings | None = None,
    segmenter: Segmenter | None = None,
    planner: Planner | None = None,
    explainer: Explainer | None = None,
    evidence: EvidenceStore | None = None,
) -> FastAPI:
    config = settings or get_settings()
    configure_logging(
        config.log_level,
        secrets=[
            config.meta_api_key.get_secret_value(),
            config.supabase_secret_key.get_secret_value(),
            config.engine_token.get_secret_value(),
        ],
    )
    store = _job_store(config)
    evidence_store = evidence or evidence_store_for(config)
    last_sweep = [0.0]

    def sweep_expired_evidence() -> None:
        """Best effort: the scheduled sweep (modal_app.py) is the guarantee."""
        if time.monotonic() - last_sweep[0] < _SWEEP_EVERY_S:
            return
        last_sweep[0] = time.monotonic()
        try:
            delete_expired(evidence_store)
        except Exception:
            logger.warning("Could not sweep expired evidence", exc_info=True)

    @cache
    def meta_client() -> MetaModelApiClient:
        """One client and one spend guard for every stage that pays, made on first use."""
        return _meta_client(config)

    deps = PipelineDeps(
        segmenter=segmenter or _segmenter(config, meta_client),
        store=store,
        planner=planner or _planner(config, meta_client),
        explainer=explainer or _explainer(config, meta_client),
        evidence=evidence_store,
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
        try:
            if not await _save_upload(video, source, config.max_upload_bytes):
                shutil.rmtree(work_dir, ignore_errors=True)
                return _error(413, "file_too_large")
            await asyncio.to_thread(store.save, job)
        except BaseException:
            shutil.rmtree(work_dir, ignore_errors=True)  # Never keep a video we will not analyze.
            raise
        logger.info("Job created", extra={"job_id": str(job.id), "stage": "ingest"})
        background.add_task(run_when_free, job, source, work_dir)
        background.add_task(sweep_expired_evidence)
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

    @app.get("/jobs/{job_id}/evidence.mp4", response_model=None)
    def get_evidence(job_id: UUID) -> Any:
        """The evidence video while it lasts: the file, or a signed link valid for an hour."""
        result = store.get_result(job_id)
        video = result.evidence.video if result and result.evidence else None
        if video is None:
            return _error(404, "evidence_not_found")
        if datetime.now(UTC) >= video.expires_at:
            return _error(404, "evidence_expired")
        location = evidence_store.locate(job_id)
        if location is None:
            return _error(404, "evidence_expired")
        if isinstance(location, Path):
            return FileResponse(location, media_type="video/mp4")
        return RedirectResponse(location, status_code=307)

    return app


def evidence_store_for(config: Settings) -> EvidenceStore:
    if _uses_supabase(config):
        return SupabaseEvidenceStore(config.supabase_url, config.supabase_secret_key)
    return LocalEvidenceStore(config.data_dir / "evidence")


def _job_store(config: Settings) -> JobStore:
    if _uses_supabase(config):
        return SupabaseJobStore(config.supabase_url, config.supabase_secret_key)
    return StorageJobStore(LocalStorage(config.data_dir))


def _uses_supabase(config: Settings) -> bool:
    configured = bool(config.supabase_url and config.supabase_secret_key.get_secret_value())
    return configured and config.store == "auto"


_ClientFactory = Callable[[], MetaModelApiClient]


def _segmenter(config: Settings, client: _ClientFactory) -> Segmenter:
    if config.segmenter == "fake":
        return ColorSegmenter()
    return Sam31Segmenter(client(), model=config.sam_model)


def _planner(config: Settings, client: _ClientFactory) -> Planner:
    if config.planner == "fake":
        return WholeClipPlanner(config.default_phrase)
    return MuseSparkPlanner(
        client(),
        model=config.muse_spark_model,
        contributor_model=config.muse_spark_contributor_model,
    )


def _explainer(config: Settings, client: _ClientFactory) -> Explainer:
    if config.explainer == "none":
        return NoExplainer()
    return MuseSparkExplainer(
        client(),
        model=config.muse_spark_model,
        contributor_model=config.muse_spark_contributor_model,
    )


def _meta_client(config: Settings) -> MetaModelApiClient:
    guard = SpendGuard(
        enabled=config.paid_calls_enabled,
        cap_usd=config.spend_cap_usd,
        ledger=JsonlSpendLedger(config.spend_ledger_path),
    )
    return MetaModelApiClient(
        api_key=config.meta_api_key, base_url=config.meta_api_base_url, guard=guard
    )


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
