"""Building Responses API requests and reading their answers (https://dev.meta.ai/docs)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class ModelOutputError(RuntimeError):
    """The response came back but holds no usable answer: incomplete, failed or refused."""


def json_schema_format(name: str, schema: Mapping[str, Any]) -> dict[str, Any]:
    """`text.format` for structured output, in strict mode so the answer matches the schema."""
    return {"type": "json_schema", "name": name, "schema": dict(schema), "strict": True}


def output_text(payload: Mapping[str, Any]) -> str:
    """The text of the assistant message, from `output` (or the `output_text` helper field)."""
    status = payload.get("status")
    if status not in (None, "completed"):
        detail = payload.get("incomplete_details") or payload.get("error")
        raise ModelOutputError(f"response {status}: {detail}")
    texts: list[str] = []
    refused = False
    for item in payload.get("output") or []:
        if not isinstance(item, Mapping) or item.get("type") != "message":
            continue
        for part in item.get("content") or []:
            if not isinstance(part, Mapping):
                continue
            if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                texts.append(part["text"])
            elif part.get("type") == "refusal":
                refused = True
    if texts:
        return "".join(texts)
    helper = payload.get("output_text")
    if isinstance(helper, str) and helper:
        return helper
    raise ModelOutputError("the model refused" if refused else "the response has no text")
