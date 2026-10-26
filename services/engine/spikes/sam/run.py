"""SAM 3.1 tracking spike: clip in, trajectory, fit, plot and overlay video out.

Offline (free, no API calls):
    uv run --group spikes python services/engine/spikes/sam/run.py --synthetic --g 9.81

Real SAM 3.1 (only after PISA_PAID_CALLS_ENABLED=true; costs about $0.06 per 5 s at 60 fps):
    uv run --group spikes python services/engine/spikes/sam/run.py eval/raw/drop.mov \\
        --segmenter sam --phrase "tennis ball" --start 0.5 --end 2.5

Outputs go to services/engine/spikes/out/<name>/ (gitignored).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from pisa_contracts import TrackedObject, TrackSet
from pisa_engine.ingest.normalize import TimeWindow, normalize
from pisa_engine.model_api.client import MetaModelApiClient
from pisa_engine.model_api.spend import JsonlSpendLedger, PaidCallsDisabledError, SpendGuard
from pisa_engine.settings import get_settings
from pisa_engine.synthetic import BallScene, render
from pisa_engine.tracking.fake import ColorSegmenter
from pisa_engine.tracking.sam import Sam31Segmenter
from pisa_engine.tracking.segmenter import Segmenter

OUT_ROOT = Path(__file__).resolve().parents[1] / "out"
INK = "#0F3D3E"
LIME = "#B8C92A"  # Darker than the brand lime so the line reads on white.


def main() -> int:
    args = _parse_args()
    name = args.name or ("synthetic-g" + str(args.g) if args.synthetic else args.clip.stem)
    out = OUT_ROOT / name
    out.mkdir(parents=True, exist_ok=True)
    timings: dict[str, float] = {}

    if args.synthetic:
        scene = BallScene(g_mps2=args.g, vx_mps=args.vx)
        source = out / "source.mp4"
        render(scene, source)
        pixels_per_meter: float | None = scene.pixels_per_meter
    else:
        source = args.clip
        pixels_per_meter = args.pixels_per_meter

    started = time.perf_counter()
    window = TimeWindow(args.start, args.end) if args.end is not None else None
    ingest = normalize(source, out / "normalized.mp4", window=window)
    timings["ingest_s"] = time.perf_counter() - started
    (out / "ingest.json").write_text(ingest.model_dump_json(indent=2))

    settings = get_settings()
    ledger = JsonlSpendLedger(settings.spend_ledger_path)
    spent_before = ledger.total_usd()
    segmenter: Segmenter
    client: MetaModelApiClient | None = None
    if args.segmenter == "sam":
        guard = SpendGuard(
            enabled=settings.paid_calls_enabled, cap_usd=settings.spend_cap_usd, ledger=ledger
        )
        client = MetaModelApiClient(
            api_key=settings.meta_api_key, base_url=settings.meta_api_base_url, guard=guard
        )
        segmenter = Sam31Segmenter(
            client,
            model=settings.sam_model,
            on_raw_output=lambda text: _save(out / "sam_raw_output.txt", text),
        )
    else:
        segmenter = ColorSegmenter()

    started = time.perf_counter()
    try:
        objects = asyncio.run(
            segmenter.track(out / "normalized.mp4", args.phrase, ingest.timebase, policy="internal")
        )
    except PaidCallsDisabledError as error:
        print(error, file=sys.stderr)
        return 3
    finally:
        if client is not None:
            asyncio.run(client.aclose())
    timings["track_s"] = time.perf_counter() - started

    tracks = TrackSet(
        width=ingest.normalized.width,
        height=ingest.normalized.height,
        timebase=ingest.timebase,
        objects=objects,
    )
    (out / "track.json").write_text(tracks.model_dump_json(indent=2))

    fits = [_fit(obj, pixels_per_meter) for obj in objects if len(obj.samples) >= 5]
    summary = {
        "name": name,
        "segmenter": args.segmenter,
        "phrase": args.phrase,
        "frames": ingest.timebase.frame_count,
        "fps": ingest.timebase.fps_num / ingest.timebase.fps_den,
        "objects": len(objects),
        "fits": fits,
        "timings_s": {key: round(value, 3) for key, value in timings.items()},
        "usd_spent": round(ledger.total_usd() - spent_before, 6),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    if objects:
        _plot(objects[0], out / "trajectory.png")
        _overlay(out / "normalized.mp4", objects[0], out / "overlay.mp4")
    print(json.dumps(summary, indent=2))
    print(f"Outputs in {out}")
    return 0


def _save(path: Path, text: str) -> None:
    path.write_text(text)


def _fit(obj: TrackedObject, pixels_per_meter: float | None) -> dict[str, float | int | None]:
    """Least-squares y(t) = a/2 t^2 + v t + y0 in image pixels (y down)."""
    t = np.array([s.t_s for s in obj.samples])
    y = np.array([s.centroid.y for s in obj.samples])
    coefficients = np.polyfit(t, y, 2)
    residuals = y - np.polyval(coefficients, t)
    acceleration = 2 * float(coefficients[0])
    return {
        "object_id": obj.object_id,
        "samples": len(t),
        "acceleration_px_s2": round(acceleration, 2),
        "residual_rms_px": round(float(np.sqrt(np.mean(residuals**2))), 3),
        "implied_g_mps2": round(acceleration / pixels_per_meter, 3) if pixels_per_meter else None,
    }


def _plot(obj: TrackedObject, path: Path) -> None:
    t = np.array([s.t_s for s in obj.samples])
    y = np.array([s.centroid.y for s in obj.samples])
    coefficients = np.polyfit(t, y, 2)
    dense = np.linspace(t.min(), t.max(), 200)
    figure, (top, bottom) = plt.subplots(
        2, 1, figsize=(6, 6), sharex=True, gridspec_kw={"height_ratios": [3, 1]}
    )
    top.plot(
        dense, np.polyval(coefficients, dense), color=LIME, linewidth=2, label="Constant-g fit"
    )
    top.scatter(t, y, s=12, color=INK, label="Measured centroid", zorder=3)
    top.invert_yaxis()
    top.set_ylabel("Height in image (px, down)")
    top.legend(frameon=False)
    bottom.axhline(0, color="#8EB69B", linewidth=1)
    bottom.scatter(t, y - np.polyval(coefficients, t), s=8, color=INK)
    bottom.set_ylabel("Residual (px)")
    bottom.set_xlabel("Time (s)")
    for axis in (top, bottom):
        axis.spines[["top", "right"]].set_visible(False)
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def _overlay(video: Path, obj: TrackedObject, path: Path) -> None:
    """The clip with the box, the centroid and its trail drawn on each frame."""
    capture = cv2.VideoCapture(str(video))
    fps = capture.get(cv2.CAP_PROP_FPS)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    by_frame = {sample.frame: sample for sample in obj.samples}
    command = [
        "ffmpeg", "-v", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{width}x{height}", "-r", f"{fps}",
        "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(path),
    ]  # fmt: skip
    encoder = subprocess.Popen(command, stdin=subprocess.PIPE)  # noqa: S603
    assert encoder.stdin is not None
    trail: list[tuple[int, int]] = []
    frame_index = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        sample = by_frame.get(frame_index)
        if sample is not None:
            trail.append((round(sample.centroid.x), round(sample.centroid.y)))
            box = sample.bbox
            cv2.rectangle(
                frame,
                (round(box.x1), round(box.y1)),
                (round(box.x2), round(box.y2)),
                (62, 61, 15),
                2,
            )
        for point in trail:
            cv2.circle(frame, point, 3, (74, 232, 214), -1, lineType=cv2.LINE_AA)
        encoder.stdin.write(frame.tobytes())
        frame_index += 1
    capture.release()
    encoder.stdin.close()
    encoder.wait()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("clip", type=Path, nargs="?", help="Video file to analyze.")
    parser.add_argument("--synthetic", action="store_true", help="Render a synthetic fall instead.")
    parser.add_argument("--g", type=float, default=9.81, help="Gravity for --synthetic (m/s^2).")
    parser.add_argument("--vx", type=float, default=0.8, help="Horizontal speed for --synthetic.")
    parser.add_argument("--segmenter", choices=["fake", "sam"], default="fake")
    parser.add_argument("--phrase", default="ball", help="One concept phrase for SAM 3.1.")
    parser.add_argument("--start", type=float, default=0.0, help="Window start in the source (s).")
    parser.add_argument("--end", type=float, default=None, help="Window end in the source (s).")
    parser.add_argument("--pixels-per-meter", type=float, default=None)
    parser.add_argument("--name", default=None, help="Output folder name.")
    args = parser.parse_args()
    if not args.synthetic and args.clip is None:
        parser.error("give a clip path or --synthetic")
    return args


if __name__ == "__main__":
    sys.exit(main())
