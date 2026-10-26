from __future__ import annotations

from pathlib import Path

import pytest

from pisa_contracts import CostEntry
from pisa_engine.limits import RateLimiter, client_key
from pisa_engine.model_api.policy import ContributorTierForbiddenError, ensure_model_allowed
from pisa_engine.model_api.pricing import UnknownPriceError, sam_cost_usd, token_cost_usd
from pisa_engine.model_api.spend import (
    InMemorySpendLedger,
    JsonlSpendLedger,
    PaidCallsDisabledError,
    SpendCapExceededError,
    SpendGuard,
)


def _entry(usd: float) -> CostEntry:
    return CostEntry(stage="track", model="sam-3.1", unit="frames", quantity=100, usd=usd)


def test_disabled_guard_refuses_everything() -> None:
    guard = SpendGuard(enabled=False, cap_usd=100.0, ledger=InMemorySpendLedger())
    with pytest.raises(PaidCallsDisabledError):
        guard.ensure_enabled()
    with pytest.raises(PaidCallsDisabledError):
        guard.reserve(0.0)


def test_guard_refuses_a_call_that_could_cross_the_cap() -> None:
    ledger = InMemorySpendLedger()
    guard = SpendGuard(enabled=True, cap_usd=1.0, ledger=ledger)
    guard.settle(guard.reserve(0.9), [_entry(0.9)])
    with pytest.raises(SpendCapExceededError):
        guard.reserve(0.2)
    guard.reserve(0.1)


def test_reservations_stop_concurrent_calls_from_jointly_crossing_the_cap() -> None:
    guard = SpendGuard(enabled=True, cap_usd=1.0, ledger=InMemorySpendLedger())
    first = guard.reserve(0.6)
    with pytest.raises(SpendCapExceededError):
        guard.reserve(0.6)  # The first call has not settled yet, but its cost is held.
    guard.release(first)
    second = guard.reserve(0.6)
    guard.settle(second, [_entry(0.5)])
    guard.release(second)  # Already settled: no double release.
    assert guard.spent_usd() == pytest.approx(0.5)
    guard.reserve(0.5)


def test_jsonl_ledger_survives_a_restart(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "spend.jsonl"
    JsonlSpendLedger(path).append([_entry(0.25), _entry(0.5)])
    assert JsonlSpendLedger(path).total_usd() == pytest.approx(0.75)
    assert JsonlSpendLedger(tmp_path / "missing.jsonl").total_usd() == 0.0


def test_contributor_tier_is_only_for_internal_clips() -> None:
    with pytest.raises(ContributorTierForbiddenError):
        ensure_model_allowed("muse-spark-1.3-contributor", "user")
    ensure_model_allowed("muse-spark-1.3-contributor", "internal")
    ensure_model_allowed("muse-spark-1.3", "user")


def test_prices() -> None:
    assert sam_cost_usd(10) == pytest.approx(50 * 0.20 / 1000)  # 50-frame minimum
    assert sam_cost_usd(300) == pytest.approx(0.06)
    assert token_cost_usd("muse-spark-1.3", 15, 175) == pytest.approx(0.000763, abs=1e-6)
    with pytest.raises(UnknownPriceError):
        token_cost_usd("some-new-model", 1, 1)


def test_rate_limiter_window_per_client_and_global_limit() -> None:
    now = [0.0]
    limiter = RateLimiter(2, window_s=60, global_limit=4, max_keys=5, clock=lambda: now[0])
    assert limiter.allow("a")
    assert limiter.allow("a")
    assert not limiter.allow("a")  # Per client.
    assert limiter.allow("b")
    assert limiter.allow("c")
    assert not limiter.allow("d")  # Global: 4 jobs already in the window.
    now[0] = 61
    assert limiter.allow("a")  # The window moved on.


def test_rotating_addresses_cannot_evict_an_active_client() -> None:
    now = [0.0]
    limiter = RateLimiter(1, window_s=60, global_limit=3, max_keys=4, clock=lambda: now[0])
    assert limiter.allow("victim-of-limit")
    for i in range(100):
        limiter.allow(f"rotating-{i}")
    assert not limiter.allow("victim-of-limit")  # Still remembered, still at its limit.
    assert len(limiter) <= 4


def test_rate_limiter_rejects_unsafe_sizes() -> None:
    with pytest.raises(ValueError, match="max_keys"):
        RateLimiter(1, window_s=60, global_limit=10, max_keys=10)


def test_ipv6_clients_are_grouped_by_their_64_prefix() -> None:
    assert client_key("2001:db8:1:2:aaaa::1") == client_key("2001:db8:1:2:bbbb::9")
    assert client_key("2001:db8:1:3::1") != client_key("2001:db8:1:2::1")
    assert client_key("203.0.113.7") == "203.0.113.7"


def test_logged_client_hashes_are_salted_and_never_show_the_address(
    caplog: pytest.LogCaptureFixture,
) -> None:
    import hashlib
    import logging

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from pisa_engine.limits import AdmissionMiddleware

    app = FastAPI()

    @app.post("/jobs")
    def jobs() -> dict[str, str]:
        return {}

    limiter = RateLimiter(5, window_s=60, global_limit=10, max_keys=20)
    app.add_middleware(AdmissionMiddleware, token="", limiter=limiter)
    with caplog.at_level(logging.INFO, logger="pisa_engine.limits"):
        TestClient(app, client=("203.0.113.9", 50000)).post("/jobs")
    (record,) = [r for r in caplog.records if r.getMessage().startswith("Job request")]
    unsalted = hashlib.sha256(b"203.0.113.9").hexdigest()[:12]
    assert record.client != unsalted  # type: ignore[attr-defined]
    assert "203.0.113.9" not in record.getMessage()
