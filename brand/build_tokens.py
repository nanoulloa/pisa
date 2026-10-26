"""Writes brand/tokens.css from brand/tokens.json.

Run: uv run python brand/build_tokens.py (part of `make gen`).

Light values sit on :root. Dark values apply with the system preference unless the
page forces light, and again under data-theme="dark" so a manual toggle wins both ways.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def build(tokens: dict[str, dict[str, object]]) -> str:
    colors = _pairs(tokens["color"])
    light = [f"--pisa-{name}: {value};" for name, value in tokens["palette"].items()]
    light += [f"--color-{name}: {pair['light']};" for name, pair in colors]
    light += [f"--font-{name}: {value};" for name, value in tokens["font"].items()]
    light += [f"--line-height-{name}: {value};" for name, value in tokens["line-height"].items()]
    light += [f"--radius-{name}: {value};" for name, value in tokens["radius"].items()]
    light.append("color-scheme: light;")
    dark = [f"--color-{name}: {pair['dark']};" for name, pair in colors]
    dark.append("color-scheme: dark;")
    return (
        "/* Generated from brand/tokens.json by brand/build_tokens.py. Do not edit by hand. */\n"
        f":root {{\n{_indent(light, 1)}\n}}\n\n"
        "@media (prefers-color-scheme: dark) {\n"
        f'  :root:not([data-theme="light"]) {{\n{_indent(dark, 2)}\n  }}\n}}\n\n'
        f':root[data-theme="dark"] {{\n{_indent(dark, 1)}\n}}\n'
    )


def _indent(lines: list[str], level: int) -> str:
    return "\n".join("  " * level + line for line in lines)


def _pairs(colors: dict[str, object]) -> list[tuple[str, dict[str, str]]]:
    pairs: list[tuple[str, dict[str, str]]] = []
    for name, value in colors.items():
        if not isinstance(value, dict) or set(value) != {"light", "dark"}:
            raise ValueError(f"color.{name} needs exactly a light and a dark value")
        pairs.append((name, value))
    return pairs


def main() -> None:
    tokens = json.loads((HERE / "tokens.json").read_text(encoding="utf-8"))
    (HERE / "tokens.css").write_text(build(tokens), encoding="utf-8")


if __name__ == "__main__":
    main()
