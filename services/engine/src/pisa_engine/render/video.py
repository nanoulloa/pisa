"""The evidence video: the clip with the object outlined, its measured points and the ghost.

Only the measured events are shown, with half a second around them, and short events play
at half speed so the ghost can be followed. After a bounce only the new phase's ghost moves;
the earlier ones leave their paths and measured points behind as a trail. Ghosts live in
stabilized coordinates; each frame maps them back through the inverse of its camera
transform, so on a shaky clip the ghost stays next to the object, not next to the frame.
The output is H.264 in an MP4 that WhatsApp accepts (under 16 MB).
"""

from __future__ import annotations

import math
import subprocess
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import numpy.typing as npt

from pisa_contracts import Timebase, TrackedObject, TrackSample
from pisa_engine.physics.trajectory import FloatArray
from pisa_engine.render.ghost import Ghost
from pisa_engine.vision.stabilize import CameraPath

Image = npt.NDArray[np.uint8]

# Brand colors in OpenCV's BGR order: ink #0F3D3E, paper #FBFCFC, lime #D4E64A.
INK = (62, 61, 15)
PAPER = (252, 252, 251)
LIME = (74, 230, 212)

MAX_SIDE_PX = 1280
MAX_SOURCE_S = 12.0
PAD_S = 0.5
SLOW_BELOW_S = 4.0
MAX_BYTES = 16 * 1024 * 1024
GHOST_ALPHA = 0.65
_SHIFT = 4  # Sub-pixel drawing: OpenCV fixed point with 2**4 subdivisions.


@dataclass(frozen=True, slots=True)
class RenderedVideo:
    path: Path
    width: int
    height: int
    duration_s: float
    playback_rate: float
    start_s: float  # Clip time of the first frame.
    size_bytes: int


class RenderError(RuntimeError):
    pass


def render_evidence(
    clip: Path,
    timebase: Timebase,
    camera: CameraPath,
    objects: Sequence[TrackedObject],
    found: Sequence[Ghost],
    output: Path,
) -> RenderedVideo | None:
    """Draw the evidence for `found` ghosts on `clip`. None when there is nothing to show."""
    if not found:
        return None
    fps = timebase.fps_num / timebase.fps_den
    first, last = _frame_span(timebase, found)
    shown_s = (last - first + 1) / fps
    rate = 0.5 if shown_s < SLOW_BELOW_S else 1.0

    capture = cv2.VideoCapture(str(clip))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    scale = min(1.0, MAX_SIDE_PX / max(width, height))
    out_w, out_h = _even(width * scale), _even(height * scale)
    owners = {(g.phrase, g.object_id) for g in found}
    samples = _samples_by_frame(objects, owners)
    radii = {key: _radius(obj.samples) for obj in objects if (key := (obj.phrase, obj.object_id))}

    command = [
        "ffmpeg", "-v", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{out_w}x{out_h}",
        "-r", f"{timebase.fps_num}/{timebase.fps_den}", "-i", "-",
        "-vf", f"setpts={1 / rate:g}*PTS", "-r", f"{timebase.fps_num}/{timebase.fps_den}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-maxrate", "2M", "-bufsize", "4M",
        # Main profile without B-frames, the moov box first: what WhatsApp on Android plays.
        "-pix_fmt", "yuv420p", "-profile:v", "main", "-bf", "0",
        "-movflags", "+faststart", "-an",
        str(output),
    ]  # fmt: skip
    encoder = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)  # noqa: S603
    assert encoder.stdin is not None
    try:
        capture.set(cv2.CAP_PROP_POS_FRAMES, first)
        for index in range(first, last + 1):
            ok, raw = capture.read()
            if not ok:
                break
            resized = cv2.resize(raw, (out_w, out_h), interpolation=cv2.INTER_AREA)
            frame = np.asarray(resized, dtype=np.uint8)
            t = timebase.start_s + index / fps
            to_frame = _to_frame(camera, index) * scale  # Output pixels are scaled pixels.
            for ghost in found:
                radius = radii.get((ghost.phrase, ghost.object_id), 12.0) * scale
                _draw_ghost(frame, ghost, t, to_frame, radius)
            for sample in samples.get(index, []):
                radius = radii.get((sample[0], sample[1]), 12.0) * scale
                _draw_outline(frame, sample[2], scale, radius)
            encoder.stdin.write(frame.tobytes())
    finally:
        capture.release()
        encoder.stdin.close()
        stderr = encoder.stderr.read().decode() if encoder.stderr else ""
        encoder.wait()
    if encoder.returncode != 0:
        raise RenderError(stderr.strip())
    size = output.stat().st_size
    if size > MAX_BYTES:
        output.unlink(missing_ok=True)
        return None
    return RenderedVideo(
        path=output,
        width=out_w,
        height=out_h,
        duration_s=round(shown_s / rate, 3),
        playback_rate=rate,
        start_s=round(timebase.start_s + first / fps, 4),
        size_bytes=size,
    )


def _frame_span(timebase: Timebase, found: Sequence[Ghost]) -> tuple[int, int]:
    """Frames covering every ghost plus padding, at most MAX_SOURCE_S around the first one."""
    fps = timebase.fps_num / timebase.fps_den
    duration = timebase.frame_count / fps
    start = min(g.start_s for g in found) - timebase.start_s - PAD_S
    end = max(g.end_s for g in found) - timebase.start_s + PAD_S
    if end - start > MAX_SOURCE_S:  # Keep the most telling ghost, which comes first.
        start = found[0].start_s - timebase.start_s - PAD_S
        end = start + MAX_SOURCE_S
    first = max(0, math.floor(max(start, 0.0) * fps))
    last = min(timebase.frame_count - 1, math.ceil(min(end, duration) * fps))
    return first, last


def _to_frame(camera: CameraPath, index: int) -> FloatArray:
    """2 x 3 affine from stabilized coordinates to this frame's pixels."""
    if camera.static or index >= len(camera.to_reference):
        return np.eye(3)[:2]
    return np.asarray(np.linalg.inv(camera.to_reference[index])[:2], dtype=np.float64)


def _draw_ghost(frame: Image, ghost: Ghost, t: float, to_frame: FloatArray, radius: float) -> None:
    """The ghost, the path it took, and where the object was measured before now. The path
    and the ghost are translucent and nothing is drawn at the object's current position, so
    the object itself always stays visible. Once the object's next phase has started only the
    path and the points remain: a ghost parked on the floor would say the object should not
    have bounced."""
    if t < ghost.start_s:
        return
    shown = ghost.gone_s is None or t < ghost.gone_s
    now = min(t, ghost.end_s)
    steps = max(2, int((now - ghost.start_s) * 120) + 1)
    times = np.linspace(ghost.start_s, now, steps)
    path = _apply(to_frame, *ghost.position(times))
    earlier = ghost.measured.t < t - 1e-6
    points = _apply(to_frame, ghost.measured.x[earlier], ghost.measured.y[earlier])

    overlay = frame.copy()
    if len(path) >= 2:
        line = (path * (1 << _SHIFT)).round().astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(overlay, [line], False, LIME, 3, cv2.LINE_AA, _SHIFT)
    x, y = path[-1]
    if shown:
        _circle(overlay, x, y, radius, LIME, -1)
    cv2.addWeighted(overlay, GHOST_ALPHA, frame, 1 - GHOST_ALPHA, 0, dst=frame)
    if shown:
        _circle(frame, x, y, radius, INK, 2)
    for px, py in points[:-1]:  # Where the object was measured, up to its last position.
        _circle(frame, px, py, 3.0, PAPER, -1)
        _circle(frame, px, py, 3.0, INK, 1)


def _draw_outline(frame: Image, sample: TrackSample, scale: float, radius: float) -> None:
    """A two-tone ring around the tracked object, readable on dark and light footage."""
    x, y = sample.centroid.x * scale, sample.centroid.y * scale
    _circle(frame, x, y, radius + 6, PAPER, 4)
    _circle(frame, x, y, radius + 6, INK, 2)


def _circle(
    frame: Image, x: float, y: float, radius: float, color: tuple[int, int, int], thickness: int
) -> None:
    unit = 1 << _SHIFT
    center = (round(x * unit), round(y * unit))
    cv2.circle(frame, center, round(radius * unit), color, thickness, cv2.LINE_AA, _SHIFT)


def _apply(to_frame: FloatArray, x: FloatArray, y: FloatArray) -> FloatArray:
    points = np.column_stack([x, y, np.ones_like(x)])
    return np.asarray(points @ to_frame.T, dtype=np.float64)


def _samples_by_frame(
    objects: Sequence[TrackedObject], owners: set[tuple[str, int]]
) -> dict[int, list[tuple[str, int, TrackSample]]]:
    by_frame: dict[int, list[tuple[str, int, TrackSample]]] = defaultdict(list)
    for obj in objects:
        if (obj.phrase, obj.object_id) in owners:
            for sample in obj.samples:
                by_frame[sample.frame].append((obj.phrase, obj.object_id, sample))
    return by_frame


def _radius(samples: Sequence[TrackSample]) -> float:
    """Half the object's typical size: the narrower side of its box, which blur does not grow."""
    if not samples:
        return 12.0
    sides = [min(s.bbox.x2 - s.bbox.x1, s.bbox.y2 - s.bbox.y1) for s in samples]
    return max(4.0, float(np.median(sides)) / 2)


def _even(value: float) -> int:
    return max(2, int(value) // 2 * 2)
