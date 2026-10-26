"""Structured JSON logging with secret redaction."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from typing import Any

REDACTED = "[REDACTED]"

# Extra attributes callers may attach with `logger.info(..., extra={...})`.
_CONTEXT_FIELDS = ("job_id", "stage", "duration_ms", "usd", "model", "client", "client_source")


class JsonFormatter(logging.Formatter):
    """One JSON object per line. Every known secret is replaced, tracebacks included."""

    def __init__(self, secrets: Iterable[str] = ()) -> None:
        super().__init__()
        self._secrets = tuple(secret for secret in secrets if secret)

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in _CONTEXT_FIELDS:
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        text = json.dumps(payload, default=str)
        for secret in self._secrets:
            text = text.replace(secret, REDACTED)
        return text


def configure_logging(level: str, secrets: Iterable[str]) -> None:
    """Send JSON logs to stderr, redacting `secrets`."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(secrets))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
