"""The bot's words, from apps/web/messages (embedded by `make gen` in messages.py)."""

from __future__ import annotations

import re
from typing import Any

from pisa_contracts import Locale
from pisa_engine.whatsapp.messages import MESSAGES

_ARGUMENT = re.compile(r"\{(\w+)\}")


def text(locale: Locale, key: str, **values: str) -> str:
    """The message at dotted `key`, with its {name} arguments filled."""
    node: Any = MESSAGES[locale]
    for part in key.split("."):
        node = node[part]
    if not isinstance(node, str):
        raise KeyError(key)
    return _ARGUMENT.sub(lambda match: values[match.group(1)], node)


def has(locale: Locale, key: str) -> bool:
    try:
        text(locale, key)
    except KeyError:
        return False
    return True
