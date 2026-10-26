"""What arrives on the webhook: the signature check, the messages in a payload, and the
language to answer in. Pure functions."""

from __future__ import annotations

import hashlib
import hmac
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from pisa_contracts import Locale

Kind = Literal["video", "text", "other"]


@dataclass(frozen=True, slots=True)
class Inbound:
    message_id: str
    sender: str  # The sender's WhatsApp id, which is their phone number.
    kind: Kind
    media_id: str | None
    mime_type: str | None
    text: str
    forwarded: bool
    frequently_forwarded: bool


def valid_signature(body: bytes, header: str | None, app_secret: str) -> bool:
    """Meta signs each delivery: X-Hub-Signature-256 is sha256=HMAC(app secret, raw body)."""
    if not header or not app_secret or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(header.removeprefix("sha256="), expected)


def messages(payload: Mapping[str, Any]) -> Iterator[Inbound]:
    """Every message in a delivery; delivery statuses and other changes are skipped."""
    if payload.get("object") != "whatsapp_business_account":
        return
    for entry in _list(payload.get("entry")):
        for change in _list(entry.get("changes")):
            value = change.get("value")
            if change.get("field") != "messages" or not isinstance(value, Mapping):
                continue
            for message in _list(value.get("messages")):
                parsed = _message(message)
                if parsed is not None:
                    yield parsed


def _message(message: Mapping[str, Any]) -> Inbound | None:
    message_id, sender, kind = message.get("id"), message.get("from"), message.get("type")
    if not isinstance(message_id, str) or not isinstance(sender, str):
        return None
    media = message.get(kind) if isinstance(kind, str) else None
    media = media if isinstance(media, Mapping) else {}
    mime = media.get("mime_type") if isinstance(media.get("mime_type"), str) else None
    is_video = kind == "video" or (kind == "document" and (mime or "").startswith("video/"))
    text = message.get("text", {}).get("body") if kind == "text" else media.get("caption")
    raw_context = message.get("context")
    context: Mapping[str, Any] = raw_context if isinstance(raw_context, Mapping) else {}
    return Inbound(
        message_id=message_id,
        sender=sender,
        kind="video" if is_video else "text" if kind == "text" else "other",
        media_id=str(media["id"]) if is_video and "id" in media else None,
        mime_type=mime,
        text=text if isinstance(text, str) else "",
        forwarded=bool(context.get("forwarded")),
        frequently_forwarded=bool(context.get("frequently_forwarded")),
    )


def _list(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


# Calling codes by language, longest first when matching. Portugal and Portuguese-speaking
# Africa get Brazilian Portuguese, the closest of the four.
_CALLING_CODES: dict[str, Locale] = {
    **dict.fromkeys(["55", "351", "244", "258", "238", "245", "239", "670"], "pt-BR"),
    **dict.fromkeys(["86"], "zh-CN"),
    **dict.fromkeys(
        [
            "34", "52", "53", "54", "56", "57", "58", "51", "591", "593", "595", "598",
            "502", "503", "504", "505", "506", "507", "240",
            "1809", "1829", "1849", "1787", "1939",
        ],
        "es",
    ),
}  # fmt: skip
_HAN = re.compile(r"[一-鿿]")
_PORTUGUESE = re.compile(r"[ãõ]|\b(você|voce|não|nao|obrigad[oa]|olá|vídeo|isso)\b", re.IGNORECASE)
_SPANISH = re.compile(r"[ñ¿¡]|\b(hola|gracias|esto|qué|que es|por favor|verdad)\b", re.IGNORECASE)
_ENGLISH = re.compile(r"\b(hello|hi|hey|thanks|is this|real|fake|please)\b", re.IGNORECASE)


def detect_locale(sender: str, text: str) -> Locale:
    """The language of the message's own words when they show it, else the phone's country."""
    if _HAN.search(text):
        return "zh-CN"
    if _PORTUGUESE.search(text):
        return "pt-BR"
    if _SPANISH.search(text):
        return "es"
    if _ENGLISH.search(text):
        return "en"
    digits = sender.lstrip("+")
    for length in (4, 3, 2):
        if (locale := _CALLING_CODES.get(digits[:length])) is not None:
            return locale
    return "en"
