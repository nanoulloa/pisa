"""Read video metadata with ffprobe."""

from __future__ import annotations

import json
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Any

from pisa_contracts import VideoProbe


class ProbeError(RuntimeError):
    pass


def probe(path: Path, *, count_frames: bool = False) -> VideoProbe:
    """Describe the first video stream of `path`.

    `count_frames` decodes the whole file to get an exact frame count.
    """
    command = ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams"]
    if count_frames:
        command.append("-count_frames")
    result = subprocess.run(  # noqa: S603 (fixed argv, no shell)
        [*command, str(path)], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise ProbeError(f"ffprobe failed on {path.name}: {result.stderr.strip()}")
    return parse_probe(json.loads(result.stdout))


def parse_probe(report: dict[str, Any]) -> VideoProbe:
    streams: list[dict[str, Any]] = report.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        raise ProbeError("No video stream.")

    avg = _rate(video.get("avg_frame_rate")) or _rate(video.get("r_frame_rate"))
    if avg is None:
        raise ProbeError("Unknown frame rate.")
    real = _rate(video.get("r_frame_rate"))
    rotation = _rotation(video)
    width, height = int(video["width"]), int(video["height"])
    if rotation % 180 != 0:
        width, height = height, width

    frames = video.get("nb_read_frames") or video.get("nb_frames")
    fmt: dict[str, Any] = report.get("format", {})
    duration = float(video.get("duration") or fmt.get("duration") or 0.0)
    return VideoProbe(
        width=width,
        height=height,
        duration_s=duration,
        fps_num=avg.numerator,
        fps_den=avg.denominator,
        is_vfr=real is not None and abs(float(real) - float(avg)) > 0.01 * float(avg),
        rotation_deg=rotation,
        frame_count=int(frames) if frames is not None else None,
        codec=str(video.get("codec_name", "unknown")),
        has_audio=any(s.get("codec_type") == "audio" for s in streams),
        size_bytes=int(fmt.get("size", 0)),
    )


def _rate(value: object) -> Fraction | None:
    if not isinstance(value, str) or value in ("0/0", ""):
        return None
    rate = Fraction(value)
    return rate if rate > 0 else None


def _rotation(video: dict[str, Any]) -> int:
    for side_data in video.get("side_data_list", []):
        if "rotation" in side_data:
            return round(float(side_data["rotation"])) % 360
    rotate_tag = video.get("tags", {}).get("rotate")
    return int(rotate_tag) % 360 if rotate_tag is not None else 0
