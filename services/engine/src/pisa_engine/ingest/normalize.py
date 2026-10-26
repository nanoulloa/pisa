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
from pisa_engine.ingest.probe import SAFE_INPUT_ARGS, ProbeError, ffmpeg_path, probe

MAX_DURATION_S = 60.0
MAX_SIDE_PX = 4096
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
    """Write the normalized clip to `output`, optionally trimmed to `window` of the source.

    The source is untrusted: its container and metadata are checked, the output is capped
    at MAX_DURATION_S whatever the metadata claims, and the result is measured again.
    """
    try:
        source_probe = probe(source)
    except ProbeError as error:
        raise IngestError("unsupported_format", str(error)) from error
    if source_probe.duration_s <= 0:
        raise IngestError("unknown_duration", "the file reports no duration")
    if source_probe.duration_s > MAX_DURATION_S:
        raise IngestError("video_too_long", f"{source_probe.duration_s:.1f} s > {MAX_DURATION_S} s")
    if max(source_probe.width, source_probe.height) > MAX_SIDE_PX:
        raise IngestError("resolution_too_high", f"{source_probe.width}x{source_probe.height}")

    fps = Fraction(source_probe.fps_num, source_probe.fps_den)
    start_s, end_s = 0.0, source_probe.duration_s
    if window is not None:
        start_s = max(0.0, window.start_s)
        end_s = min(source_probe.duration_s, window.end_s)
        if end_s <= start_s:
            raise IngestError("empty_window", f"{window.start_s}..{window.end_s} s")
    length_s = min(end_s - start_s, MAX_DURATION_S)

    command = [
        "ffmpeg", "-v", "error", "-y",
        "-ss", f"{start_s:.6f}", "-t", f"{length_s:.6f}",
        *SAFE_INPUT_ARGS, "-i", ffmpeg_path(source),
        "-map", "0:v:0", "-an",
        "-vf", f"fps={fps.numerator}/{fps.denominator},{_EVEN_SIZE},format=yuv420p",
        "-fps_mode", "cfr",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-movflags", "+faststart",
        ffmpeg_path(output),
    ]  # fmt: skip
    result = subprocess.run(command, capture_output=True, text=True, check=False)  # noqa: S603
    if result.returncode != 0:
        raise IngestError("transcode_failed", result.stderr.strip())

    normalized = probe(output, count_frames=True)
    if normalized.duration_s > MAX_DURATION_S + 1 / float(fps):
        raise IngestError("video_too_long", f"decoded {normalized.duration_s:.1f} s")
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


def trim_frames(clip: Path, timebase: Timebase, first: int, count: int, output: Path) -> Timebase:
    """Frames [first, first + count) of a normalized clip, encoded the same way, and their
    timebase. Used to send SAM only the frames an event needs: it bills per frame."""
    fps = f"{timebase.fps_num}/{timebase.fps_den}"
    command = [
        "ffmpeg", "-v", "error", "-y",
        *SAFE_INPUT_ARGS, "-i", ffmpeg_path(clip),
        "-map", "0:v:0", "-an",
        "-vf", f"trim=start_frame={first}:end_frame={first + count},setpts=PTS-STARTPTS",
        "-fps_mode", "cfr", "-r", fps,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-movflags", "+faststart",
        ffmpeg_path(output),
    ]  # fmt: skip
    result = subprocess.run(command, capture_output=True, text=True, check=False)  # noqa: S603
    if result.returncode != 0:
        raise IngestError("transcode_failed", result.stderr.strip())
    trimmed = probe(output, count_frames=True)
    if trimmed.frame_count != count:
        raise IngestError("trim_failed", f"expected {count} frames, got {trimmed.frame_count}")
    return Timebase(
        fps_num=timebase.fps_num,
        fps_den=timebase.fps_den,
        start_s=timebase.start_s + first * timebase.fps_den / timebase.fps_num,
        frame_count=count,
    )
