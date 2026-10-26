from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pisa_contracts import VideoProbe
from pisa_engine.ingest import normalize as normalize_module
from pisa_engine.ingest.normalize import IngestError, TimeWindow, normalize
from pisa_engine.ingest.probe import parse_probe, probe


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)  # noqa: S603, S607


@pytest.fixture(scope="module")
def test_clip(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """2 s of ffmpeg's test pattern at 30 fps, 320x240, with an audio track."""
    path = tmp_path_factory.mktemp("clips") / "testsrc.mp4"
    _ffmpeg(
        "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=30:duration=2",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path),
    )  # fmt: skip
    return path


def test_probe_reads_size_rate_and_frame_count(test_clip: Path) -> None:
    info = probe(test_clip, count_frames=True)
    assert (info.width, info.height) == (320, 240)
    assert (info.fps_num, info.fps_den) == (30, 1)
    assert info.frame_count == 60
    assert info.has_audio is True
    assert info.is_vfr is False
    assert info.rotation_deg == 0


def test_normalize_trims_to_window_with_exact_timebase(test_clip: Path, tmp_path: Path) -> None:
    result = normalize(test_clip, tmp_path / "out.mp4", window=TimeWindow(0.5, 1.5))
    assert result.normalized.codec == "h264"
    assert result.normalized.has_audio is False
    assert (result.timebase.fps_num, result.timebase.fps_den) == (30, 1)
    assert result.timebase.start_s == 0.5
    assert result.timebase.frame_count == 30


def test_normalize_applies_rotation(test_clip: Path, tmp_path: Path) -> None:
    rotated = tmp_path / "rotated.mp4"
    _ffmpeg("-display_rotation", "90", "-i", str(test_clip), "-c", "copy", str(rotated))
    assert probe(rotated).rotation_deg in (90, 270)
    assert (probe(rotated).width, probe(rotated).height) == (240, 320)

    result = normalize(rotated, tmp_path / "upright.mp4")
    assert (result.normalized.width, result.normalized.height) == (240, 320)
    assert result.normalized.rotation_deg == 0


def test_videos_over_a_minute_are_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    long_probe = VideoProbe(
        width=320, height=240, duration_s=61.0, fps_num=30, fps_den=1, is_vfr=False,
        rotation_deg=0, frame_count=None, codec="h264", has_audio=False, size_bytes=1,
    )  # fmt: skip
    monkeypatch.setattr(normalize_module, "probe", lambda *_args, **_kwargs: long_probe)
    with pytest.raises(IngestError) as error:
        normalize(tmp_path / "in.mp4", tmp_path / "out.mp4")
    assert error.value.code == "video_too_long"


def test_parse_probe_flags_variable_frame_rate() -> None:
    report = {
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "hevc",
                "width": 1920,
                "height": 1080,
                "avg_frame_rate": "5994/100",
                "r_frame_rate": "120/1",
                "side_data_list": [{"rotation": -90}],
            }
        ],
        "format": {"duration": "4.2", "size": "1000"},
    }
    info = parse_probe(report)
    assert info.is_vfr is True
    assert info.rotation_deg == 270
    assert (info.width, info.height) == (1080, 1920)
    assert (info.fps_num, info.fps_den) == (2997, 50)


@pytest.mark.parametrize(
    "content",
    [
        "ffconcat version 1.0\nfile '/etc/passwd'\n",
        "#EXTM3U\n#EXT-X-TARGETDURATION:1\n#EXTINF:1,\nhttp://127.0.0.1:9/segment.ts\n",
    ],
    ids=["concat-script", "hls-playlist"],
)
def test_disguised_scripts_are_rejected_not_followed(content: str, tmp_path: Path) -> None:
    disguised = tmp_path / "video.mp4"
    disguised.write_text(content)
    with pytest.raises(IngestError) as error:
        normalize(disguised, tmp_path / "out.mp4")
    assert error.value.code == "unsupported_format"
    assert not (tmp_path / "out.mp4").exists()


def test_videos_without_a_duration_are_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    no_duration = VideoProbe(
        width=320, height=240, duration_s=0.0, fps_num=30, fps_den=1, is_vfr=False,
        rotation_deg=0, frame_count=None, codec="h264", has_audio=False, size_bytes=1,
    )  # fmt: skip
    monkeypatch.setattr(normalize_module, "probe", lambda *_args, **_kwargs: no_duration)
    with pytest.raises(IngestError) as error:
        normalize(tmp_path / "in.mp4", tmp_path / "out.mp4")
    assert error.value.code == "unknown_duration"
