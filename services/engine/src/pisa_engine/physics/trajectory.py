"""Trajectories and their flight phases. Pure functions on arrays; no I/O, no models."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise

import numpy as np
import numpy.typing as npt

from pisa_contracts import TrackedObject

FloatArray = npt.NDArray[np.float64]
BoolArray = npt.NDArray[np.bool_]

# A step shorter than this (pixels per frame) counts as standing still.
REST_STEP_PX = 1.0
# Consecutive still steps that make a rest. A single short step can be the first frame of a fall.
REST_MIN_STEPS = 3
# A bounce is a sharp lowest point: the object came down, and goes back up, at least this far.
BOUNCE_MIN_PX = 2.0


@dataclass(frozen=True, slots=True)
class Trajectory:
    """Positions over time in image pixels (y points down), and the object's area in pixels.

    Area stands in for depth: an object that grows or shrinks is moving toward or away from
    the camera. Without masks (for example in tests), area is constant.
    """

    t: FloatArray
    x: FloatArray
    y: FloatArray
    area: FloatArray | None = None

    def __len__(self) -> int:
        return int(self.t.size)

    def window(self, start: int, stop: int) -> Trajectory:
        area = None if self.area is None else self.area[start:stop]
        return Trajectory(self.t[start:stop], self.x[start:stop], self.y[start:stop], area)


def from_track(obj: TrackedObject) -> Trajectory:
    samples = sorted(obj.samples, key=lambda sample: sample.frame)
    return Trajectory(
        t=np.array([s.t_s for s in samples], dtype=np.float64),
        x=np.array([s.centroid.x for s in samples], dtype=np.float64),
        y=np.array([s.centroid.y for s in samples], dtype=np.float64),
        area=np.array([s.area_px for s in samples], dtype=np.float64),
    )


def flight_phases(trajectory: Trajectory, *, min_samples: int = 8) -> list[Trajectory]:
    """Split a track into free-flight phases.

    Drops the rest before release (keeping the release frame) and the rest after landing,
    then cuts at every bounce. The bounce frame belongs to no phase: the object is in
    contact there. Phases shorter than `min_samples` are dropped.
    """
    start, stop = _moving_span(trajectory)
    if stop - start < min_samples:
        return []
    cuts = [i for i in range(start + 2, stop - 2) if _is_bounce(trajectory.y, i)]
    phases = []
    for left, right in pairwise([start - 1, *cuts, stop]):
        if right - (left + 1) >= min_samples:
            phases.append(trajectory.window(left + 1, right))
    return phases


def _moving_span(trajectory: Trajectory) -> tuple[int, int]:
    """[start, stop) from the release frame to the last frame before the object comes to rest."""
    steps = np.hypot(np.diff(trajectory.x), np.diff(trajectory.y))
    still = steps < REST_STEP_PX
    lead = _leading_run(still)
    trail = _leading_run(still[::-1])
    start = lead if lead >= REST_MIN_STEPS else 0
    stop = len(trajectory) - 1 - trail if trail >= REST_MIN_STEPS else len(trajectory)
    return start, stop


def _leading_run(mask: BoolArray) -> int:
    false_at = np.flatnonzero(~mask)
    return int(false_at[0]) if false_at.size else int(mask.size)


def _is_bounce(y: FloatArray, i: int) -> bool:
    lowest = y[i] >= y[i - 1] and y[i] > y[i + 1]
    came_down = y[i] - y[i - 2] >= BOUNCE_MIN_PX
    goes_up = y[i] - y[i + 2] >= BOUNCE_MIN_PX
    return bool(lowest and came_down and goes_up)
