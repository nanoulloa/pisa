"""Pixels per meter from an object of roughly known size, for T4 implied gravity.

Motion blur only ever makes an object look longer along its motion, never narrower across
it, so a ball's diameter is read from the narrower side of its box, at a low percentile over
the frames. Still objects (a door, a person) use the median of the named dimension.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from pisa_contracts import ReferenceObject, TrackSample
from pisa_engine.physics.implied_g import Scale

MIN_SAMPLES = 5


def pixel_size(samples: Sequence[TrackSample], dimension: str) -> float | None:
    if len(samples) < MIN_SAMPLES:
        return None
    widths = np.array([s.bbox.x2 - s.bbox.x1 for s in samples], dtype=np.float64)
    heights = np.array([s.bbox.y2 - s.bbox.y1 for s in samples], dtype=np.float64)
    if dimension == "diameter":
        size = float(np.percentile(np.minimum(widths, heights), 25))
    elif dimension == "height":
        size = float(np.median(heights))
    elif dimension == "width":
        size = float(np.median(widths))
    else:  # length: the longer side.
        size = float(np.median(np.maximum(widths, heights)))
    return size if size > 0 else None


def scale_from(reference: ReferenceObject, samples: Sequence[TrackSample]) -> Scale | None:
    size = pixel_size(samples, reference.dimension)
    if size is None:
        return None
    return Scale(
        low_px_per_m=size / reference.size_max_m, high_px_per_m=size / reference.size_min_m
    )


def best_scale(
    references: Sequence[ReferenceObject], samples_by_phrase: dict[str, list[TrackSample]]
) -> Scale | None:
    """The usable reference whose size is known most tightly."""
    scales = [
        scale
        for reference in references
        if (scale := scale_from(reference, samples_by_phrase.get(reference.phrase, [])))
    ]
    return min(scales, key=lambda s: s.high_px_per_m / s.low_px_per_m, default=None)
