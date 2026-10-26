"""Our own hard stop on paid API calls.

Meta's Billing "Spend limit" only sends email alerts, so the engine enforces the
budget itself: a kill switch, plus a persistent ledger checked before every call.
"""

from __future__ import annotations

import threading
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pisa_contracts import CostEntry


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
    def total_usd(self) -> float: ...

    def append(self, entries: Sequence[CostEntry]) -> None: ...


class InMemorySpendLedger:
    def __init__(self) -> None:
        self.entries: list[CostEntry] = []

    def total_usd(self) -> float:
        return sum(entry.usd for entry in self.entries)

    def append(self, entries: Sequence[CostEntry]) -> None:
        self.entries.extend(entries)


class JsonlSpendLedger:
    """One `CostEntry` per line. Survives restarts; local to one machine."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def total_usd(self) -> float:
        if not self._path.exists():
            return 0.0
        with self._path.open(encoding="utf-8") as lines:
            return sum(CostEntry.model_validate_json(line).usd for line in lines if line.strip())

    def append(self, entries: Sequence[CostEntry]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as ledger:
            for entry in entries:
                ledger.write(entry.model_dump_json() + "\n")


@dataclass(slots=True)
class Reservation:
    """A worst-case cost held against the cap while a call is in flight."""

    usd: float
    open: bool = True


class SpendGuard:
    """Kill switch plus cap. Reserving and settling are atomic, so concurrent calls cannot
    each pass the check and overshoot the cap together."""

    def __init__(self, *, enabled: bool, cap_usd: float, ledger: SpendLedger) -> None:
        self._enabled = enabled
        self._cap_usd = cap_usd
        self._ledger = ledger
        self._lock = threading.Lock()
        self._reserved_usd = 0.0

    def ensure_enabled(self) -> None:
        """For calls that are not billed themselves, such as file uploads."""
        if not self._enabled:
            raise PaidCallsDisabledError()

    def reserve(self, worst_case_usd: float) -> Reservation:
        """Hold the worst-case cost, or raise if it would not fit under the cap."""
        self.ensure_enabled()
        with self._lock:
            committed = self._ledger.total_usd() + self._reserved_usd
            if committed + worst_case_usd > self._cap_usd:
                raise SpendCapExceededError(committed, worst_case_usd, self._cap_usd)
            self._reserved_usd += worst_case_usd
        return Reservation(worst_case_usd)

    def settle(self, reservation: Reservation, entries: Sequence[CostEntry]) -> None:
        """Record what the call cost and free its reservation."""
        with self._lock:
            if reservation.open:
                self._ledger.append(entries)
                self._close(reservation)

    def release(self, reservation: Reservation) -> None:
        """Free a reservation without recording a cost (the call never went through)."""
        with self._lock:
            if reservation.open:
                self._close(reservation)

    def spent_usd(self) -> float:
        return self._ledger.total_usd()

    def _close(self, reservation: Reservation) -> None:
        self._reserved_usd -= reservation.usd
        reservation.open = False
