"""Abuse limits for the public API: body size, bearer token and per-client job rate.

All of them are ASGI middleware, so they run before FastAPI reads or parses the body.
"""

from __future__ import annotations

import contextlib
import hmac
import ipaddress
import json
import logging
import time
from collections import OrderedDict, deque
from collections.abc import Callable

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)

JOBS_PATH = "/jobs"


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
    """At most `limit` events per `window_s` seconds for each key, and `global_limit` in total.

    In memory, one process. The global limit also bounds memory and makes eviction safe:
    only keys seen within the window can hold events, and there are at most `global_limit`
    of them, so with `max_keys` above that the least recently seen key is always expired.
    Rotating through many addresses therefore cannot push an active client out.
    """

    def __init__(
        self,
        limit: int,
        window_s: float,
        *,
        global_limit: int,
        max_keys: int = 10_000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_keys <= global_limit:
            raise ValueError(
                "max_keys must exceed global_limit, or eviction could drop active keys"
            )
        self._limit = limit
        self._global_limit = global_limit
        self._window_s = window_s
        self._max_keys = max_keys
        self._clock = clock
        self._all: deque[float] = deque()
        self._events: OrderedDict[str, deque[float]] = OrderedDict()
        self.global_exhausted = False

    def allow(self, key: str) -> bool:
        now = self._clock()
        _expire(self._all, now - self._window_s)
        self.global_exhausted = len(self._all) >= self._global_limit
        if self.global_exhausted:
            return False
        events = self._events.pop(key, deque())
        _expire(events, now - self._window_s)
        allowed = len(events) < self._limit
        if allowed:
            events.append(now)
            self._all.append(now)
        if events:
            self._events[key] = events  # Re-inserted last: most recently seen.
            while len(self._events) > self._max_keys:
                self._events.popitem(last=False)
        return allowed

    def __len__(self) -> int:
        return len(self._events)


def _expire(events: deque[float], before: float) -> None:
    while events and events[0] <= before:
        events.popleft()


def client_key(host: str) -> str:
    """IPv4 addresses as they are; IPv6 by /64, since one client usually holds a whole /64."""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return host
    if address.version == 6:
        return str(ipaddress.ip_network(f"{address}/64", strict=False))
    return str(address)


class AdmissionMiddleware:
    """Runs before any body is read. With a token configured, every route except the health
    check needs it, so no path variant can slip past an allowlist. Every POST counts against
    the per-client and global job rates, and only job creation spends them."""

    def __init__(self, app: ASGIApp, *, token: str, limiter: RateLimiter) -> None:
        self.app = app
        self.token = token
        self.limiter = limiter

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or _route_path(scope) == "/healthz":
            await self.app(scope, receive, send)
            return
        if self.token:
            supplied = dict(scope["headers"]).get(b"authorization", b"")
            if not hmac.compare_digest(supplied, f"Bearer {self.token}".encode()):
                await _send_error(send, 401, "unauthorized")
                return
        if scope["method"] == "POST" and _route_path(scope).rstrip("/") == JOBS_PATH:
            client = scope.get("client")
            if not self.limiter.allow(client_key(client[0]) if client else "unknown"):
                if self.limiter.global_exhausted:
                    logger.warning("Global job limit reached; refusing new jobs for now")
                await _send_error(send, 429, "rate_limited")
                return
        await self.app(scope, receive, send)


def _route_path(scope: Scope) -> str:
    """The path the router matches: the request path without the app's mount prefix."""
    path: str = scope["path"]
    root: str = scope.get("root_path", "")
    return path[len(root) :] if root and path.startswith(root) else path
