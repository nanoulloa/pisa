"""Our own hard stop on paid API calls.

Meta's Billing "Spend limit" only sends email alerts, so the engine enforces the
budget itself: a kill switch, plus a persistent ledger checked before every call. When
Supabase is configured the ledger lives there, so every container and every local run
shares one budget.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

import httpx
from pydantic import SecretStr

from pisa_contracts import CostEntry

logger = logging.getLogger(__name__)


class PaidCallsDisabledError(RuntimeError):
    def __init__(self) -> None:
        super().__init__(
            "Paid API calls are disabled (PISA_PAID_CALLS_ENABLED is not true). "
            "No request was sent."
        )


class SpendCapExceededError(RuntimeError):
    def __init__(self, spent_usd: float, worst_case_usd: float, cap_usd: float) -> None:
        super().__init__(
            f"Refusing a call that could cost ${worst_case_usd:.4f}: ${spent_usd:.4f} already "
            f"spent of a ${cap_usd:.2f} cap (PISA_SPEND_CAP_USD)."
        )


class SpendLedger(Protocol):
    """Where spending is recorded, and where worst-case costs are held while calls run.

    Holding is atomic: two calls can never both be granted a hold that only one of them
    fits. Local ledgers guarantee that within one process; the Supabase ledger across every
    engine that shares the project.
    """

    def hold(self, usd: float, cap_usd: float) -> str | None:
        """Hold `usd` if what is spent and held stays within `cap_usd`. The hold's id, or None."""
        ...

    def settle(self, hold: str, entries: Sequence[CostEntry]) -> None:
        """Replace a hold with what the call cost. Ignored for a hold already closed."""
        ...

    def release(self, hold: str) -> None:
        """Drop a hold for a call that was never sent."""
        ...

    def spent_usd(self) -> float: ...

    def committed_usd(self) -> float:
        """Spent plus held."""
        ...


class _LocalHolds:
    """Holds kept in this process, for ledgers that only one process writes."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._holds: dict[str, float] = {}

    def hold(self, usd: float, cap_usd: float) -> str | None:
        with self._lock:
            if self.spent_usd() + sum(self._holds.values()) + usd > cap_usd:
                return None
            hold = uuid4().hex
            self._holds[hold] = usd
            return hold

    def settle(self, hold: str, entries: Sequence[CostEntry]) -> None:
        with self._lock:
            if self._holds.pop(hold, None) is not None:
                self.append(entries)

    def release(self, hold: str) -> None:
        with self._lock:
            self._holds.pop(hold, None)

    def committed_usd(self) -> float:
        with self._lock:
            return self.spent_usd() + sum(self._holds.values())

    def spent_usd(self) -> float:
        raise NotImplementedError

    def append(self, entries: Sequence[CostEntry]) -> None:
        raise NotImplementedError


class InMemorySpendLedger(_LocalHolds):
    def __init__(self) -> None:
        super().__init__()
        self.entries: list[CostEntry] = []

    def spent_usd(self) -> float:
        return sum(entry.usd for entry in self.entries)

    def append(self, entries: Sequence[CostEntry]) -> None:
        self.entries.extend(entries)


class JsonlSpendLedger(_LocalHolds):
    """One `CostEntry` per line. Survives restarts; local to one machine."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self._path = path

    def spent_usd(self) -> float:
        if not self._path.exists():
            return 0.0
        with self._path.open(encoding="utf-8") as lines:
            return sum(CostEntry.model_validate_json(line).usd for line in lines if line.strip())

    def append(self, entries: Sequence[CostEntry]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as ledger:
            for entry in entries:
                ledger.write(entry.model_dump_json() + "\n")


class SupabaseSpendLedger:
    """The `spend_entries` and `spend_holds` tables (supabase/migrations), through functions
    that grant holds one at a time. Shared by every container, so the cap holds for all."""

    def __init__(
        self, url: str, secret_key: SecretStr, transport: httpx.BaseTransport | None = None
    ) -> None:
        key = secret_key.get_secret_value()
        headers = {"apikey": key}
        if key.startswith("eyJ"):  # Legacy service_role JWTs also go in Authorization.
            headers["Authorization"] = f"Bearer {key}"
        self._http = httpx.Client(
            base_url=url.rstrip("/") + "/rest/v1/rpc/",
            headers=headers,
            timeout=httpx.Timeout(10.0),
            transport=transport,
        )

    def hold(self, usd: float, cap_usd: float) -> str | None:
        hold = self._call("spend_reserve", {"p_usd": usd, "p_cap_usd": cap_usd})
        return str(hold) if hold else None

    def settle(self, hold: str, entries: Sequence[CostEntry]) -> None:
        """The call already happened. If its cost cannot be written, the hold stays in the
        ledger at the worst case, which is never less than what the call cost."""
        rows = [entry.model_dump(mode="json") for entry in entries]
        try:
            self._call("spend_settle", {"p_hold": hold, "p_entries": rows})
        except httpx.HTTPError:
            logger.warning("Could not settle a spend hold; it stays counted at the worst case")

    def release(self, hold: str) -> None:
        try:
            self._call("spend_release", {"p_hold": hold})
        except httpx.HTTPError:
            logger.warning("Could not release a spend hold; it stays counted at the worst case")

    def spent_usd(self) -> float:
        return float(self._call("spend_spent_usd", {}))

    def committed_usd(self) -> float:
        return float(self._call("spend_committed_usd", {}))

    def _call(self, function: str, arguments: dict[str, object]) -> Any:
        response = self._http.post(function, json=arguments)
        response.raise_for_status()
        return response.json() if response.content else None  # Void functions send no body.


@dataclass(slots=True)
class Reservation:
    """A worst-case cost held against the cap while a call is in flight."""

    hold: str
    usd: float
    open: bool = True


class SpendGuard:
    """Kill switch plus cap. The ledger grants holds atomically, so concurrent calls cannot
    each pass the check and overshoot the cap together."""

    def __init__(self, *, enabled: bool, cap_usd: float, ledger: SpendLedger) -> None:
        self._enabled = enabled
        self._cap_usd = cap_usd
        self._ledger = ledger

    def ensure_enabled(self) -> None:
        """For calls that are not billed themselves, such as file uploads."""
        if not self._enabled:
            raise PaidCallsDisabledError()

    def reserve(self, worst_case_usd: float) -> Reservation:
        """Hold the worst-case cost, or raise if it would not fit under the cap."""
        self.ensure_enabled()
        hold = self._ledger.hold(worst_case_usd, self._cap_usd)
        if hold is None:
            committed = self._ledger.committed_usd()
            raise SpendCapExceededError(committed, worst_case_usd, self._cap_usd)
        return Reservation(hold, worst_case_usd)

    def settle(self, reservation: Reservation, entries: Sequence[CostEntry]) -> None:
        """Record what the call cost and free its reservation."""
        if reservation.open:
            reservation.open = False
            self._ledger.settle(reservation.hold, entries)

    def release(self, reservation: Reservation) -> None:
        """Free a reservation without recording a cost (the call never went through)."""
        if reservation.open:
            reservation.open = False
            self._ledger.release(reservation.hold)

    def spent_usd(self) -> float:
        return self._ledger.spent_usd()
