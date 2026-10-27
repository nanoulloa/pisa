from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

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
    SupabaseSpendLedger,
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
    assert JsonlSpendLedger(path).spent_usd() == pytest.approx(0.75)
    assert JsonlSpendLedger(tmp_path / "missing.jsonl").spent_usd() == 0.0


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


class FakeSpendRpc:
    """The Supabase functions over HTTP, enough to check the requests and the guard on top."""

    def __init__(self, *, spent: float = 0.0, fail_settle: bool = False) -> None:
        self.requests: list[httpx.Request] = []
        self.holds: dict[str, float] = {}
        self.spent = spent
        self.fail_settle = fail_settle

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        function = request.url.path.rsplit("/", 1)[-1]
        args = json.loads(request.content or b"{}")
        if function == "spend_reserve":
            if self.spent + sum(self.holds.values()) + args["p_usd"] > args["p_cap_usd"]:
                return httpx.Response(200, content=b"null")
            hold = f"hold-{len(self.holds)}"
            self.holds[hold] = args["p_usd"]
            return httpx.Response(200, json=hold)
        if function == "spend_settle":
            if self.fail_settle:
                return httpx.Response(503, json={"message": "unavailable"})
            if self.holds.pop(args["p_hold"], None) is not None:
                self.spent += sum(entry["usd"] for entry in args["p_entries"])
            return httpx.Response(204)
        if function == "spend_release":
            self.holds.pop(args["p_hold"], None)
            return httpx.Response(204)
        if function == "spend_committed_usd":
            return httpx.Response(200, json=self.spent + sum(self.holds.values()))
        return httpx.Response(200, json=self.spent)


def _supabase_guard(rpc: FakeSpendRpc, cap_usd: float = 1.0) -> SpendGuard:
    ledger = SupabaseSpendLedger(
        "https://project.supabase.co",
        SecretStr("sb_secret_not-a-real-key"),
        transport=httpx.MockTransport(rpc),
    )
    return SpendGuard(enabled=True, cap_usd=cap_usd, ledger=ledger)


def test_the_supabase_ledger_holds_through_the_database() -> None:
    rpc = FakeSpendRpc(spent=0.4)
    guard = _supabase_guard(rpc)
    reservation = guard.reserve(0.5)

    reserve = rpc.requests[0]
    assert reserve.url.path == "/rest/v1/rpc/spend_reserve"
    assert json.loads(reserve.content) == {"p_usd": 0.5, "p_cap_usd": 1.0}
    assert reserve.headers["apikey"] == "sb_secret_not-a-real-key"
    with pytest.raises(SpendCapExceededError, match=r"\$0\.9000 already spent"):
        guard.reserve(0.2)  # Another container's hold counts the same as this one's.

    guard.settle(reservation, [_entry(0.3)])
    settle = json.loads(rpc.requests[-1].content)
    assert settle["p_hold"] == "hold-0"
    assert settle["p_entries"][0]["usd"] == 0.3
    assert guard.spent_usd() == pytest.approx(0.7)


def test_a_settle_the_database_misses_stays_held_at_the_worst_case() -> None:
    """The call already happened: its job goes on, and the hold keeps the budget honest."""
    rpc = FakeSpendRpc(fail_settle=True)
    guard = _supabase_guard(rpc)
    guard.settle(guard.reserve(0.5), [_entry(0.1)])
    assert rpc.holds == {"hold-0": 0.5}
