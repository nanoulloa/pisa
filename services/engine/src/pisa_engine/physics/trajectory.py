"""Trajectories and their flight phases. Pure functions on arrays; no I/O, no models."""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import pairwise

import numpy as np
import numpy.typing as npt

from pisa_contracts import TrackedObject

FloatArray = npt.NDArray[np.float64]
BoolArray = npt.NDArray[np.bool_]

# An object within this many pixels of where it rests counts as standing still ...
REST_RADIUS_PX = 1.0
# ... or within this many standard deviations of the track's own jitter, when that is larger.
# Trackers on real footage jitter by a pixel or two, so a held ball never looks perfectly still.
JITTER_SIGMAS = 4.0
# Samples in a row that make a rest, and that end one: a single short step can be the first
# frame of a fall, and a single far one can be jitter.
REST_MIN_STEPS = 3
# A bounce is a sharp lowest point: the object came down, and goes back up, at least this far
# (or JITTER_SIGMAS jitter deviations, when that is larger).
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


@dataclass(frozen=True, slots=True)
class Bounce:
    """Two flight phases on either side of one contact with the ground."""

    before: Trajectory
    after: Trajectory
    contact_t: float
    contact_y: float


@dataclass(frozen=True, slots=True)
class Flight:
    phases: list[Trajectory]
    bounces: list[Bounce]


def segment_flight(trajectory: Trajectory, *, min_samples: int = 8) -> Flight:
    """Split a track into free-flight phases and the bounces between them.

    Drops the rest before release (keeping the release frame) and the rest after landing,
    then cuts at every bounce. The bounce frame belongs to no phase: the object is in
    contact there. Phases shorter than `min_samples` are dropped, and so are bounces next
    to them.
    """
    jitter = _jitter_px(trajectory)
    start, stop = _moving_span(trajectory, max(REST_RADIUS_PX, JITTER_SIGMAS * jitter))
    if stop - start < min_samples:
        return Flight(phases=[], bounces=[])
    rise = max(BOUNCE_MIN_PX, JITTER_SIGMAS * jitter)
    contacts = [i for i in range(start + 2, stop - 2) if _is_bounce(trajectory.y, i, rise)]
    windows = [(left + 1, right) for left, right in pairwise([start - 1, *contacts, stop])]
    pieces = [trajectory.window(lo, hi) if hi - lo >= min_samples else None for lo, hi in windows]
    bounces = [
        Bounce(before, after, float(trajectory.t[contact]), float(trajectory.y[contact]))
        for before, after, contact in zip(pieces, pieces[1:], contacts, strict=False)
        if before is not None and after is not None
    ]
    return Flight(phases=[piece for piece in pieces if piece is not None], bounces=bounces)


def flight_phases(trajectory: Trajectory, *, min_samples: int = 8) -> list[Trajectory]:
    """The free-flight phases of a track. See `segment_flight`."""
    return segment_flight(trajectory, min_samples=min_samples).phases


def _moving_span(trajectory: Trajectory, radius_px: float) -> tuple[int, int]:
    """[start, stop) from the release frame to the last frame before the object comes to rest."""
    lead = _rest_samples(trajectory.x, trajectory.y, radius_px)
    trail = _rest_samples(trajectory.x[::-1], trajectory.y[::-1], radius_px)
    start = lead - 1 if lead > REST_MIN_STEPS else 0  # Keep the release frame.
    stop = len(trajectory) - trail if trail > REST_MIN_STEPS else len(trajectory)
    return start, stop


def _rest_samples(x: FloatArray, y: FloatArray, radius_px: float) -> int:
    """How many leading samples belong to the rest the object starts in. The rest ends where
    the object leaves for good, REST_MIN_STEPS samples in a row beyond `radius_px` of where it
    rested; one jittery sample outside does not end it."""
    settle = REST_MIN_STEPS + 1
    if x.size < settle:
        return 0
    anchor_x, anchor_y = float(np.median(x[:settle])), float(np.median(y[:settle]))
    outside = np.hypot(x - anchor_x, y - anchor_y) >= radius_px
    gone = np.lib.stride_tricks.sliding_window_view(outside, REST_MIN_STEPS).all(axis=1)
    left_at = np.flatnonzero(gone)
    return int(left_at[0]) if left_at.size else int(x.size)


def _jitter_px(trajectory: Trajectory) -> float:
    """The tracker's noise, in pixels, from second differences: true motion changes them
    slowly, jitter changes them every frame. Motion can only inflate the estimate, so the
    calmer axis is used."""
    if len(trajectory) < 5:
        return 0.0
    estimates = []
    for values in (trajectory.x, trajectory.y):
        second = np.diff(values, 2)
        mad = float(np.median(np.abs(second - np.median(second))))
        estimates.append(1.4826 * mad / math.sqrt(6))  # White noise: sd of 2nd diffs is sqrt(6).
    return min(estimates)


def _is_bounce(y: FloatArray, i: int, rise_px: float) -> bool:
    lowest = y[i] >= y[i - 1] and y[i] > y[i + 1]
    came_down = y[i] - y[i - 2] >= rise_px
    goes_up = y[i] - y[i + 2] >= rise_px
    return bool(lowest and came_down and goes_up)
