"""Synthetic clips with known physics, for tests and for running the pipeline without API calls.

A ball is drawn with sub-pixel accuracy on a plain background and moves under
constant gravity, so every stage can be checked against the true trajectory.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import numpy.typing as npt

BACKGROUND_BGR = (236, 238, 236)
BALL_BGR = (0, 120, 255)  # Saturated orange, easy to threshold in HSV.
_SUBPIXEL_SHIFT = 4  # cv2 drawing uses fixed-point coordinates with 2**4 subdivisions.


@dataclass(frozen=True, slots=True)
class BallScene:
    """A ball launched at t=0. Image y points down, so gravity is positive."""

    g_mps2: float = 9.81
    pixels_per_meter: float = 400.0
    fps: int = 60
    duration_s: float = 0.6
    width: int = 640
    height: int = 960
    x0_px: float = 320.0
    y0_px: float = 80.0
    vx_mps: float = 0.0
    vy_mps: float = 0.0
    radius_px: float = 14.0

    @property
    def frame_count(self) -> int:
        return round(self.duration_s * self.fps)

    def true_trajectory(self) -> npt.NDArray[np.float64]:
        """Rows of (t, x, y) in seconds and pixels, one per frame."""
        t = np.arange(self.frame_count, dtype=np.float64) / self.fps
        x = self.x0_px + self.vx_mps * self.pixels_per_meter * t
        y = self.y0_px + (self.vy_mps * t + 0.5 * self.g_mps2 * t**2) * self.pixels_per_meter
        return np.column_stack([t, x, y])


def render(scene: BallScene, output: Path) -> None:
    """Encode the scene as an H.264 MP4 at a constant frame rate."""
    command = [
        "ffmpeg", "-v", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "bgr24",
        "-s", f"{scene.width}x{scene.height}", "-r", str(scene.fps),
        "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p",
        str(output),
    ]  # fmt: skip
    frames = b"".join(_draw(scene, x, y).tobytes() for _, x, y in scene.true_trajectory())
    subprocess.run(command, input=frames, capture_output=True, check=True)  # noqa: S603


def _draw(scene: BallScene, x: float, y: float) -> npt.NDArray[np.uint8]:
    frame = np.empty((scene.height, scene.width, 3), dtype=np.uint8)
    frame[:] = BACKGROUND_BGR
    scale = 1 << _SUBPIXEL_SHIFT
    cv2.circle(
        frame,
        (round(x * scale), round(y * scale)),
        round(scene.radius_px * scale),
        BALL_BGR,
        thickness=-1,
        lineType=cv2.LINE_AA,
        shift=_SUBPIXEL_SHIFT,
    )
    return frame
