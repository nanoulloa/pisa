"""Abuse limits for the public API: body size, bearer token and per-client job rate.

All of them are ASGI middleware, so they run before FastAPI reads or parses the body.
"""

from __future__ import annotations

import contextlib
import hmac
import ipaddress
import json
import time
from collections import OrderedDict, deque
from collections.abc import Callable

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class _BodyTooLargeError(Exception):
    pass


class BodySizeLimitMiddleware:
    """Refuses POST bodies over `max_bytes` while they arrive, before anything parses them.

    Checks Content-Length first, then counts the bytes actually received, which also covers
    chunked uploads that send no length.
    """

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "POST":
            await self.app(scope, receive, send)
            return
        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > self.max_bytes:
            await _send_too_large(send)
            return

        received = 0
        exceeded = False

        async def limited_receive() -> Message:
            nonlocal received, exceeded
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    exceeded = True
                    raise _BodyTooLargeError
            return message

        async def guarded_send(message: Message) -> None:
            if not exceeded:  # Drop whatever error the app produced from the aborted read.
                await send(message)

        with contextlib.suppress(_BodyTooLargeError):
            await self.app(scope, limited_receive, guarded_send)
        if exceeded:
            await _send_too_large(send)


async def _send_too_large(send: Send) -> None:
    await _send_error(send, 413, "file_too_large")


async def _send_error(send: Send, status: int, code: str) -> None:
    body = json.dumps({"error": {"code": code, "stage": None}}).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send({"type": "http.response.body", "body": body})


class RateLimiter:
    """At most `limit` events per `window_s` seconds for each key. In memory, one process.

    Tracks at most `max_keys` clients; the least recently seen are forgotten first, and keys
    with no events left in the window are dropped.
    """

    def __init__(
        self,
        limit: int,
        window_s: float,
        *,
        max_keys: int = 10_000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._limit = limit
        self._window_s = window_s
        self._max_keys = max_keys
        self._clock = clock
        self._events: OrderedDict[str, deque[float]] = OrderedDict()

    def allow(self, key: str) -> bool:
        now = self._clock()
        events = self._events.pop(key, deque())
        while events and now - events[0] >= self._window_s:
            events.popleft()
        allowed = len(events) < self._limit
        if allowed:
            events.append(now)
        if events:
            self._events[key] = events  # Re-inserted last: most recently seen.
            while len(self._events) > self._max_keys:
                self._events.popitem(last=False)
        return allowed

    def __len__(self) -> int:
        return len(self._events)


def client_key(host: str) -> str:
    """IPv4 addresses as they are; IPv6 by /64, since one client usually holds a whole /64."""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return host
    if address.version == 6:
        return str(ipaddress.ip_network(f"{address}/64", strict=False))
    return str(address)


class JobAdmissionMiddleware:
    """Checks the bearer token and the per-client rate before a job upload is read at all."""

    def __init__(self, app: ASGIApp, *, path: str, token: str, limiter: RateLimiter) -> None:
        self.app = app
        self.path = path
        self.token = token
        self.limiter = limiter

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"] != self.path:
            await self.app(scope, receive, send)
            return
        if self.token:
            supplied = dict(scope["headers"]).get(b"authorization", b"")
            if not hmac.compare_digest(supplied, f"Bearer {self.token}".encode()):
                await _send_error(send, 401, "unauthorized")
                return
        client = scope.get("client")
        if not self.limiter.allow(client_key(client[0]) if client else "unknown"):
            await _send_error(send, 429, "rate_limited")
            return
        await self.app(scope, receive, send)
