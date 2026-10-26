"""WhatsApp Cloud API on Meta's Graph API (https://developers.facebook.com/docs/whatsapp).

Downloads the media people send and sends replies. Media URLs expire after 5 minutes and
need the access token. Videos are H.264 MP4 up to 16 MB. Failed calls are retried with
backoff only when a repeat cannot send a message twice: refused before arriving (429, or a
connection that never opened), or a download.
"""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from pydantic import SecretStr

logger = logging.getLogger(__name__)

MAX_VIDEO_BYTES = 16 * 1024 * 1024
RETRIES = 3
_NEVER_SENT = (httpx.ConnectError, httpx.ConnectTimeout)


class GraphError(RuntimeError):
    def __init__(self, status_code: int, body: str) -> None:
        super().__init__(f"Graph API returned HTTP {status_code}: {body[:300]}")
        self.status_code = status_code


class MediaTooLargeError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MediaInfo:
    url: str
    mime_type: str
    file_size: int | None


class GraphClient:
    def __init__(
        self,
        *,
        access_token: SecretStr,
        phone_number_id: str,
        version: str = "v26.0",
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._token = access_token
        self._phone = phone_number_id
        self._sleep = sleep
        self._http = httpx.AsyncClient(
            base_url=f"https://graph.facebook.com/{version}/",
            timeout=httpx.Timeout(30.0),
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def media_info(self, media_id: str) -> MediaInfo:
        """GET /{media-id}: a download URL valid for 5 minutes."""
        response = await self._retrying(
            lambda: self._http.get(
                media_id, params={"phone_number_id": self._phone}, headers=self._auth()
            ),
            safe_to_repeat=True,
        )
        payload = _json(response)
        url, mime = payload.get("url"), payload.get("mime_type")
        if not isinstance(url, str) or not isinstance(mime, str):
            raise GraphError(response.status_code, "media response has no url or mime_type")
        size = payload.get("file_size")
        return MediaInfo(url=url, mime_type=mime, file_size=size if isinstance(size, int) else None)

    async def download(
        self, url: str, destination: Path, *, max_bytes: int = MAX_VIDEO_BYTES
    ) -> int:
        """Stream the media to `destination`, refusing anything over `max_bytes`."""
        for attempt in range(RETRIES):
            try:
                return await self._download_once(url, destination, max_bytes)
            except (httpx.TransportError, GraphError) as error:
                retryable = not isinstance(error, GraphError) or error.status_code >= 500
                if not retryable or attempt == RETRIES - 1:
                    raise
                await self._sleep(_backoff(attempt))
        raise AssertionError("unreachable")

    async def upload_media(self, path: Path, mime_type: str) -> str:
        """POST /{phone-number-id}/media. Returns the media id to send."""
        data = path.read_bytes()
        response = await self._retrying(
            lambda: self._http.post(
                f"{self._phone}/media",
                headers=self._auth(),
                data={"messaging_product": "whatsapp", "type": mime_type},
                files={"file": (path.name, data, mime_type)},
            ),
            safe_to_repeat=True,  # An orphan upload is harmless; it is never sent.
        )
        media_id = _json(response).get("id")
        if not isinstance(media_id, str):
            raise GraphError(response.status_code, "upload response has no id")
        return media_id

    async def send_text(self, to: str, body: str, *, preview_url: bool = False) -> str:
        return await self._send(to, "text", {"preview_url": preview_url, "body": body})

    async def send_video(self, to: str, media_id: str, caption: str) -> str:
        return await self._send(to, "video", {"id": media_id, "caption": caption})

    async def _send(self, to: str, kind: str, content: Mapping[str, Any]) -> str:
        """POST /{phone-number-id}/messages. Returns the message id."""
        body = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": kind,
            kind: dict(content),
        }
        response = await self._retrying(
            lambda: self._http.post(f"{self._phone}/messages", headers=self._auth(), json=body),
            safe_to_repeat=False,
        )
        messages = _json(response).get("messages")
        if not isinstance(messages, list) or not messages or not isinstance(messages[0], dict):
            raise GraphError(response.status_code, "send response has no message id")
        return str(messages[0].get("id", ""))

    async def _download_once(self, url: str, destination: Path, max_bytes: int) -> int:
        written = 0
        async with self._http.stream("GET", url, headers=self._auth()) as response:
            if response.status_code >= 400:
                await response.aread()
                raise GraphError(response.status_code, response.text)
            with destination.open("wb") as file:
                async for chunk in response.aiter_bytes():
                    written += len(chunk)
                    if written > max_bytes:
                        file.close()
                        destination.unlink(missing_ok=True)
                        raise MediaTooLargeError(f"over {max_bytes} bytes")
                    file.write(chunk)
        return written

    async def _retrying(
        self, call: Callable[[], Awaitable[httpx.Response]], *, safe_to_repeat: bool
    ) -> httpx.Response:
        """Retry 429 and connections that never opened; 5xx and timeouts only when safe."""
        for attempt in range(RETRIES):
            last = attempt == RETRIES - 1
            try:
                response = await call()
            except _NEVER_SENT:
                if last:
                    raise
            except httpx.TransportError:
                if last or not safe_to_repeat:
                    raise
            else:
                retryable = response.status_code == 429 or (
                    safe_to_repeat and response.status_code >= 500
                )
                if not retryable or last:
                    if response.status_code >= 400:
                        raise GraphError(response.status_code, response.text)
                    return response
            await self._sleep(_backoff(attempt))
        raise AssertionError("unreachable")

    def _auth(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token.get_secret_value()}"}


def _json(response: httpx.Response) -> dict[str, Any]:
    payload = response.json()
    if not isinstance(payload, dict):
        raise GraphError(response.status_code, "expected a JSON object")
    return payload


def _backoff(attempt: int) -> float:
    return float(2**attempt) + random.uniform(0, 0.5)  # noqa: S311 (jitter, not security)
