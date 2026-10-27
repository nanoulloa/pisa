"""The eval: runs are saved and resumable, scores are honest, calibration protects real videos."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

import pisa_contracts as contracts
from pisa_contracts import (
    DataPolicy,
    EvalTruth,
    IngestResult,
    Plan,
    TestOutcome,
    Timebase,
    Verdict,
    VideoProbe,
)
from pisa_engine.evaluation.baseline import (
    QUESTION,
    MuseSparkBaseline,
    Opinion,
    load_baseline,
    run_baseline,
)
from pisa_engine.evaluation.calibration import calibrate
from pisa_engine.evaluation.manifest import Clip, Manifest
from pisa_engine.evaluation.markdown import calibration_markdown, report_markdown
from pisa_engine.evaluation.runner import RunInfo, RunStoppedError, load_runs, run_manifest
from pisa_engine.evaluation.scoring import Outcome, outcomes, rate, score, summary
from pisa_engine.model_api import costs
from pisa_engine.model_api.client import MetaModelApiClient
from pisa_engine.model_api.responses import ModelOutputError
from pisa_engine.model_api.spend import InMemorySpendLedger, PaidCallsDisabledError, SpendGuard
from pisa_engine.physics.results import result
from pisa_engine.planning.planner import WholeClipPlanner
from pisa_engine.render.store import LocalEvidenceStore
from pisa_engine.synthetic import BallScene, render
from pisa_engine.tracking.fake import ColorSegmenter
from pisa_engine.verdict import POLICY_VERSION, PolicyConfig

pytestmark = pytest.mark.anyio

NOW = datetime(2026, 10, 27, tzinfo=UTC)


def _info(segmenter: str = "color-offline") -> RunInfo:
    return RunInfo(
        manifest="eval/test.json",
        segmenter=segmenter,
        planner="whole-clip",
        data_policy="user",
        started_at=NOW,
    )


@pytest.fixture(scope="module")
def eval_set(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Manifest]:
    folder = tmp_path_factory.mktemp("eval")
    scenes = {
        "drop": BallScene(hold_s=0.1, duration_s=0.7, position_noise_px=1.0),
        "eased": BallScene(profile="eased", hold_s=0.1, duration_s=0.7, position_noise_px=1.0),
        "empty": BallScene(radius_px=0.0, duration_s=0.5),  # Nothing to track.
    }
    for name, scene in scenes.items():
        render(scene, folder / f"{name}.mp4")
    manifest = Manifest(
        name="test",
        clips=[
            Clip(id="drop", file="drop.mp4", truth="real", tags=["drop"]),
            Clip(id="eased", file="eased.mp4", truth="generated", tags=["drop"]),
            Clip(id="empty", file="empty.mp4", truth="real", tags=["empty"]),
        ],
    )
    path = folder / "manifest.json"
    path.write_text(manifest.model_dump_json(), encoding="utf-8")
    return path, manifest


async def _run(
    path: Path, manifest: Manifest, out: Path, *, segmenter: str = "color-offline"
) -> list[str]:
    seen: list[str] = []
    await run_manifest(
        path,
        manifest,
        out,
        _info(segmenter),
        segmenter=ColorSegmenter(),
        planner=WholeClipPlanner("ball"),
        evidence=LocalEvidenceStore(out / "evidence"),
        progress=seen.append,
    )
    return seen


# Running


async def test_a_run_is_saved_scored_and_resumed(
    eval_set: tuple[Path, Manifest], tmp_path: Path
) -> None:
    path, manifest = eval_set
    out = tmp_path / "run"
    assert len(await _run(path, manifest, out)) == 3

    info, runs = load_runs(out)
    report = score(manifest, runs, info, name="test", created_at=NOW)
    assert [c.verdict for c in report.clips] == [
        "consistent_with_real_physics",
        "physically_impossible",
        "inconclusive",
    ]
    assert (report.false_positive_rate.count, report.false_positive_rate.total) == (0, 2)
    assert (report.detection_rate.count, report.detection_rate.total) == (1, 1)
    t1 = next(t for t in report.tests if t.test == "free_fall_shape")
    assert (t1.decisive.real, t1.decisive.generated) == (0, 1)
    assert report.cost_usd == 0
    assert "0 of 2" in report_markdown(report)

    # Clips already run are not run again, and a run never mixes two setups.
    assert await _run(path, manifest, out) == []
    with pytest.raises(ValueError, match="another setup"):
        await _run(path, manifest, out, segmenter="sam-3.1")


async def test_a_run_stops_at_the_paid_calls_switch(
    eval_set: tuple[Path, Manifest], tmp_path: Path
) -> None:
    class SwitchedOff:
        async def plan(self, video: Path, ingest: IngestResult, *, policy: DataPolicy) -> Plan:
            raise PaidCallsDisabledError

    path, manifest = eval_set
    out = tmp_path / "run"
    with pytest.raises(RunStoppedError, match="paid_calls_disabled"):
        await run_manifest(
            path,
            manifest,
            out,
            _info(),
            segmenter=ColorSegmenter(),
            planner=SwitchedOff(),
            evidence=LocalEvidenceStore(out / "evidence"),
            progress=lambda _: None,
        )
    assert not list((out / "results").glob("*.json"))  # So a rerun retries them.


async def test_missing_clips_stop_the_run_before_it_starts(tmp_path: Path) -> None:
    manifest = Manifest(name="x", clips=[Clip(id="gone", file="gone.mp4", truth="real")])
    with pytest.raises(FileNotFoundError, match=r"gone\.mp4"):
        await _run(tmp_path / "manifest.json", manifest, tmp_path / "run")


def test_manifests_reject_repeated_ids_and_unknown_first_frames() -> None:
    clip = {"id": "a", "file": "a.mp4", "truth": "real"}
    with pytest.raises(ValueError, match="repeated"):
        Manifest.model_validate({"name": "x", "clips": [clip, clip]})
    generated = {"id": "b", "file": "b.mp4", "truth": "generated", "first_frame_of": "zzz"}
    with pytest.raises(ValueError, match="first_frame_of"):
        Manifest.model_validate({"name": "x", "clips": [clip, generated]})


# Scoring


def test_rates_carry_wilson_intervals() -> None:
    none_in_ten = rate(0, 10)
    assert none_in_ten.value == 0
    assert none_in_ten.ci_low == 0
    assert none_in_ten.ci_high == pytest.approx(0.2775, abs=1e-4)
    half = rate(5, 10)
    assert (half.ci_low, half.ci_high) == pytest.approx((0.2366, 0.7634), abs=1e-4)
    assert rate(0, 0).value is None


def test_summaries() -> None:
    values = summary([4.0, 1.0, 3.0, 2.0])
    assert (values.median, values.p90, values.max) == (2.5, 4.0, 4.0)
    assert summary([]).median is None


# Calibration


def _outcome(clip_id: str, truth: EvalTruth, *tests: contracts.TestResult) -> Outcome:
    clip = Clip(id=clip_id, file=f"{clip_id}.mp4", truth=truth)
    verdict = Verdict(
        label="inconclusive", policy_version=POLICY_VERSION, decisive_tests=[], reason_code=None
    )
    return Outcome(clip, verdict, list(tests), 1.0, 0.0)


def _t1(outcome: TestOutcome, confidence: float) -> contracts.TestResult:
    return result("free_fall_shape", outcome, confidence, [], None)


def test_calibration_raises_a_threshold_until_real_clips_are_safe() -> None:
    found = [
        _outcome("real-1", "real", _t1("violation", 0.92)),
        _outcome("real-2", "real", _t1("pass", 0.8)),
        _outcome("gen-1", "generated", _t1("violation", 0.97)),
        _outcome("gen-2", "generated", _t1("violation", 0.85)),
    ]
    calibration = calibrate(found)
    assert (calibration.current_score.false_positives, calibration.current_score.detections) == (
        1,
        1,
    )
    assert calibration.recommended.threshold("free_fall_shape") == 0.95
    assert calibration.recommended.threshold("galileo_pair") == 0.9  # No evidence, no change.
    score_after = calibration.recommended_score
    assert (score_after.false_positives, score_after.detections) == (0, 1)
    assert "0.95" in calibration_markdown("test", calibration)


def test_calibration_says_when_no_threshold_is_safe() -> None:
    found = [_outcome("real", "real", _t1("violation", 0.995))]
    calibration = calibrate(found)
    assert not calibration.feasible
    assert "need attention" in calibration_markdown("test", calibration)


async def test_scores_can_be_recomputed_under_another_policy(
    eval_set: tuple[Path, Manifest], tmp_path: Path
) -> None:
    """Decisions come from saved test results, so no model runs again to try a policy."""
    path, manifest = eval_set
    out = tmp_path / "run"
    await _run(path, manifest, out)
    _, runs = load_runs(out)
    without_t1 = PolicyConfig(
        convicting_tests=frozenset({"galileo_pair", "bounce_energy", "time_base_consistency"})
    )
    labels = [o.verdict.label for o in outcomes(manifest, runs, without_t1)]
    assert labels[1] == "inconclusive"  # The eased drop is no longer convicted.


# Baseline: Muse Spark's opinion on the same clips


def _ingest() -> IngestResult:
    probe = VideoProbe(
        width=640,
        height=960,
        duration_s=2.0,
        fps_num=60,
        fps_den=1,
        is_vfr=False,
        rotation_deg=0,
        frame_count=120,
        codec="h264",
        has_audio=False,
        size_bytes=10_000,
    )
    timebase = Timebase(fps_num=60, fps_den=1, start_s=0.0, frame_count=120)
    return IngestResult(source=probe, normalized=probe, timebase=timebase, scene_cuts_s=[])


async def test_muse_spark_is_asked_plainly_and_answers_in_a_scorable_shape(
    tmp_path: Path,
) -> None:
    requests: list[httpx.Request] = []

    def api(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "DELETE":
            return httpx.Response(200, json={"id": "file-7", "deleted": True})
        if request.url.path.endswith("/files"):
            return httpx.Response(200, json={"id": "file-7", "expires_at": 1793050000})
        if request.url.path.endswith("/input_tokens"):
            return httpx.Response(200, json={"input_tokens": 9000})
        text = json.dumps({"answer": "real", "reason": "The lighting looks natural."})
        return httpx.Response(
            200,
            json={
                "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}],
                "usage": {"input_tokens": 9000, "output_tokens": 300},
            },
        )

    client = MetaModelApiClient(
        api_key=SecretStr("LLM_000_not-a-real-key"),
        base_url="https://api.meta.ai/v1",
        guard=SpendGuard(enabled=True, cap_usd=1.0, ledger=InMemorySpendLedger()),
        transport=httpx.MockTransport(api),
    )
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"\x00")
    baseline = MuseSparkBaseline(client)
    with costs.collecting() as spent:
        opinion = await baseline.ask(video, _ingest(), policy="user")

    assert (opinion.answer, opinion.reason) == ("real", "The lighting looks natural.")
    _, count, create, delete = requests
    body = json.loads(create.content)
    assert json.loads(count.content) == body
    assert body["model"] == "muse-spark-1.3"
    question, clip = body["input"][0]["content"]
    assert question == {"type": "input_text", "text": QUESTION}
    assert clip == {"type": "input_video", "file_id": "file-7", "fps": 8.0}  # As the planner.
    assert "physic" not in (body["instructions"] + question["text"]).lower()  # No hints.
    assert body["text"]["format"]["name"] == "opinion"
    assert {e.stage for e in spent} == {"baseline"}
    assert (delete.method, delete.url.path) == ("DELETE", "/v1/files/file-7")
    assert baseline.model_for("internal") == "muse-spark-1.3-contributor"


class _ScriptedBaseline:
    """Gives the scripted answers in order; an exception in the script is raised instead."""

    def __init__(self, *script: str | Exception) -> None:
        self.script = list(script)
        self.asked = 0

    def model_for(self, policy: DataPolicy) -> str:
        return "muse-spark-1.3"

    async def ask(self, video: Path, ingest: IngestResult, *, policy: DataPolicy) -> Opinion:
        self.asked += 1
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        return Opinion.model_validate({"answer": step, "reason": "Because."})


async def test_baseline_answers_are_saved_scored_and_resumed(
    eval_set: tuple[Path, Manifest], tmp_path: Path
) -> None:
    path, manifest = eval_set
    out = tmp_path / "run"
    await _run(path, manifest, out)
    info, runs = load_runs(out)

    # drop (real), eased (generated), empty (real); the last call fails and counts as unsure.
    scripted = _ScriptedBaseline("generated", "generated", ModelOutputError("not JSON"))
    await run_baseline(path, manifest, out, scripted, policy="user", progress=lambda _: None)
    await run_baseline(path, manifest, out, scripted, policy="user", progress=lambda _: None)
    assert scripted.asked == 3  # The second run asked nothing again.

    report = score(manifest, runs, info, name="t", created_at=NOW, baseline=load_baseline(out))
    assert report.baseline is not None
    assert (
        report.baseline.false_positive_rate.count,
        report.baseline.false_positive_rate.total,
    ) == (
        1,
        2,
    )
    assert report.baseline.detection_rate.count == 1
    assert report.baseline.unsure_rate.count == 1
    assert [c.baseline for c in report.clips] == ["generated", "generated", "unsure"]
    assert "Compared with asking Muse Spark" in report_markdown(report)

    # An opinion on only some clips is not a comparison.
    partial = {k: v for k, v in load_baseline(out).items() if k != "empty"}
    assert score(manifest, runs, info, name="t", created_at=NOW, baseline=partial).baseline is None


async def test_the_baseline_stops_at_the_paid_calls_switch(
    eval_set: tuple[Path, Manifest], tmp_path: Path
) -> None:
    path, manifest = eval_set
    out = tmp_path / "run"
    with pytest.raises(RunStoppedError, match="paid_calls_disabled"):
        await run_baseline(
            path, manifest, out, _ScriptedBaseline(PaidCallsDisabledError()), policy="user"
        )
    assert load_baseline(out) == {}
