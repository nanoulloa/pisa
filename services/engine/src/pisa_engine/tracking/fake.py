"""A free, offline stand-in for SAM 3.1 that segments the synthetic balls by color."""

from __future__ import annotations

import asyncio
from pathlib import Path

import cv2
import numpy as np

from pisa_contracts import BBox, DataPolicy, Point2, Timebase, TrackedObject, TrackSample
from pisa_engine.tracking.segmenter import frame_time

# HSV range around the synthetic balls' orange (OpenCV hue runs 0..179).
_LOWER_HSV = np.array([5, 150, 150], dtype=np.uint8)
_UPPER_HSV = np.array([25, 255, 255], dtype=np.uint8)
_MIN_AREA_PX = 20
# A ball moves less than this between frames, so the nearest blob is the same ball.
_MAX_STEP_PX = 120.0


class ColorSegmenter:
    """Tracks every saturated-orange blob, keeping ids by nearest position. Ignores the phrase."""

    async def track(
        self, video: Path, phrase: str, timebase: Timebase, *, policy: DataPolicy
    ) -> list[TrackedObject]:
        return await asyncio.to_thread(_track, video, phrase, timebase)


def _track(video: Path, phrase: str, timebase: Timebase) -> list[TrackedObject]:
    capture = cv2.VideoCapture(str(video))
    tracks: list[list[TrackSample]] = []
    frame_index = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            for sample in _segment(frame, frame_index, timebase):
                _assign(tracks, sample)
            frame_index += 1
    finally:
        capture.release()
    return [
        TrackedObject(phrase=phrase, object_id=index, samples=samples)
        for index, samples in enumerate(tracks)
    ]


def _segment(frame: np.ndarray, frame_index: int, timebase: Timebase) -> list[TrackSample]:
    mask = cv2.inRange(cv2.cvtColor(frame, cv2.COLOR_BGR2HSV), _LOWER_HSV, _UPPER_HSV)
    count, _, stats, centroids = cv2.connectedComponentsWithStats(mask)
    samples = []
    for label in range(1, count):  # Label 0 is the background.
        x, y, w, h, area = (int(v) for v in stats[label])
        if area < _MIN_AREA_PX:
            continue
        cx, cy = (float(v) for v in centroids[label])
        samples.append(
            TrackSample(
                frame=frame_index,
                t_s=frame_time(timebase, frame_index),
                bbox=BBox(x1=x, y1=y, x2=x + w, y2=y + h),
                centroid=Point2(x=cx, y=cy),
                area_px=area,
                confidence=None,
            )
        )
    return samples


def _assign(tracks: list[list[TrackSample]], sample: TrackSample) -> None:
    """Appends the sample to the track whose last position is nearest, or starts a new one."""
    best, best_distance = None, _MAX_STEP_PX
    for track in tracks:
        last = track[-1]
        if last.frame == sample.frame:
            continue  # That track already has its blob for this frame.
        distance = float(
            np.hypot(last.centroid.x - sample.centroid.x, last.centroid.y - sample.centroid.y)
        )
        if distance < best_distance:
            best, best_distance = track, distance
    if best is None:
        tracks.append([sample])
    else:
        best.append(sample)
