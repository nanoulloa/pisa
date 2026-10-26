"""Tracking only where the plan says objects move freely.

Each phrase is tracked once, over the span of its events (SAM bills per frame, one phrase
per request), and only samples inside an event window are kept. Outside the windows a hand
holds, throws or catches the object, and that motion is not free fall.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from pisa_contracts import DataPolicy, Plan, Timebase, TrackedObject
from pisa_engine.ingest.normalize import trim_frames
from pisa_engine.tracking.segmenter import Segmenter


@dataclass(frozen=True, slots=True)
class Window:
    """Seconds from the start of the clip."""

    start_s: float
    end_s: float

    def contains(self, t_s: float) -> bool:
        return self.start_s <= t_s <= self.end_s


def event_windows(plan: Plan) -> dict[str, list[Window]]:
    """Each event phrase with its windows, sorted, overlapping ones merged."""
    windows: dict[str, list[Window]] = defaultdict(list)
    for event in plan.events:
        for phrase in event.object_phrases:
            windows[phrase].append(Window(event.start_s, event.end_s))
    return {phrase: _merged(spans) for phrase, spans in windows.items()}


def reference_windows(plan: Plan, events: dict[str, list[Window]]) -> dict[str, list[Window]]:
    """Reference objects that are not already tracked, over the first event's window: a
    scale needs a few frames of the object, not the whole clip."""
    spans = sorted((w for ws in events.values() for w in ws), key=lambda w: w.start_s)
    if not spans:
        return {}
    return {r.phrase: [spans[0]] for r in plan.references if r.phrase not in events}


async def track_windows(
    segmenter: Segmenter,
    video: Path,
    timebase: Timebase,
    windows: dict[str, list[Window]],
    work_dir: Path,
    *,
    policy: DataPolicy,
) -> list[TrackedObject]:
    """Track each phrase over its span, with frame indices and times in the whole clip."""
    tracked: list[TrackedObject] = []
    for index, (phrase, spans) in enumerate(windows.items()):
        first, count = _frames(timebase, spans[0].start_s, spans[-1].end_s)
        if count <= 0:
            continue
        clip, clip_timebase = video, timebase
        if first > 0 or count < timebase.frame_count:
            clip = work_dir / f"track-{index}.mp4"
            clip_timebase = trim_frames(video, timebase, first, count, clip)
        try:
            objects = await segmenter.track(clip, phrase, clip_timebase, policy=policy)
        finally:
            if clip != video:
                clip.unlink(missing_ok=True)
        for obj in objects:
            samples = [
                s.model_copy(update={"frame": s.frame + first})
                for s in obj.samples
                if any(w.contains(s.t_s - timebase.start_s) for w in spans)
            ]
            if samples:
                tracked.append(obj.model_copy(update={"samples": samples}))
    return tracked


def _frames(timebase: Timebase, start_s: float, end_s: float) -> tuple[int, int]:
    """First frame and frame count covering [start_s, end_s] of the clip."""
    per_s = timebase.fps_num / timebase.fps_den
    first = max(0, math.floor(start_s * per_s))
    last = min(timebase.frame_count - 1, math.ceil(end_s * per_s))
    return first, last - first + 1


def _merged(spans: list[Window]) -> list[Window]:
    merged: list[Window] = []
    for span in sorted(spans, key=lambda w: w.start_s):
        if merged and span.start_s <= merged[-1].end_s:
            last = merged[-1]
            merged[-1] = Window(last.start_s, max(last.end_s, span.end_s))
        else:
            merged.append(span)
    return merged
