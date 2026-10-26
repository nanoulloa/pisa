"""Writes the contracts' JSON Schema into the Python package, so deployed code can send it on.

Run by `make gen`. The schema travels as a Python module rather than a data file because
deploy tools copy Python sources reliably and data files only when told to.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HEADER = '''# Generated from {source} by `make gen`. Do not edit by hand.
# ruff: noqa: E501
"""The contracts' JSON Schema, for code that passes it on, such as the planner's output format."""

import json
from typing import Any

SCHEMA: dict[str, Any] = json.loads(
    r"""
'''


def main() -> None:
    source, target = Path(sys.argv[1]), Path(sys.argv[2])
    text = json.dumps(json.loads(source.read_text(encoding="utf-8")), indent=1, ensure_ascii=False)
    if '"""' in text:
        raise SystemExit("The schema contains triple quotes and cannot be embedded.")
    target.write_text(HEADER.format(source=source) + text + '\n"""\n)\n', encoding="utf-8")


if __name__ == "__main__":
    main()
