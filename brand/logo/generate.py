"""Builds every logo SVG from one construction, so the geometry stays exact.

Run: uv run python brand/logo/generate.py

Master grid: 64 x 64 units, 4-unit module. The tower leans 4 degrees (the real
tower's lean); the drop line is exactly vertical. Small sizes (16 and 32 px) are
redrawn on the pixel grid so they stay crisp; at 16 px the lean is a one-pixel
step over twelve pixels (4.8 degrees), the closest the pixel grid allows.
"""

from __future__ import annotations

import math
from pathlib import Path

OUT = Path(__file__).resolve().parent
INK = "#0F3D3E"
PAPER = "#FBFCFC"
LIME = "#D4E64A"
LEAN_DEG = 4.0

# Master construction of the chosen mark ("Plumb"), in 64-unit space.
BASE_Y = 54.0
TOWER_W = 12.0
TOWER_H = 44.0
TOWER_X = 17.25
LINE_X = 41.25
LINE_W = 2.5
BALL_R = 5.5


def _num(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _svg(body: str, *, size: int = 64, label: str = "Pisa", extra: str = "") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
        f'role="img" aria-label="{label}">{extra}{body}</svg>\n'
    )


# Tower blocks from the ground up: (height, width). Four floors of 8 units and a 4-unit belfry,
# separated by 2-unit gaps, total 44 units. The narrower belfry gives the Pisa silhouette.
FLOORS = ((8.0, TOWER_W), (8.0, TOWER_W), (8.0, TOWER_W), (8.0, TOWER_W), (4.0, 8.0))
FLOOR_GAP = 2.0


def plumb_shapes(fill: str, ball_fill: str | None = None) -> str:
    """A tower of floors leaning 4 degrees, a vertical drop line, and the dropped sphere."""
    tan_lean = math.tan(math.radians(LEAN_DEG))

    def axis_x(y: float) -> float:
        return TOWER_X + TOWER_W / 2 + (BASE_Y - y) * tan_lean

    blocks = []
    y = BASE_Y
    for height, width in FLOORS:
        top = y - height
        corners = [
            (axis_x(y) - width / 2, y),
            (axis_x(y) + width / 2, y),
            (axis_x(top) + width / 2, top),
            (axis_x(top) - width / 2, top),
        ]
        blocks.append(" ".join(f"{_num(cx)},{_num(cy)}" for cx, cy in corners))
        y = top - FLOOR_GAP
    top_y = BASE_Y - TOWER_H
    ball_cy = BASE_Y - BALL_R
    tower = "".join(f'<polygon points="{points}"/>' for points in blocks)
    return (
        f'<g fill="{fill}">{tower}</g>'
        f'<rect x="{_num(LINE_X - LINE_W / 2)}" y="{_num(top_y)}" width="{_num(LINE_W)}" '
        f'height="{_num(ball_cy - top_y)}" fill="{fill}"/>'
        f'<circle cx="{_num(LINE_X)}" cy="{_num(ball_cy)}" r="{_num(BALL_R)}" '
        f'fill="{ball_fill or fill}"/>'
    )


def pair_shapes(fill: str) -> str:
    """Galileo's two equal spheres, falling side by side and landing together."""
    parts = []
    for cx in (22.0, 42.0):
        parts.append(f'<rect x="{_num(cx - 1.25)}" y="10" width="2.5" height="32" fill="{fill}"/>')
        parts.append(f'<circle cx="{_num(cx)}" cy="46" r="6" fill="{fill}"/>')
    parts.append(f'<rect x="10" y="55" width="44" height="2.5" fill="{fill}"/>')
    return "".join(parts)


def ghost_shapes(fill: str) -> str:
    """Two objects thrown alike: the measured one floats on a shallow arc, the ghost falls true."""
    start_x, start_y, end_x = 10.0, 12.0, 46.0
    shallow_drop, true_drop = 18.0, 38.0

    def arc(drop: float) -> str:
        # A parabola from the start point, as one quadratic Bezier with a horizontal tangent.
        mid_x = (start_x + end_x) / 2
        start = f"{_num(start_x)},{_num(start_y)}"
        return f"M{start} Q{_num(mid_x)},{_num(start_y)} {_num(end_x)},{_num(start_y + drop)}"

    return (
        f'<path d="{arc(shallow_drop)}" fill="none" stroke="{fill}" stroke-width="2.5"/>'
        f'<path d="{arc(true_drop)}" fill="none" stroke="{fill}" stroke-width="2.5" '
        f'stroke-dasharray="3 3"/>'
        f'<circle cx="{_num(end_x)}" cy="{_num(start_y + shallow_drop)}" r="5.5" fill="{fill}"/>'
        f'<circle cx="{_num(end_x)}" cy="{_num(start_y + true_drop)}" r="4.5" fill="none" '
        f'stroke="{fill}" stroke-width="2.5"/>'
    )


def favicon_16(fill: str) -> str:
    """Pixel-grid cut: tower in two 4 x 6 px blocks offset by one pixel, 1 px line, 4 px ball."""
    return (
        f'<g fill="{fill}" shape-rendering="crispEdges">'
        '<rect x="3" y="8" width="4" height="6"/><rect x="4" y="2" width="4" height="6"/>'
        '<rect x="10" y="2" width="1" height="8"/></g>'
        f'<circle cx="10.5" cy="12" r="2" fill="{fill}"/>'
    )


def favicon_32(fill: str) -> str:
    """Pixel-grid cut at 32 px: three floors and a belfry, stepping right, and a 2 px line."""
    blocks = (
        '<rect x="8" y="21" width="6" height="6"/>'
        '<rect x="8" y="14" width="6" height="6"/>'
        '<rect x="9" y="7" width="6" height="6"/>'
        '<rect x="10" y="4" width="4" height="2"/>'
    )
    return (
        f'<g fill="{fill}" shape-rendering="crispEdges">{blocks}'
        '<rect x="20" y="4" width="2" height="19"/></g>'
        f'<circle cx="21" cy="24" r="3" fill="{fill}"/>'
    )


ADAPTIVE = (
    f"<style>.m{{fill:{INK}}}@media (prefers-color-scheme:dark){{.m{{fill:{PAPER}}}}}</style>"
)


def main() -> None:
    files = {
        "concept-plumb.svg": _svg(plumb_shapes(INK), label="Pisa concept: plumb"),
        "concept-pair.svg": _svg(pair_shapes(INK), label="Pisa concept: pair"),
        "concept-ghost.svg": _svg(ghost_shapes(INK), label="Pisa concept: ghost"),
        "pisa-mark.svg": _svg(plumb_shapes("currentColor")),
        "pisa-mark-ink.svg": _svg(plumb_shapes(INK)),
        "pisa-mark-paper.svg": _svg(plumb_shapes(PAPER)),
        "favicon-16.svg": _svg(
            favicon_16("currentColor").replace('fill="currentColor"', 'class="m"'),
            size=16,
            extra=ADAPTIVE,
        ),
        "favicon-32.svg": _svg(
            favicon_32("currentColor").replace('fill="currentColor"', 'class="m"'),
            size=32,
            extra=ADAPTIVE,
        ),
        "app-icon-512.svg": _svg(
            f'<rect width="64" height="64" rx="14" fill="{INK}"/>' + plumb_shapes(PAPER, LIME),
        ),
    }
    for name, svg in files.items():
        (OUT / name).write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()
