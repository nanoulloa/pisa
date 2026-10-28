"""Where evidence videos live for 24 hours: local disk, or a private Supabase Storage bucket.

The evidence video shows the user's own frames, so it gets the raw video's rule: it is
deleted 24 hours after the check. Only derived measurements stay. Clients never see a
storage URL that lasts: the engine hands out a signed link valid for one hour.
"""

from __future__ import annotations

import logging
import shutil
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

import httpx
from pydantic import SecretStr

logger = logging.getLogger(__name__)

EVIDENCE_TTL = timedelta(hours=24)
SIGNED_URL_TTL_S = 3600
# Everyone who opens a shared result gets the same link while it has ten minutes left, so
# only the first viewer waits for Storage to sign one.
REUSE_SIGNED_S = SIGNED_URL_TTL_S - 600
MAX_SIGNED = 1024
BUCKET = "evidence"


class EvidenceStore(Protocol):
    def put(self, job_id: UUID, video: Path) -> None: ...

    def locate(self, job_id: UUID) -> Path | str | None:
        """A local file or a signed URL, or None when the video is gone."""
        ...

    def delete_older_than(self, cutoff: datetime) -> int:
        """Delete every video stored before `cutoff`; returns how many."""
        ...


class LocalEvidenceStore:
    def __init__(self, root: Path) -> None:
        self._root = root

    def put(self, job_id: UUID, video: Path) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(video, self._path(job_id))

    def locate(self, job_id: UUID) -> Path | None:
        path = self._path(job_id)
        return path if path.exists() else None

    def delete_older_than(self, cutoff: datetime) -> int:
        deleted = 0
        for path in self._root.glob("*.mp4") if self._root.exists() else []:
            if datetime.fromtimestamp(path.stat().st_mtime, UTC) < cutoff:
                path.unlink(missing_ok=True)
                deleted += 1
        return deleted

    def _path(self, job_id: UUID) -> Path:
        return self._root / f"{job_id}.mp4"


class SupabaseEvidenceStore:
    """The private `evidence` bucket (supabase/migrations), through the Storage API."""

    def __init__(
        self,
        url: str,
        secret_key: SecretStr,
        transport: httpx.BaseTransport | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._clock = clock
        self._signed: OrderedDict[UUID, tuple[str, float]] = OrderedDict()
        self._lock = threading.Lock()
        key = secret_key.get_secret_value()
        headers = {"apikey": key}
        if key.startswith("eyJ"):  # Legacy service_role JWTs also go in Authorization.
            headers["Authorization"] = f"Bearer {key}"
        self._base = url.rstrip("/") + "/storage/v1"
        self._http = httpx.Client(
            base_url=self._base + "/",
            headers=headers,
            timeout=httpx.Timeout(30.0),
            transport=transport,
        )

    def put(self, job_id: UUID, video: Path) -> None:
        response = self._http.post(
            f"object/{BUCKET}/{job_id}.mp4",
            content=video.read_bytes(),
            headers={"Content-Type": "video/mp4", "x-upsert": "true"},
        )
        response.raise_for_status()

    def locate(self, job_id: UUID) -> str | None:
        now = self._clock()
        with self._lock:
            cached = self._signed.get(job_id)
        if cached is not None and now - cached[1] < REUSE_SIGNED_S:
            return cached[0]
        response = self._http.post(
            f"object/sign/{BUCKET}/{job_id}.mp4", json={"expiresIn": SIGNED_URL_TTL_S}
        )
        if response.status_code in (400, 404):  # Not found (Storage answers 400 for that too).
            return None
        response.raise_for_status()
        signed = response.json().get("signedURL")
        if not isinstance(signed, str):
            return None
        with self._lock:
            self._signed[job_id] = (f"{self._base}{signed}", now)
            self._signed.move_to_end(job_id)
            while len(self._signed) > MAX_SIGNED:
                self._signed.popitem(last=False)
        return f"{self._base}{signed}"

    def delete_older_than(self, cutoff: datetime) -> int:
        stale = []
        for item in self._list():
            created = _created_at(item)
            if created is not None and created < cutoff:
                stale.append(str(item["name"]))
        for start in range(0, len(stale), 1000):  # The API removes at most 1,000 per call.
            response = self._http.request(
                "DELETE", f"object/{BUCKET}", json={"prefixes": stale[start : start + 1000]}
            )
            response.raise_for_status()
        if stale:
            with self._lock:
                self._signed.clear()  # No link to a deleted video outlives it.
        return len(stale)

    def _list(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        while True:
            response = self._http.post(
                f"object/list/{BUCKET}",
                json={
                    "prefix": "",
                    "limit": 1000,
                    "offset": len(items),
                    "sortBy": {"column": "created_at", "order": "asc"},
                },
            )
            response.raise_for_status()
            page: list[dict[str, Any]] = response.json()
            items.extend(page)
            if len(page) < 1000:
                return items


def delete_expired(store: EvidenceStore, now: datetime | None = None) -> int:
    deleted = store.delete_older_than((now or datetime.now(UTC)) - EVIDENCE_TTL)
    if deleted:
        logger.info("Expired evidence deleted", extra={"videos": deleted})
    return deleted


def _created_at(item: dict[str, Any]) -> datetime | None:
    value = item.get("created_at")
    if not isinstance(value, str):
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
