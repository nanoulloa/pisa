from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pisa_engine import __version__
from pisa_engine.api import app
from pisa_engine.storage import LocalStorage


def test_healthz() -> None:
    response = TestClient(app).get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_local_storage_round_trip(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    storage.put_bytes("jobs/abc/plan.json", b"{}")
    assert storage.exists("jobs/abc/plan.json")
    assert storage.get_bytes("jobs/abc/plan.json") == b"{}"


@pytest.mark.parametrize("key", ["../escape.json", "/etc/passwd", "jobs/../../x"])
def test_local_storage_rejects_keys_outside_its_root(tmp_path: Path, key: str) -> None:
    with pytest.raises(ValueError, match="relative paths"):
        LocalStorage(tmp_path).put_bytes(key, b"")
