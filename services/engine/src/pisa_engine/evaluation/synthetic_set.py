"""A synthetic eval set with known physics: a free check that the whole eval runs.

"Real" clips follow real physics; "generated" clips break it the ways video generators do.
A few clips are there to show limits honestly rather than to be caught:

- a real fall filmed in slow motion looks like low gravity, and a generated fall with low
  gravity looks the same; without a scale and a trusted frame rate no test can tell them
  apart, so Pisa calls both consistent;
- motion at constant speed has no acceleration to measure, so it is inconclusive.

Positions jitter by one or two pixels, about what a tracker adds on real footage.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from pisa_contracts import EvalTruth
from pisa_engine.evaluation.manifest import Clip, Manifest
from pisa_engine.synthetic import BallScene, render


@dataclass(frozen=True, slots=True)
class SyntheticClip:
    id: str
    truth: EvalTruth
    tags: tuple[str, ...]
    scene: BallScene
    notes: str | None = None


_DROP = BallScene(hold_s=0.1, duration_s=0.7, position_noise_px=1.0)
_THROW = BallScene(
    hold_s=0.1,
    duration_s=0.9,
    x0_px=120.0,
    y0_px=600.0,
    vx_mps=1.0,
    vy_mps=-3.5,
    position_noise_px=1.0,
)
_BOUNCE = BallScene(profile="bounce", duration_s=1.4, position_noise_px=1.0)
_GAINING = replace(_BOUNCE, y0_px=400.0, duration_s=1.0)


def _handheld(scene: BallScene) -> BallScene:
    """A textured background the stabilizer can follow, filmed by a shaking hand."""
    return replace(scene, textured=True, camera_shake_px=6.0)


def _clip(
    clip_id: str, truth: EvalTruth, tags: str, scene: BallScene, notes: str | None = None
) -> SyntheticClip:
    return SyntheticClip(clip_id, truth, tuple(tags.split()), scene, notes)


SYNTHETIC_SET: tuple[SyntheticClip, ...] = (
    # Real physics.
    _clip("drop-still", "real", "drop static", replace(_DROP, position_noise_px=0.5, seed=1)),
    _clip("drop-sideways", "real", "drop static", replace(_DROP, vx_mps=0.5, seed=2)),
    _clip(
        "drop-jittery",
        "real",
        "drop static",
        replace(_DROP, vx_mps=0.8, position_noise_px=2.0, seed=3),
    ),
    _clip("drop-handheld", "real", "drop handheld", _handheld(replace(_DROP, vx_mps=0.5, seed=4))),
    _clip("throw", "real", "throw static", replace(_THROW, seed=5)),
    _clip("throw-handheld", "real", "throw handheld", _handheld(replace(_THROW, seed=6))),
    _clip(
        "bounce-soft",
        "real",
        "bounce static",
        replace(_BOUNCE, restitution=0.6, vx_mps=0.5, seed=7),
    ),
    _clip(
        "bounce-lively",
        "real",
        "bounce static",
        replace(_BOUNCE, restitution=0.8, vx_mps=0.3, seed=8),
    ),
    _clip(
        "bounce-handheld",
        "real",
        "bounce handheld",
        _handheld(replace(_BOUNCE, vx_mps=0.3, seed=9)),
    ),
    _clip("pair-together", "real", "pair static", replace(_DROP, companion_g_mps2=9.81, seed=10)),
    _clip(
        "pair-together-sideways",
        "real",
        "pair static",
        replace(_DROP, companion_g_mps2=9.81, vx_mps=0.3, position_noise_px=1.5, seed=11),
    ),
    _clip(
        "drop-slow-motion",
        "real",
        "drop static slow-motion",
        replace(_DROP, g_mps2=9.81 / 4, seed=12),
        "A real fall at quarter speed.",
    ),
    # Broken physics, the ways video generators break it.
    _clip("eased-drop", "generated", "drop static", replace(_DROP, profile="eased", seed=21)),
    _clip(
        "eased-drop-sideways",
        "generated",
        "drop static",
        replace(_DROP, profile="eased", vx_mps=0.5, position_noise_px=2.0, seed=22),
    ),
    _clip(
        "eased-drop-handheld",
        "generated",
        "drop handheld",
        _handheld(replace(_DROP, profile="eased", seed=23)),
    ),
    _clip(
        "bounce-gains-energy",
        "generated",
        "bounce static",
        replace(_GAINING, restitution=1.15, vx_mps=0.5, seed=24),
    ),
    _clip(
        "bounce-gains-more",
        "generated",
        "bounce static",
        replace(_GAINING, restitution=1.3, vx_mps=0.3, seed=25),
    ),
    _clip("pair-apart", "generated", "pair static", replace(_DROP, companion_g_mps2=6.0, seed=26)),
    _clip(
        "pair-far-apart",
        "generated",
        "pair static",
        replace(_DROP, companion_g_mps2=4.0, vx_mps=0.3, seed=27),
    ),
    _clip(
        "constant-speed-drop",
        "generated",
        "drop static",
        replace(_DROP, profile="constant_velocity", seed=28),
        "No acceleration to measure.",
    ),
    _clip(
        "low-gravity-drop",
        "generated",
        "drop static low-gravity",
        replace(_DROP, g_mps2=2.5, seed=29),
        "Looks just like slow motion.",
    ),
    _clip(
        "low-gravity-bounce",
        "generated",
        "bounce static low-gravity",
        replace(_BOUNCE, g_mps2=3.0, duration_s=2.2, vx_mps=0.1, seed=30),
        "Every flight has the same low gravity.",
    ),
)


def write_synthetic_set(folder: Path) -> Path:
    """Renders every clip into `folder` and returns the path of its manifest."""
    folder.mkdir(parents=True, exist_ok=True)
    for item in SYNTHETIC_SET:
        render(item.scene, folder / f"{item.id}.mp4")
    manifest = Manifest(
        name="synthetic",
        synthetic=True,
        clips=[
            Clip(
                id=item.id,
                file=f"{item.id}.mp4",
                truth=item.truth,
                tags=list(item.tags),
                source="pisa_engine.synthetic",
                notes=item.notes,
            )
            for item in SYNTHETIC_SET
        ],
    )
    path = folder / "manifest.json"
    path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return path
