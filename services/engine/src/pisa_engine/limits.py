"""Abuse limits for the public API: request body size and per-client job rate."""

from __future__ import annotations

import contextlib
import time
from collections import defaultdict, deque
from collections.abc import Callable

from starlette.types import ASGIApp, Message, Receive, Scope, Send

_TOO_LARGE_BODY = b'{"error":{"code":"file_too_large","stage":null}}'


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
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send({"type": "http.response.body", "body": _TOO_LARGE_BODY})


class RateLimiter:
    """At most `limit` events per `window_s` seconds for each key. In memory, one process."""

    def __init__(
        self, limit: int, window_s: float, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._limit = limit
        self._window_s = window_s
        self._clock = clock
        self._events: defaultdict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = self._clock()
        events = self._events[key]
        while events and now - events[0] >= self._window_s:
            events.popleft()
        if len(events) >= self._limit:
            return False
        events.append(now)
        return True
