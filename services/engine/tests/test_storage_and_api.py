"""Storage, the job pipeline and the HTTP API, end to end on synthetic clips. No network."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from pisa_engine import __version__
from pisa_engine.api import create_app
from pisa_engine.settings import Settings
from pisa_engine.storage import LocalStorage
from pisa_engine.synthetic import BallScene, MotionProfile, render


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(_env_file=None, PISA_DATA_DIR=str(tmp_path / "data"))


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))


@pytest.fixture(scope="module")
def clips(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    folder = tmp_path_factory.mktemp("clips")
    profiles: tuple[MotionProfile, ...] = ("free_fall", "eased", "constant_velocity")
    paths: dict[str, Path] = {}
    for profile in profiles:
        paths[profile] = folder / f"{profile}.mp4"
        render(BallScene(profile=profile, hold_s=0.15, duration_s=0.75, vx_mps=0.8), paths[profile])
    return paths


def _upload(client: TestClient, clip: Path, locale: str = "es") -> dict[str, object]:
    with clip.open("rb") as video:
        response = client.post(
            "/jobs", files={"video": ("clip.mp4", video, "video/mp4")}, data={"locale": locale}
        )
    assert response.status_code == 202, response.text
    body: dict[str, object] = response.json()
    return body


def test_healthz(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


@pytest.mark.parametrize(
    ("profile", "label"),
    [
        ("free_fall", "consistent_with_real_physics"),
        ("eased", "physically_impossible"),
        ("constant_velocity", "inconclusive"),
    ],
)
def test_upload_runs_the_pipeline_to_a_verdict(
    client: TestClient, clips: dict[str, Path], profile: str, label: str
) -> None:
    created = _upload(client, clips[profile])
    assert created["status"] == "queued"
    assert created["locale"] == "es"
    assert created["data_policy"] == "user"

    # TestClient runs background tasks before returning, so the job is already finished.
    job = client.get(f"/jobs/{created['id']}").json()
    assert (job["status"], job["stage"], job["error"]) == ("done", "verdict", None)

    result = client.get(f"/jobs/{created['id']}/result").json()
    assert result["verdict"]["label"] == label
    assert result["ingest"]["timebase"]["fps_num"] == 60
    assert result["tracks"]["objects"][0]["samples"]


def test_a_file_that_is_not_a_video_fails_with_a_clear_code(
    client: TestClient, tmp_path: Path
) -> None:
    fake = tmp_path / "notes.mp4"
    fake.write_text("not a video")
    created = _upload(client, fake)
    job = client.get(f"/jobs/{created['id']}").json()
    assert job["status"] == "failed"
    assert job["error"] == {"code": "unsupported_format", "stage": "ingest"}
    assert client.get(f"/jobs/{created['id']}/result").status_code == 404


def test_uploads_over_the_limit_are_refused(settings: Settings, clips: dict[str, Path]) -> None:
    small = settings.model_copy(update={"max_upload_bytes": 1000})
    client = TestClient(create_app(small))
    with clips["free_fall"].open("rb") as video:
        response = client.post("/jobs", files={"video": ("clip.mp4", video, "video/mp4")})
    assert response.status_code == 413
    assert response.json() == {"error": {"code": "file_too_large", "stage": None}}


def test_sam_jobs_stop_at_the_kill_switch(settings: Settings, clips: dict[str, Path]) -> None:
    sam = settings.model_copy(update={"segmenter": "sam"})
    client = TestClient(create_app(sam))
    created = _upload(client, clips["free_fall"])
    job = client.get(f"/jobs/{created['id']}").json()
    assert job["error"] == {"code": "paid_calls_disabled", "stage": "track"}


def test_bodies_over_the_limit_are_cut_off_while_they_arrive(settings: Settings) -> None:
    client = TestClient(create_app(settings.model_copy(update={"max_upload_bytes": 1000})))
    declared = client.post("/jobs", content=b"x" * 200_000, headers={"content-type": "video/mp4"})
    assert declared.status_code == 413

    def chunks() -> Iterator[bytes]:  # Chunked: no Content-Length to check up front.
        for _ in range(100):
            yield b"x" * 4096

    form = {"content-type": "multipart/form-data; boundary=pisa"}
    streamed = client.post("/jobs", content=chunks(), headers=form)
    assert streamed.status_code == 413
    assert streamed.json()["error"]["code"] == "file_too_large"


def test_jobs_are_rate_limited_per_client(settings: Settings, clips: dict[str, Path]) -> None:
    client = TestClient(create_app(settings.model_copy(update={"jobs_per_hour": 2})))
    for _ in range(2):
        _upload(client, clips["free_fall"])
    with clips["free_fall"].open("rb") as video:
        response = client.post("/jobs", files={"video": ("clip.mp4", video, "video/mp4")})
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"


def test_engine_token_is_required_when_configured(
    settings: Settings, clips: dict[str, Path]
) -> None:
    token = SecretStr("s3cret-engine-token")
    client = TestClient(create_app(settings.model_copy(update={"engine_token": token})))
    with clips["free_fall"].open("rb") as video:
        refused = client.post("/jobs", files={"video": ("clip.mp4", video, "video/mp4")})
    assert refused.status_code == 401
    with clips["free_fall"].open("rb") as video:
        accepted = client.post(
            "/jobs",
            files={"video": ("clip.mp4", video, "video/mp4")},
            headers={"Authorization": "Bearer s3cret-engine-token"},
        )
    assert accepted.status_code == 202
    # Every route but the health check needs the token, so path variants cannot slip past.
    assert client.get(f"/jobs/{accepted.json()['id']}").status_code == 401
    assert client.post("/jobs/", content=b"").status_code == 401
    assert client.get("/healthz").status_code == 200


def test_unknown_jobs_and_locales(client: TestClient, clips: dict[str, Path]) -> None:
    missing = client.get("/jobs/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "job_not_found"
    with clips["free_fall"].open("rb") as video:
        response = client.post(
            "/jobs", files={"video": ("clip.mp4", video, "video/mp4")}, data={"locale": "fr"}
        )
    assert response.status_code == 422


def test_local_storage_round_trip(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    storage.put_bytes("jobs/abc/plan.json", b"{}")
    assert storage.exists("jobs/abc/plan.json")
    assert storage.get_bytes("jobs/abc/plan.json") == b"{}"


@pytest.mark.parametrize("key", ["../escape.json", "/etc/passwd", "jobs/../../x"])
def test_local_storage_rejects_keys_outside_its_root(tmp_path: Path, key: str) -> None:
    with pytest.raises(ValueError, match="relative paths"):
        LocalStorage(tmp_path).put_bytes(key, b"")
