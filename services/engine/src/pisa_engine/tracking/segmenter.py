"""The tracking interface every segmenter implements."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pisa_contracts import DataPolicy, Timebase, TrackedObject


class Segmenter(Protocol):
    async def track(
        self, video: Path, phrase: str, timebase: Timebase, *, policy: DataPolicy
    ) -> list[TrackedObject]:
        """Detect and track every instance of `phrase` in a constant-frame-rate clip."""
        ...


def frame_time(timebase: Timebase, frame: int) -> float:
    return timebase.start_s + frame * timebase.fps_den / timebase.fps_num
