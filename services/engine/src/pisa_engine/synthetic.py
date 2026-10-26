"""Synthetic clips with known physics, for tests and for running the pipeline without API calls.

A ball is drawn with sub-pixel accuracy on a plain background. It can fall under constant
gravity (what real physics does), ease in and out (what keyframed animation and many
generated clips do), or move at constant speed. Every stage can be checked against the
true trajectory.

CLI: python -m pisa_engine.synthetic --profile eased --out clip.mp4
"""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
import numpy.typing as npt

BACKGROUND_BGR = (236, 238, 236)
BALL_BGR = (0, 120, 255)  # Saturated orange, easy to threshold in HSV.
_SUBPIXEL_SHIFT = 4  # cv2 drawing uses fixed-point coordinates with 2**4 subdivisions.

MotionProfile = Literal["free_fall", "eased", "constant_velocity"]


@dataclass(frozen=True, slots=True)
class BallScene:
    """A ball held still for `hold_s`, then released. Image y points down, so gravity is positive.

    `eased` and `constant_velocity` cover the same distance in the same time as the free fall.
    """

    profile: MotionProfile = "free_fall"
    hold_s: float = 0.0
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
        tau = np.clip(t - self.hold_s, 0.0, None)  # Time since release.
        flight = self.duration_s - self.hold_s
        drop_m = self.vy_mps * flight + 0.5 * self.g_mps2 * flight**2
        if self.profile == "free_fall":
            fallen_m = self.vy_mps * tau + 0.5 * self.g_mps2 * tau**2
        elif self.profile == "eased":
            s = tau / flight
            fallen_m = drop_m * (3 * s**2 - 2 * s**3)  # Smoothstep: speeds up, then slows down.
        else:
            fallen_m = drop_m * tau / flight
        x = self.x0_px + self.vx_mps * self.pixels_per_meter * tau
        y = self.y0_px + fallen_m * self.pixels_per_meter
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a synthetic clip with known motion.")
    parser.add_argument("--profile", choices=["free_fall", "eased", "constant_velocity"])
    parser.add_argument("--g", type=float, default=9.81, help="Gravity in m/s^2.")
    parser.add_argument("--hold", type=float, default=0.0, help="Seconds held before release.")
    parser.add_argument("--duration", type=float, default=0.6, help="Clip length in seconds.")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    scene = BallScene(
        profile=args.profile or "free_fall",
        hold_s=args.hold,
        g_mps2=args.g,
        duration_s=args.duration,
        vx_mps=0.8,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    render(scene, args.out)


if __name__ == "__main__":
    main()
