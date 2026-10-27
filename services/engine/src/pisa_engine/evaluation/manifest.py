"""The eval set: which clips, what each one really is, and how it was made.

A manifest is a JSON file; clip paths are relative to it:

    {"name": "phone-v1", "clips": [
      {"id": "drop-01", "file": "real/drop-01.mp4", "truth": "real",
       "tags": ["drop", "static"], "source": "Pixel 8, 60 fps"},
      {"id": "drop-01-gen", "file": "generated/drop-01-gen.mp4", "truth": "generated",
       "tags": ["drop", "static"], "source": "generator name and version",
       "first_frame_of": "drop-01"}
    ]}

Clip files can show people, so they live in `eval/raw/`, which git ignores.
"""

from __future__ import annotations

from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pisa_contracts import EvalTruth


class Clip(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    file: str
    truth: EvalTruth
    # What the clip shows and how it was filmed, for the per-tag breakdown: drop, throw,
    # bounce, pair, static, handheld.
    tags: list[str] = Field(default_factory=list)
    # The phone and frame rate, or the generator and its version.
    source: str | None = None
    # For a generated clip: the real clip whose first frame it was generated from.
    first_frame_of: str | None = None
    notes: str | None = None


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    # True when every clip comes from the engine's own synthetic generator.
    synthetic: bool = False
    clips: list[Clip]

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        ids = [clip.id for clip in self.clips]
        repeated = sorted({i for i in ids if ids.count(i) > 1})
        if repeated:
            raise ValueError(f"repeated clip ids: {', '.join(repeated)}")
        real = {clip.id for clip in self.clips if clip.truth == "real"}
        for clip in self.clips:
            if clip.first_frame_of is not None and clip.first_frame_of not in real:
                raise ValueError(f"{clip.id}: first_frame_of names no real clip")
        return self


def load_manifest(path: Path) -> Manifest:
    return Manifest.model_validate_json(path.read_text(encoding="utf-8"))


def clip_path(manifest_path: Path, clip: Clip) -> Path:
    return (manifest_path.parent / clip.file).resolve()
