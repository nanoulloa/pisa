"""Synthetic clips with known physics, for tests and for running the pipeline without API calls.

A ball is drawn with sub-pixel accuracy. It can fall under constant gravity (what real
physics does), ease in and out (what keyframed animation and many generated clips do), move
at constant speed, or bounce with a chosen restitution (above 1 is impossible). A second
ball can be released beside it with its own gravity, the background can be textured, and
the camera can shake, so every stage can be checked against the true trajectory.

CLI: python -m pisa_engine.synthetic --profile eased --out clip.mp4
     python -m pisa_engine.synthetic --companion-g 6 --vx 0 --duration 0.7 --out pair.mp4
"""

from __future__ import annotations

import argparse
import math
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
_MARGIN_PX = 48  # Extra canvas around the frame so a shaking camera never sees an edge.

MotionProfile = Literal["free_fall", "eased", "constant_velocity", "bounce"]
Rows = npt.NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class BallScene:
    """A ball held still for `hold_s`, then released. Image y points down, so gravity is positive.

    `eased` and `constant_velocity` cover the same distance in the same time as the free fall.
    `bounce` falls to `floor_y_px` and leaves each contact at `restitution` times its speed.
    """

    profile: MotionProfile = "free_fall"
    hold_s: float = 0.0
    g_mps2: float = 9.81
    restitution: float = 0.7
    floor_y_px: float = 880.0
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
    # A second ball released at the same moment, `companion_dx_px` to the right.
    companion_g_mps2: float | None = None
    companion_dx_px: float = 160.0
    # Background texture and camera shake, for stabilization.
    textured: bool = False
    camera_shake_px: float = 0.0
    # Random per-frame displacement of each drawn ball, like a tracker's jitter on real footage.
    position_noise_px: float = 0.0
    seed: int = 0

    @property
    def frame_count(self) -> int:
        return round(self.duration_s * self.fps)

    def true_trajectory(self) -> Rows:
        """Rows of (t, x, y) in seconds and scene pixels, one per frame."""
        return self._trajectory(self.g_mps2, 0.0)

    def companion_trajectory(self) -> Rows | None:
        if self.companion_g_mps2 is None:
            return None
        return self._trajectory(self.companion_g_mps2, self.companion_dx_px)

    def camera_offsets(self) -> Rows:
        """Per-frame camera position (dx, dy) in pixels: a smooth, deterministic hand shake."""
        if self.camera_shake_px == 0:
            return np.zeros((self.frame_count, 2))
        rng = np.random.default_rng(self.seed)
        t = np.arange(self.frame_count) / self.fps
        phases = rng.uniform(0, 2 * math.pi, 4)
        dx = np.sin(2 * math.pi * 1.3 * t + phases[0]) + 0.5 * np.sin(
            2 * math.pi * 3.1 * t + phases[1]
        )
        dy = np.sin(2 * math.pi * 1.7 * t + phases[2]) + 0.5 * np.sin(
            2 * math.pi * 2.6 * t + phases[3]
        )
        return np.column_stack([dx, dy]) * self.camera_shake_px / 1.5

    def _trajectory(self, g: float, dx_px: float) -> Rows:
        t = np.arange(self.frame_count, dtype=np.float64) / self.fps
        tau = np.clip(t - self.hold_s, 0.0, None)  # Time since release.
        flight = self.duration_s - self.hold_s
        drop_m = self.vy_mps * flight + 0.5 * g * flight**2
        if self.profile == "free_fall":
            fallen_m = self.vy_mps * tau + 0.5 * g * tau**2
        elif self.profile == "eased":
            s = tau / flight
            fallen_m = drop_m * (3 * s**2 - 2 * s**3)  # Smoothstep: speeds up, then slows down.
        elif self.profile == "constant_velocity":
            fallen_m = drop_m * tau / flight
        else:
            fallen_m = self._bouncing(tau, g)
        x = self.x0_px + dx_px + self.vx_mps * self.pixels_per_meter * tau
        y = self.y0_px + fallen_m * self.pixels_per_meter
        return np.column_stack([t, x, y])

    def _bouncing(self, tau: npt.NDArray[np.float64], g: float) -> npt.NDArray[np.float64]:
        """Distance fallen (m) for a ball that bounces on the floor with this restitution."""
        floor_m = (self.floor_y_px - self.y0_px) / self.pixels_per_meter
        fallen = np.empty_like(tau)
        for i, time in enumerate(tau):
            start, height, speed = 0.0, 0.0, self.vy_mps  # Phase start, fallen at start, speed.
            while True:
                if height == floor_m and abs(speed) < 0.05:  # Too slow to leave the floor.
                    fallen[i] = floor_m
                    break
                # Time to reach the floor from `height` with downward speed `speed`.
                distance = floor_m - height
                hit = (-speed + math.sqrt(speed**2 + 2 * g * distance)) / g
                if time - start < hit or hit <= 1e-9:
                    dt = time - start
                    fallen[i] = height + speed * dt + 0.5 * g * dt**2
                    break
                start += hit
                height = floor_m
                speed = -self.restitution * (speed + g * hit)  # Leaves the floor going up.
        return fallen


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
    background = _background(scene)
    balls = [scene.true_trajectory()]
    companion = scene.companion_trajectory()
    if companion is not None:
        balls.append(companion)
    if scene.position_noise_px > 0:  # The true trajectory stays exact; only the drawing jitters.
        rng = np.random.default_rng(scene.seed + 2)
        for rows in balls:
            rows[:, 1:] += rng.normal(0.0, scene.position_noise_px, (len(rows), 2))
    offsets = scene.camera_offsets()
    frames = []
    for index, (dx, dy) in enumerate(offsets):
        canvas = background.copy()
        for rows in balls:
            _draw_ball(canvas, scene, rows[index, 1] + _MARGIN_PX, rows[index, 2] + _MARGIN_PX)
        # The camera looks at the scene from (margin + shake): content moves the other way.
        view = np.array([[1, 0, -(_MARGIN_PX + dx)], [0, 1, -(_MARGIN_PX + dy)]], dtype=np.float64)
        frame = cv2.warpAffine(canvas, view, (scene.width, scene.height), flags=cv2.INTER_LINEAR)
        frames.append(frame.tobytes())
    subprocess.run(command, input=b"".join(frames), capture_output=True, check=True)  # noqa: S603


def _background(scene: BallScene) -> npt.NDArray[np.uint8]:
    shape = (scene.height + 2 * _MARGIN_PX, scene.width + 2 * _MARGIN_PX, 3)
    canvas = np.empty(shape, dtype=np.uint8)
    canvas[:] = BACKGROUND_BGR
    if not scene.textured:
        return canvas
    # Gray shapes give a stabilizer corners to follow without ever looking orange.
    rng = np.random.default_rng(scene.seed + 1)
    for _ in range(140):
        x, y = int(rng.integers(0, shape[1])), int(rng.integers(0, shape[0]))
        w, h = int(rng.integers(8, 60)), int(rng.integers(8, 60))
        shade = int(rng.integers(40, 200))
        cv2.rectangle(canvas, (x, y), (x + w, y + h), (shade, shade, shade), thickness=-1)
    return canvas


def _draw_ball(canvas: npt.NDArray[np.uint8], scene: BallScene, x: float, y: float) -> None:
    scale = 1 << _SUBPIXEL_SHIFT
    cv2.circle(
        canvas,
        (round(x * scale), round(y * scale)),
        round(scene.radius_px * scale),
        BALL_BGR,
        thickness=-1,
        lineType=cv2.LINE_AA,
        shift=_SUBPIXEL_SHIFT,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a synthetic clip with known motion.")
    parser.add_argument("--profile", choices=["free_fall", "eased", "constant_velocity", "bounce"])
    parser.add_argument("--g", type=float, default=9.81, help="Gravity in m/s^2.")
    parser.add_argument("--restitution", type=float, default=0.7, help="For --profile bounce.")
    parser.add_argument("--hold", type=float, default=0.0, help="Seconds held before release.")
    parser.add_argument("--duration", type=float, default=0.6, help="Clip length in seconds.")
    parser.add_argument("--vx", type=float, default=0.8, help="Horizontal speed in m/s.")
    parser.add_argument("--companion-g", type=float, help="Drop a second ball with this gravity.")
    parser.add_argument("--shake", type=float, default=0.0, help="Camera shake in pixels.")
    parser.add_argument("--textured", action="store_true", help="Draw a textured background.")
    parser.add_argument("--noise", type=float, default=0.0, help="Position jitter in pixels.")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    scene = BallScene(
        profile=args.profile or "free_fall",
        hold_s=args.hold,
        g_mps2=args.g,
        restitution=args.restitution,
        duration_s=args.duration,
        vx_mps=args.vx,
        companion_g_mps2=args.companion_g,
        textured=args.textured or args.shake > 0,
        camera_shake_px=args.shake,
        position_noise_px=args.noise,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    render(scene, args.out)


if __name__ == "__main__":
    main()
