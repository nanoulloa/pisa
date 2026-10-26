"""A free, offline stand-in for SAM 3.1 that segments the synthetic ball by color."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from pisa_contracts import BBox, DataPolicy, Point2, Timebase, TrackedObject, TrackSample
from pisa_engine.tracking.segmenter import frame_time

# HSV range around the synthetic ball's orange (OpenCV hue runs 0..179).
_LOWER_HSV = np.array([5, 150, 150], dtype=np.uint8)
_UPPER_HSV = np.array([25, 255, 255], dtype=np.uint8)


class ColorSegmenter:
    """Tracks one saturated-orange object per frame. Ignores the phrase."""

    async def track(
        self, video: Path, phrase: str, timebase: Timebase, *, policy: DataPolicy
    ) -> list[TrackedObject]:
        capture = cv2.VideoCapture(str(video))
        samples: list[TrackSample] = []
        frame_index = 0
        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                sample = _segment(frame, frame_index, timebase)
                if sample is not None:
                    samples.append(sample)
                frame_index += 1
        finally:
            capture.release()
        return [TrackedObject(phrase=phrase, object_id=0, samples=samples)] if samples else []


def _segment(frame: np.ndarray, frame_index: int, timebase: Timebase) -> TrackSample | None:
    mask = cv2.inRange(cv2.cvtColor(frame, cv2.COLOR_BGR2HSV), _LOWER_HSV, _UPPER_HSV)
    moments = cv2.moments(mask, binaryImage=True)
    if moments["m00"] <= 0:
        return None
    x, y, w, h = cv2.boundingRect(mask)
    return TrackSample(
        frame=frame_index,
        t_s=frame_time(timebase, frame_index),
        bbox=BBox(x1=x, y1=y, x2=x + w, y2=y + h),
        centroid=Point2(x=moments["m10"] / moments["m00"], y=moments["m01"] / moments["m00"]),
        area_px=moments["m00"],
        confidence=None,
    )
