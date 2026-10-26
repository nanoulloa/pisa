"""What one job spent, collected without passing a list through every adapter.

The client records each settled call here; the pipeline opens `collecting()` around a job
and saves what it gathered as the result's `costs`.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar

from pisa_contracts import CostEntry

_current: ContextVar[list[CostEntry] | None] = ContextVar("pisa_job_costs", default=None)


def record(entries: Sequence[CostEntry]) -> None:
    collected = _current.get()
    if collected is not None:
        collected.extend(entries)


@contextmanager
def collecting() -> Iterator[list[CostEntry]]:
    entries: list[CostEntry] = []
    token = _current.set(entries)
    try:
        yield entries
    finally:
        _current.reset(token)
