"""The conversation: forward a video, get an acknowledgment, then the verdict and evidence.

Two messages per check (the acknowledgment and the result) keep each check inside Meta's
free monthly tier. The sender's phone number is used only to reply: jobs and results never
store it, and logs carry a salted hash.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import secrets
import shutil
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pisa_contracts import AnalysisResult, Job, Locale
from pisa_engine.explain.keys import explanation_key
from pisa_engine.jobs import JobStore
from pisa_engine.limits import RateLimiter
from pisa_engine.whatsapp.copy import has, text
from pisa_engine.whatsapp.graph import MAX_VIDEO_BYTES, GraphClient, MediaTooLargeError
from pisa_engine.whatsapp.inbound import Inbound, detect_locale
from pisa_engine.whatsapp.ledger import MessageLedger

logger = logging.getLogger(__name__)

CAPTION_LIMIT = 1024  # WhatsApp's limit for a video caption.

RunAnalysis = Callable[[Job, Path, Path], Awaitable[Job]]


@dataclass(frozen=True, slots=True)
class BotDeps:
    graph: GraphClient
    ledger: MessageLedger
    jobs: JobStore
    limiter: RateLimiter
    run: RunAnalysis  # Runs the pipeline; leaves the work folder in place for the reply.
    data_dir: Path
    public_url: str


class WhatsAppBot:
    def __init__(self, deps: BotDeps) -> None:
        self._deps = deps
        self._salt = secrets.token_bytes(16)  # Per process, so logged hashes cannot be reversed.

    async def handle(self, message: Inbound) -> None:
        """Answer one message. Never raises: a failure is logged and the user told."""
        who = hmac.new(self._salt, message.sender.encode(), hashlib.sha256).hexdigest()[:12]
        try:
            if not await asyncio.to_thread(self._deps.ledger.claim, message.message_id):
                logger.info("WhatsApp message already handled", extra={"sender": who})
                return
            locale = detect_locale(message.sender, message.text)
            if message.kind == "text":
                await self._say(message, text(locale, "WhatsApp.welcome"))
            elif message.kind != "video" or message.media_id is None:
                await self._say(message, text(locale, "WhatsApp.onlyVideos"))
            elif not self._deps.limiter.allow(f"wa:{who}"):
                busy = self._deps.limiter.global_exhausted
                await self._say(
                    message, text(locale, f"WhatsApp.{'busy' if busy else 'rateLimited'}")
                )
            else:
                await self._check(message, message.media_id, locale)
        except Exception:
            logger.exception("WhatsApp message failed", extra={"sender": who})

    async def _check(self, message: Inbound, media_id: str, locale: Locale) -> None:
        graph = self._deps.graph
        media = await graph.media_info(media_id)
        if media.file_size is not None and media.file_size > MAX_VIDEO_BYTES:
            await self._say(message, text(locale, "WhatsApp.tooLarge"))
            return
        job = Job(
            id=uuid4(),
            created_at=datetime.now(UTC),
            source="whatsapp",
            locale=locale,
            data_policy="user",
            status="queued",
            stage=None,
            error=None,
        )
        work_dir = self._deps.data_dir / "work" / str(job.id)
        work_dir.mkdir(parents=True, exist_ok=True)
        try:
            await asyncio.to_thread(self._deps.jobs.save, job)
            await self._say(message, text(locale, "WhatsApp.received"))
            try:
                await graph.download(media.url, work_dir / "source")
            except MediaTooLargeError:
                await self._say(message, text(locale, "WhatsApp.tooLarge"))
                return
            final = await self._deps.run(job, work_dir / "source", work_dir)
            await self._reply(message, final, work_dir, locale)
        finally:
            # Privacy: the downloaded video and everything made from it leave this machine.
            shutil.rmtree(work_dir, ignore_errors=True)

    async def _reply(self, message: Inbound, final: Job, work_dir: Path, locale: Locale) -> None:
        result = await asyncio.to_thread(self._deps.jobs.get_result, final.id)
        if final.status != "done" or result is None or result.verdict is None:
            code = final.error.code if final.error else "internal_error"
            error = text(
                locale,
                f"Errors.{code}" if has(locale, f"Errors.{code}") else "Errors.internal_error",
            )
            await self._say(message, f"{error} {text(locale, 'WhatsApp.tryAnother')}")
            return
        link = f"{self._deps.public_url.rstrip('/')}/{locale}/result/{final.id}"
        video = work_dir / "evidence.mp4"
        legend = _legend(result, locale) if video.exists() else None
        caption = _caption(result, locale, link, legend, message.frequently_forwarded)
        if legend is not None:
            media_id = await self._deps.graph.upload_media(video, "video/mp4")
            await self._deps.graph.send_video(message.sender, media_id, caption)
        else:  # The link preview shows the share card.
            await self._deps.graph.send_text(message.sender, caption, preview_url=True)

    async def _say(self, message: Inbound, body: str) -> None:
        await self._deps.graph.send_text(message.sender, body)


def _caption(
    result: AnalysisResult, locale: Locale, link: str, legend: str | None, forwarded_often: bool
) -> str:
    """Verdict, the sentence under it, what the ghost means, and the link: what fits."""
    assert result.verdict is not None
    verdict = result.verdict
    if result.explanation is not None and result.explanation.locale == locale:
        sentence = result.explanation.text
    else:
        sentence = text(locale, f"Explanations.{explanation_key(verdict, result.tests)}")
    head = [f"*{text(locale, f'Verdict.{verdict.label}')}*", sentence]
    if forwarded_often:
        head.append(text(locale, "WhatsApp.frequentlyForwarded"))
    tail = [text(locale, "WhatsApp.details", link=link)]
    for optional in ([legend] if legend else []), []:
        caption = "\n\n".join([*head, *optional, *tail])
        if len(caption) <= CAPTION_LIMIT:
            return caption
    return "\n\n".join([*head[:2], *tail])[:CAPTION_LIMIT]


def _legend(result: AnalysisResult, locale: Locale) -> str | None:
    if result.evidence is None or result.evidence.video is None or not result.evidence.series:
        return None
    return text(locale, f"WhatsApp.legend.{result.evidence.series[0].model}")
