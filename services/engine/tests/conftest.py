from __future__ import annotations

import socket
from typing import Any

import pytest

_LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def _no_paid_api_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests never see a real key or an enabled kill switch from the developer's shell."""
    for name in ("MODEL_API_KEY", "PISA_PAID_CALLS_ENABLED", "PISA_SPEND_CAP_USD"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail any test that tries to reach a non-local host. HTTP tests use httpx.MockTransport."""
    real_connect = socket.socket.connect

    def guarded_connect(self: socket.socket, address: Any) -> None:
        if isinstance(address, tuple) and address[0] not in _LOCAL_HOSTS:
            raise RuntimeError(f"Tests must not open network connections (tried {address!r}).")
        real_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
