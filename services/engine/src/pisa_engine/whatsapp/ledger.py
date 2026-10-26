"""Which WhatsApp messages were already handled. Meta retries deliveries for days and may
send the same message twice; each message id is claimed once, so a video is checked once."""

from __future__ import annotations

from collections import OrderedDict
from datetime import UTC, datetime, timedelta
from typing import Protocol

import httpx
from pydantic import SecretStr

KEEP_FOR = timedelta(days=7)  # Longer than Meta keeps retrying.


class MessageLedger(Protocol):
    def claim(self, message_id: str) -> bool:
        """True the first time a message id is seen, False after."""
        ...

    def forget_older_than(self, cutoff: datetime) -> None: ...


class MemoryMessageLedger:
    """For tests and local runs: one process, the most recent ids."""

    def __init__(self, max_ids: int = 10_000) -> None:
        self._seen: OrderedDict[str, datetime] = OrderedDict()
        self._max_ids = max_ids

    def claim(self, message_id: str) -> bool:
        if message_id in self._seen:
            return False
        self._seen[message_id] = datetime.now(UTC)
        while len(self._seen) > self._max_ids:
            self._seen.popitem(last=False)
        return True

    def forget_older_than(self, cutoff: datetime) -> None:
        for message_id, seen in list(self._seen.items()):
            if seen < cutoff:
                del self._seen[message_id]


class SupabaseMessageLedger:
    """The `whatsapp_messages` table (supabase/migrations): shared by every engine container."""

    def __init__(
        self, url: str, secret_key: SecretStr, transport: httpx.BaseTransport | None = None
    ) -> None:
        key = secret_key.get_secret_value()
        headers = {"apikey": key}
        if key.startswith("eyJ"):  # Legacy service_role JWTs also go in Authorization.
            headers["Authorization"] = f"Bearer {key}"
        self._http = httpx.Client(
            base_url=url.rstrip("/") + "/rest/v1/",
            headers=headers,
            timeout=httpx.Timeout(10.0),
            transport=transport,
        )

    def claim(self, message_id: str) -> bool:
        # A duplicate key is ignored and returns no row; a new one returns itself.
        response = self._http.post(
            "whatsapp_messages",
            json={"id": message_id},
            headers={"Prefer": "resolution=ignore-duplicates,return=representation"},
        )
        response.raise_for_status()
        return bool(response.json())

    def forget_older_than(self, cutoff: datetime) -> None:
        response = self._http.delete(
            "whatsapp_messages",
            params={"received_at": f"lt.{cutoff.isoformat()}"},
            headers={"Prefer": "return=minimal"},
        )
        response.raise_for_status()
