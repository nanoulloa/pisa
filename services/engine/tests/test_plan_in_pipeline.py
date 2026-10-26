"""The plan drives the pipeline: windows keep hands out, references give T4 a scale."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

import pisa_contracts as contracts
from pisa_contracts import (
    BBox,
    DataPolicy,
    Explanation,
    IngestResult,
    Locale,
    Plan,
    Point2,
    ReferenceObject,
    Timebase,
    TrackedObject,
    TrackSample,
    Verdict,
)
from pisa_engine.api import create_app
from pisa_engine.ingest.normalize import normalize, trim_frames
from pisa_engine.physics.scale import best_scale, pixel_size
from pisa_engine.planning.planner import checked
from pisa_engine.settings import Settings
from pisa_engine.synthetic import BallScene, render
from pisa_engine.tracking.segmenter import frame_time
from pisa_engine.tracking.windows import Window, event_windows, reference_windows

FPS = 60


def _plan(
    events: list[tuple[float, float]],
    *,
    phrase: str = "ball",
    references: Sequence[dict[str, Any]] = (),
    slow_motion: bool = False,
    measurable: bool = True,
) -> Plan:
    return Plan.model_validate(
        {
            "measurable": measurable,
            "reason": None if measurable else "no_free_flight",
            "events": [
                {"type": "throw", "start_s": a, "end_s": b, "object_phrases": [phrase]}
                for a, b in events
            ],
            "references": list(references),
            "camera": {
                "motion": "static",
                "has_cuts": False,
                "slow_motion_suspected": slow_motion,
            },
        }
    )


class StaticPlanner:
    def __init__(self, plan: Plan) -> None:
        self._plan = plan

    async def plan(self, video: Path, ingest: IngestResult, *, policy: DataPolicy) -> Plan:
        return checked(self._plan, ingest)


class ScriptedSegmenter:
    """Returns a prepared whole-clip track, cut to the frames of the clip it is given."""

    def __init__(self, t: np.ndarray, x: np.ndarray, y: np.ndarray) -> None:
        self._rows = np.column_stack([t, x, y])
        self.calls: list[tuple[str, Timebase]] = []

    async def track(
        self, video: Path, phrase: str, timebase: Timebase, *, policy: DataPolicy
    ) -> list[TrackedObject]:
        self.calls.append((phrase, timebase))
        first = round(timebase.start_s * timebase.fps_num / timebase.fps_den)
        samples = []
        for frame in range(timebase.frame_count):
            _, x, y = self._rows[first + frame]
            samples.append(
                TrackSample(
                    frame=frame,
                    t_s=frame_time(timebase, frame),
                    bbox=BBox(x1=x - 14, y1=y - 14, x2=x + 14, y2=y + 14),
                    centroid=Point2(x=float(x), y=float(y)),
                    area_px=616.0,
                    confidence=0.9,
                )
            )
        return [TrackedObject(phrase=phrase, object_id=0, samples=samples)]


class RecordingExplainer:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.seen: list[Verdict] = []

    async def explain(
        self,
        verdict: Verdict,
        results: Sequence[contracts.TestResult],
        plan: Plan,
        *,
        locale: Locale,
        policy: DataPolicy,
    ) -> Explanation | None:
        self.seen.append(verdict)
        if self.fail:
            raise RuntimeError("simulated explainer outage")
        return Explanation(locale=locale, text="Explained.", model="test")


def _analyze(clip: Path, tmp_path: Path, **components: Any) -> dict[str, Any]:
    settings = Settings(_env_file=None, PISA_DATA_DIR=str(tmp_path / "data"))
    client = TestClient(create_app(settings, **components))
    with clip.open("rb") as video:
        created = client.post("/jobs", files={"video": ("clip.mp4", video, "video/mp4")})
    job = client.get(f"/jobs/{created.json()['id']}").json()
    assert job["status"] == "done", job
    result: dict[str, Any] = client.get(f"/jobs/{created.json()['id']}/result").json()
    return result


def _toss() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """A hand pushes the ball up for 0.3 s, lets go, and it flies freely for 0.7 s."""
    t = np.arange(60) / FPS
    release, push = 0.3, 3000.0  # px/s^2 upward
    hand = 600 - 0.5 * push * t**2
    tau = t - release
    v0, y0 = -push * release, 600 - 0.5 * push * release**2
    flight = y0 + v0 * tau + 0.5 * 9.81 * 400 * tau**2
    return t, 320 + 100 * t, np.where(t < release, hand, flight)


@pytest.fixture(scope="module")
def clip_1s(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("clips") / "one_second.mp4"
    render(BallScene(duration_s=1.0), path)
    return path


def test_without_a_window_the_hand_makes_a_real_toss_look_impossible(
    clip_1s: Path, tmp_path: Path
) -> None:
    """Why the planner's windows matter: the push before release is not free fall."""
    plan = _plan([(0.0, 1.0)])
    result = _analyze(
        clip_1s, tmp_path, planner=StaticPlanner(plan), segmenter=ScriptedSegmenter(*_toss())
    )
    assert result["verdict"]["label"] == "physically_impossible"


def test_the_planners_window_keeps_the_hand_out(clip_1s: Path, tmp_path: Path) -> None:
    segmenter = ScriptedSegmenter(*_toss())
    result = _analyze(
        clip_1s, tmp_path, planner=StaticPlanner(_plan([(0.32, 1.0)])), segmenter=segmenter
    )
    assert result["verdict"]["label"] == "consistent_with_real_physics"
    # Only the window's frames went to the segmenter (SAM bills per frame), in a trimmed clip.
    ((phrase, timebase),) = segmenter.calls
    assert phrase == "ball"
    assert timebase.start_s == pytest.approx(19 / FPS)
    assert timebase.frame_count == 60 - 19
    samples = result["tracks"]["objects"][0]["samples"]
    assert samples[0]["frame"] == 20  # Frame numbers are back in the whole clip's terms.
    assert samples[0]["t_s"] == pytest.approx(20 / FPS)


def test_an_unmeasurable_plan_tracks_nothing_and_says_why(clip_1s: Path, tmp_path: Path) -> None:
    segmenter = ScriptedSegmenter(*_toss())
    result = _analyze(
        clip_1s,
        tmp_path,
        planner=StaticPlanner(_plan([], measurable=False)),
        segmenter=segmenter,
    )
    assert segmenter.calls == []
    assert result["tracks"] is None
    assert result["verdict"]["label"] == "inconclusive"
    assert result["verdict"]["reason_code"] == "no_free_flight"
    assert result["plan"]["measurable"] is False


BALL = {"phrase": "ball", "dimension": "diameter", "size_min_m": 0.065, "size_max_m": 0.075}


@pytest.fixture(scope="module")
def falls(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    folder = tmp_path_factory.mktemp("falls")
    paths = {}
    for name, g in (("earth", 9.81), ("moon", 1.62)):
        paths[name] = folder / f"{name}.mp4"
        render(BallScene(g_mps2=g, hold_s=0.1, duration_s=0.7, vx_mps=0.8), paths[name])
    return paths


def _implied_g(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [t for t in result["tests"] if t["test"] == "implied_g"]


def test_a_known_size_gives_gravity_in_meters(falls: dict[str, Path], tmp_path: Path) -> None:
    plan = _plan([(0.0, 0.7)], references=[BALL])
    result = _analyze(falls["earth"], tmp_path, planner=StaticPlanner(plan))
    (t4,) = _implied_g(result)
    g = next(m for m in t4["measurements"] if m["name"] == "implied_g")
    assert t4["outcome"] == "pass"
    assert g["ci_low"] < 9.81 < g["ci_high"]
    assert result["verdict"]["label"] == "consistent_with_real_physics"


def test_moon_gravity_is_flagged_but_never_convicts_alone(
    falls: dict[str, Path], tmp_path: Path
) -> None:
    plan = _plan([(0.0, 0.7)], references=[BALL])
    result = _analyze(falls["moon"], tmp_path, planner=StaticPlanner(plan))
    (t4,) = _implied_g(result)
    assert (t4["outcome"], t4["reason_code"]) == ("violation", "gravity_too_weak")
    g = next(m for m in t4["measurements"] if m["name"] == "implied_g")
    assert g["value"] == pytest.approx(1.62, rel=0.1)
    # A real slow-motion clip looks exactly like this, so the answer stays open.
    assert (result["verdict"]["label"], result["verdict"]["reason_code"]) == (
        "inconclusive",
        "weak_violation",
    )


def test_suspected_slow_motion_sets_implied_gravity_aside(
    falls: dict[str, Path], tmp_path: Path
) -> None:
    plan = _plan([(0.0, 0.7)], references=[BALL], slow_motion=True)
    result = _analyze(falls["moon"], tmp_path, planner=StaticPlanner(plan))
    (t4,) = _implied_g(result)
    assert (t4["outcome"], t4["reason_code"]) == ("not_applicable", "slow_motion")
    assert result["verdict"]["label"] == "consistent_with_real_physics"


def test_the_explanation_is_saved_and_its_failure_never_fails_the_job(
    falls: dict[str, Path], tmp_path: Path
) -> None:
    explained = _analyze(falls["earth"], tmp_path / "a", explainer=RecordingExplainer())
    assert explained["explanation"] == {"locale": "en", "text": "Explained.", "model": "test"}
    assert explained["costs"] == []  # Nothing paid was called.
    failed = _analyze(falls["earth"], tmp_path / "b", explainer=RecordingExplainer(fail=True))
    assert failed["explanation"] is None
    assert failed["verdict"]["label"] == "consistent_with_real_physics"


# Building blocks


def test_event_windows_merge_per_phrase_and_references_get_the_first_window() -> None:
    plan = _plan([(0.5, 1.0), (0.8, 1.4), (2.0, 2.5)], references=[{**BALL, "phrase": "door"}])
    events = event_windows(plan)
    assert events == {"ball": [Window(0.5, 1.4), Window(2.0, 2.5)]}
    assert reference_windows(plan, events) == {"door": [Window(0.5, 1.4)]}


def test_trimmed_frames_are_the_same_frames(clip_1s: Path, tmp_path: Path) -> None:
    ingest = normalize(clip_1s, tmp_path / "normalized.mp4")
    timebase = trim_frames(tmp_path / "normalized.mp4", ingest.timebase, 20, 25, tmp_path / "t.mp4")
    assert timebase.frame_count == 25
    assert timebase.start_s == pytest.approx(20 / FPS)

    def frame(path: Path, index: int) -> np.ndarray:
        capture = cv2.VideoCapture(str(path))
        capture.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, image = capture.read()
        capture.release()
        assert ok
        return np.asarray(image, dtype=np.float64)

    # The ball is where it was in the source frame, up to re-encoding noise.
    difference = np.abs(frame(tmp_path / "t.mp4", 0) - frame(tmp_path / "normalized.mp4", 20))
    assert difference.mean() < 1.0


def _box_samples(widths: list[float], heights: list[float]) -> list[TrackSample]:
    return [
        TrackSample(
            frame=i,
            t_s=i / FPS,
            bbox=BBox(x1=0, y1=0, x2=w, y2=h),
            centroid=Point2(x=w / 2, y=h / 2),
            area_px=w * h,
            confidence=None,
        )
        for i, (w, h) in enumerate(zip(widths, heights, strict=True))
    ]


def test_a_blurred_ball_is_measured_across_its_motion() -> None:
    # Falling fast, the ball smears vertically; its width stays the diameter.
    samples = _box_samples([28, 28, 29, 28, 28, 28], [28, 34, 45, 60, 80, 95])
    assert pixel_size(samples, "diameter") == pytest.approx(28.0)


def test_the_tightest_reference_wins() -> None:
    samples = {"ball": _box_samples([28] * 6, [28] * 6), "door": _box_samples([90] * 6, [800] * 6)}
    references = [
        ReferenceObject(phrase="door", dimension="height", size_min_m=1.9, size_max_m=2.4),
        ReferenceObject(phrase="ball", dimension="diameter", size_min_m=0.065, size_max_m=0.069),
    ]
    scale = best_scale(references, samples)
    assert scale is not None
    assert (scale.low_px_per_m, scale.high_px_per_m) == pytest.approx((28 / 0.069, 28 / 0.065))
