"""Writes the copy the WhatsApp bot needs from the web app's messages into the engine.

Run by `make gen`, so every translation lives in apps/web/messages and is reviewed and tested
in one place. The bot only fills plain {name} arguments, so plural and select forms are
rejected here rather than sent half-formatted to someone's phone.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

LOCALES = ("en", "es", "zh-CN", "pt-BR")
HEADER = '''# Generated from apps/web/messages by `make gen`. Do not edit by hand.
# ruff: noqa: E501, RUF001
"""Copy for the WhatsApp bot: its own namespace plus verdicts, errors and explanations."""

import json
from typing import Any

MESSAGES: dict[str, dict[str, Any]] = json.loads(
    r"""
'''


def main() -> None:
    source, target = Path(sys.argv[1]), Path(sys.argv[2])
    copy: dict[str, Any] = {}
    for locale in LOCALES:
        messages = json.loads((source / f"{locale}.json").read_text(encoding="utf-8"))
        copy[locale] = {
            "WhatsApp": messages["WhatsApp"],
            "Verdict": messages["Verdict"],
            "Errors": messages["Errors"],
            "Explanations": messages["Result"]["explanations"],
        }
    text = json.dumps(copy, indent=1, ensure_ascii=False)
    if re.search(r"\{\w+,\s*(plural|select|selectordinal)", text):
        raise SystemExit("The bot's copy may only use plain {name} arguments.")
    if '"""' in text:
        raise SystemExit("The copy contains triple quotes and cannot be embedded.")
    target.write_text(HEADER + text + '\n"""\n)\n', encoding="utf-8")


if __name__ == "__main__":
    main()
