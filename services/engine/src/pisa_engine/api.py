"""HTTP API of the engine. Jobs arrive here from the web app and, later, the WhatsApp webhook."""

from __future__ import annotations

import asyncio
import hmac
import json
import logging
import shutil
import time
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, FastAPI, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, RedirectResponse

from pisa_contracts import Job, Locale
from pisa_engine import __version__
from pisa_engine.explain.explainer import Explainer
from pisa_engine.jobs import JobStore, StorageJobStore, SupabaseJobStore
from pisa_engine.limits import AdmissionMiddleware, BodySizeLimitMiddleware, RateLimiter
from pisa_engine.logs import configure_logging
from pisa_engine.model_api.client import MetaModelApiClient
from pisa_engine.pipeline import PipelineDeps, run_job
from pisa_engine.planning.planner import Planner
from pisa_engine.render.store import (
    EvidenceStore,
    LocalEvidenceStore,
    SupabaseEvidenceStore,
    delete_expired,
)
from pisa_engine.settings import Settings, get_settings
from pisa_engine.storage import LocalStorage
from pisa_engine.tracking.segmenter import Segmenter
from pisa_engine.whatsapp.bot import BotDeps, WhatsAppBot
from pisa_engine.whatsapp.graph import GraphClient
from pisa_engine.whatsapp.inbound import messages, valid_signature
from pisa_engine.whatsapp.ledger import (
    KEEP_FOR,
    MemoryMessageLedger,
    MessageLedger,
    SupabaseMessageLedger,
)
from pisa_engine.wiring import explainer_for, meta_client_for, planner_for, segmenter_for

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
    graph: GraphClient | None = None,
) -> FastAPI:
    config = settings or get_settings()
    configure_logging(
        config.log_level,
        secrets=[
            config.meta_api_key.get_secret_value(),
            config.supabase_secret_key.get_secret_value(),
            config.engine_token.get_secret_value(),
            config.whatsapp_access_token.get_secret_value(),
            config.whatsapp_app_secret.get_secret_value(),
            config.whatsapp_verify_token.get_secret_value(),
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
        return meta_client_for(config)

    deps = PipelineDeps(
        segmenter=segmenter or segmenter_for(config, meta_client),
        store=store,
        planner=planner or planner_for(config, meta_client),
        explainer=explainer or explainer_for(config, meta_client),
        evidence=evidence_store,
    )
    rate = RateLimiter(config.jobs_per_hour, window_s=3600, global_limit=config.jobs_per_hour_total)
    slots = asyncio.Semaphore(config.max_concurrent_jobs)

    async def analyze(job: Job, source: Path, work_dir: Path) -> Job:
        async with slots:
            return await run_job(job, source, work_dir, deps)

    async def run_when_free(job: Job, source: Path, work_dir: Path) -> None:
        try:
            await analyze(job, source, work_dir)
        finally:
            # Privacy: the uploaded video and its normalized copy are deleted as soon as the
            # job ends. Only derived measurements are kept.
            shutil.rmtree(work_dir, ignore_errors=True)

    bot: WhatsAppBot | None = None
    whatsapp_graph = graph or _graph(config)
    if whatsapp_graph is not None:
        bot = WhatsAppBot(
            BotDeps(
                graph=whatsapp_graph,
                ledger=message_ledger_for(config),
                jobs=store,
                limiter=rate,
                run=analyze,
                data_dir=config.data_dir,
                public_url=config.public_url,
            )
        )

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

    @app.get("/whatsapp/webhook", response_model=None)
    def verify_whatsapp(request: Request) -> Any:
        """Meta's subscription check: echo the challenge when the verify token matches."""
        params = request.query_params
        expected = config.whatsapp_verify_token.get_secret_value()
        supplied = params.get("hub.verify_token", "")
        challenge = params.get("hub.challenge", "")
        if (
            expected
            and params.get("hub.mode") == "subscribe"
            and hmac.compare_digest(supplied.encode(), expected.encode())
            and challenge.isalnum()
            and len(challenge) <= 128
        ):
            return PlainTextResponse(challenge)
        return _error(403, "forbidden")

    @app.post("/whatsapp/webhook", response_model=None)
    async def receive_whatsapp(request: Request, background: BackgroundTasks) -> Any:
        """Signed deliveries only. Answers at once; each message is handled in the background."""
        if bot is None:
            return _error(404, "whatsapp_not_configured")
        body = await request.body()
        secret = config.whatsapp_app_secret.get_secret_value()
        if not valid_signature(body, request.headers.get("x-hub-signature-256"), secret):
            logger.warning("WhatsApp delivery with a bad signature refused")
            return _error(401, "invalid_signature")
        try:
            payload = json.loads(body)
        except ValueError:
            return _error(400, "invalid_payload")
        if isinstance(payload, dict):
            for message in messages(payload):
                background.add_task(bot.handle, message)
        return {"status": "received"}

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


def message_ledger_for(config: Settings) -> MessageLedger:
    if _uses_supabase(config):
        return SupabaseMessageLedger(config.supabase_url, config.supabase_secret_key)
    return MemoryMessageLedger()


def sweep_expired(config: Settings) -> None:
    """Hourly: evidence videos past 24 hours, and WhatsApp message ids past Meta's retries."""
    delete_expired(evidence_store_for(config))
    message_ledger_for(config).forget_older_than(datetime.now(UTC) - KEEP_FOR)


def _graph(config: Settings) -> GraphClient | None:
    """The bot runs only when the token, the app secret and the phone number id are all set."""
    token, app_secret = config.whatsapp_access_token, config.whatsapp_app_secret
    if not (token.get_secret_value() and app_secret.get_secret_value()):
        return None
    if not config.whatsapp_phone_number_id:
        return None
    return GraphClient(
        access_token=token,
        phone_number_id=config.whatsapp_phone_number_id,
        version=config.whatsapp_graph_version,
    )


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
