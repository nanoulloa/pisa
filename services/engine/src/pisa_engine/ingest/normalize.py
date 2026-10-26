"""Turn any phone or social video into the one format every later stage reads.

The output is an H.264 MP4 at a constant frame rate equal to the source's
average rate, with rotation applied and no audio. Constant frame rate makes
frame index -> time exact, which the physics depends on. Muse Spark only
accepts MP4, and SAM 3.1 accepts H.264 MP4.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from pisa_contracts import IngestResult, Timebase
from pisa_engine.ingest.probe import probe

MAX_DURATION_S = 60.0
# libx264 with yuv420p needs even dimensions.
_EVEN_SIZE = "scale=trunc(iw/2)*2:trunc(ih/2)*2"


class IngestError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code


@dataclass(frozen=True, slots=True)
class TimeWindow:
    start_s: float
    end_s: float


def normalize(source: Path, output: Path, *, window: TimeWindow | None = None) -> IngestResult:
    """Write the normalized clip to `output`, optionally trimmed to `window` of the source."""
    source_probe = probe(source)
    if source_probe.duration_s > MAX_DURATION_S:
        raise IngestError("video_too_long", f"{source_probe.duration_s:.1f} s > {MAX_DURATION_S} s")

    fps = Fraction(source_probe.fps_num, source_probe.fps_den)
    start_s = 0.0
    trim: list[str] = []
    if window is not None:
        start_s = max(0.0, window.start_s)
        end_s = min(source_probe.duration_s, window.end_s)
        if end_s <= start_s:
            raise IngestError("empty_window", f"{window.start_s}..{window.end_s} s")
        trim = ["-ss", f"{start_s:.6f}", "-t", f"{end_s - start_s:.6f}"]

    command = [
        "ffmpeg", "-v", "error", "-y",
        *trim,
        "-i", str(source),
        "-map", "0:v:0", "-an",
        "-vf", f"fps={fps.numerator}/{fps.denominator},{_EVEN_SIZE},format=yuv420p",
        "-fps_mode", "cfr",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-movflags", "+faststart",
        str(output),
    ]  # fmt: skip
    result = subprocess.run(command, capture_output=True, text=True, check=False)  # noqa: S603
    if result.returncode != 0:
        raise IngestError("transcode_failed", result.stderr.strip())

    normalized = probe(output, count_frames=True)
    return IngestResult(
        source=source_probe,
        normalized=normalized,
        timebase=Timebase(
            fps_num=normalized.fps_num,
            fps_den=normalized.fps_den,
            start_s=start_s,
            frame_count=normalized.frame_count or 0,
        ),
        scene_cuts_s=[],
    )
