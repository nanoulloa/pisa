"""The ghost: where real physics puts the object during each measured flight.

Pure: flights in, ghosts out. A ghost leaves with its object (same place, same speed) and
then follows a law. It follows a stricter law only where that law's test found a violation,
so on a real clip every ghost runs on top of its object:

- elastic_bounce: after a bounce that gains energy, the highest bounce physics allows, which
  keeps all of the arriving speed. The object rises above it.
- partner: two objects released together that fall apart get their shared acceleration, the
  mean of theirs. Each drifts away from its ghost.
- earth_gravity: when the size reference shows gravity that is not Earth's (and nothing
  suggests slow motion), Earth's gravity at the measured scale. The object lags behind.
- fit: otherwise, the closest constant-gravity path. Motion that no gravity makes (eased,
  slowing while falling) parts from it.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np

from pisa_contracts import EvidenceSeries
from pisa_engine.physics.bounce import bounce_energy, contact_time
from pisa_engine.physics.fit import fit_free_fall
from pisa_engine.physics.implied_g import EARTH_G, Scale, implied_gravity
from pisa_engine.physics.pair import PairThresholds, galileo_pair
from pisa_engine.physics.trajectory import Bounce, Flight, FloatArray, Trajectory

GhostModel = Literal["fit", "earth_gravity", "partner", "elastic_bounce"]

MIN_SAMPLES = 8
MAX_SERIES = 6


@dataclass(frozen=True, slots=True)
class OwnedFlight:
    """A flight and the tracked object it belongs to."""

    phrase: str
    object_id: int
    flight: Flight


@dataclass(frozen=True, slots=True)
class Ghost:
    """y(t) = y0 + vy (t - t_ref) + a (t - t_ref)^2 / 2 and x(t) = x0 + vx (t - t_ref), in
    stabilized pixels with y down, shown from `start_s` to `end_s`."""

    phrase: str
    object_id: int
    model: GhostModel
    measured: Trajectory
    start_s: float
    end_s: float
    t_ref: float
    x0: float
    vx: float
    y0: float
    vy: float
    acceleration: float
    px_per_m: float | None

    def position(self, t: FloatArray) -> tuple[FloatArray, FloatArray]:
        tau = t - self.t_ref
        x = self.x0 + self.vx * tau
        y = self.y0 + self.vy * tau + 0.5 * self.acceleration * tau**2
        return x, y

    def deviation_px(self) -> float:
        """The largest vertical gap between the object and its ghost."""
        _, y = self.position(self.measured.t)
        return float(np.abs(self.measured.y - y).max())

    def telling(self) -> float:
        """The gap relative to how far the object moved, to rank ghosts by what they show."""
        travel = float(self.measured.y.max() - self.measured.y.min())
        return self.deviation_px() / max(travel, 5.0)


def ghosts(
    flights: Sequence[OwnedFlight], *, scale: Scale | None, slow_motion: bool
) -> list[Ghost]:
    """One ghost per measured flight phase, the most telling first."""
    px_per_m = math.sqrt(scale.low_px_per_m * scale.high_px_per_m) if scale else None
    shared = _shared_accelerations(flights)
    found: list[Ghost] = []
    for index, owned in enumerate(flights):
        for number, phase in enumerate(owned.flight.phases):
            if len(phase) < MIN_SAMPLES:
                continue
            bounce = next((b for b in owned.flight.bounces if b.after is phase), None)
            elastic = _elastic(owned, bounce, px_per_m) if bounce is not None else None
            if elastic is not None:
                found.append(elastic)
            elif number == 0 and index in shared:
                found.append(_anchored(owned, phase, "partner", shared[index], px_per_m))
            elif px_per_m is not None and not slow_motion and _not_earth(phase, scale):
                earth = EARTH_G * px_per_m
                found.append(_anchored(owned, phase, "earth_gravity", earth, px_per_m))
            else:
                found.append(_fitted(owned, phase, px_per_m))
    return sorted(found, key=lambda ghost: ghost.telling(), reverse=True)


def evidence_series(found: Sequence[Ghost]) -> list[EvidenceSeries]:
    series = []
    for ghost in found[:MAX_SERIES]:
        _, ghost_y = ghost.position(ghost.measured.t)
        series.append(
            EvidenceSeries(
                phrase=ghost.phrase,
                object_id=ghost.object_id,
                model=ghost.model,
                t_s=_rounded(ghost.measured.t, 4),
                y_px=_rounded(ghost.measured.y, 2),
                ghost_y_px=_rounded(ghost_y, 2),
                px_per_m=None if ghost.px_per_m is None else round(ghost.px_per_m, 2),
            )
        )
    return series


def _fitted(owned: OwnedFlight, phase: Trajectory, px_per_m: float | None) -> Ghost:
    """The closest constant-gravity path through the measured points."""
    fit = fit_free_fall(phase)
    t_ref = float(phase.t[0])
    y0 = float(np.polyval(fit.polynomial(), t_ref))
    vy, _ = fit.velocity(t_ref)
    return _ghost(owned, phase, "fit", t_ref, y0, vy, fit.acceleration, px_per_m)


def _anchored(
    owned: OwnedFlight,
    phase: Trajectory,
    model: GhostModel,
    acceleration: float,
    px_per_m: float | None,
) -> Ghost:
    """Leaves where and as fast as the object left (from its own fit), with this acceleration."""
    fit = fit_free_fall(phase)
    t_ref = float(phase.t[0])
    y0 = float(np.polyval(fit.polynomial(), t_ref))
    vy, _ = fit.velocity(t_ref)
    return _ghost(owned, phase, model, t_ref, y0, vy, acceleration, px_per_m)


def _ghost(
    owned: OwnedFlight,
    phase: Trajectory,
    model: GhostModel,
    t_ref: float,
    y0: float,
    vy: float,
    acceleration: float,
    px_per_m: float | None,
) -> Ghost:
    tau = phase.t - t_ref
    design = np.column_stack([np.ones_like(tau), tau])
    (x0, vx), *_ = np.linalg.lstsq(design, phase.x, rcond=None)
    return Ghost(
        phrase=owned.phrase,
        object_id=owned.object_id,
        model=model,
        measured=phase,
        start_s=t_ref,
        end_s=float(phase.t[-1]),
        t_ref=t_ref,
        x0=float(x0),
        vx=float(vx),
        y0=float(y0),
        vy=float(vy),
        acceleration=acceleration,
        px_per_m=px_per_m,
    )


def _elastic(owned: OwnedFlight, bounce: Bounce, px_per_m: float | None) -> Ghost | None:
    """After a bounce that gains energy: leave the contact with all of the arriving speed."""
    if bounce_energy(bounce).outcome != "violation":
        return None
    before, after = fit_free_fall(bounce.before), fit_free_fall(bounce.after)
    contact = contact_time(before, after, bounce)
    speed_in, _ = before.velocity(contact)
    tau = bounce.after.t - contact
    design = np.column_stack([np.ones_like(tau), tau])
    (x0, vx), *_ = np.linalg.lstsq(design, bounce.after.x, rcond=None)
    return Ghost(
        phrase=owned.phrase,
        object_id=owned.object_id,
        model="elastic_bounce",
        measured=bounce.after,
        start_s=contact,
        end_s=float(bounce.after.t[-1]),
        t_ref=contact,
        x0=float(x0),
        vx=float(vx),
        y0=float(np.polyval(before.polynomial(), contact)),
        vy=-speed_in,
        acceleration=before.acceleration,
        px_per_m=px_per_m,
    )


def _not_earth(phase: Trajectory, scale: Scale | None) -> bool:
    """T4 measured gravity whose interval leaves Earth's out."""
    return scale is not None and implied_gravity(fit_free_fall(phase), scale).outcome == "violation"


def _shared_accelerations(flights: Sequence[OwnedFlight]) -> dict[int, float]:
    """Pairs whose first phases were released together and fail T2, with their mean
    acceleration: the one a real pair would share."""
    gap = PairThresholds().max_release_gap_s
    firsts = {
        index: owned.flight.phases[0]
        for index, owned in enumerate(flights)
        if owned.flight.phases and len(owned.flight.phases[0]) >= MIN_SAMPLES
    }
    shared: dict[int, float] = {}
    for a, first in firsts.items():
        for b, second in firsts.items():
            if b <= a or abs(first.t[0] - second.t[0]) > gap:
                continue
            if galileo_pair(first, second).outcome == "violation":
                mean = (fit_free_fall(first).acceleration + fit_free_fall(second).acceleration) / 2
                shared.setdefault(a, mean)
                shared.setdefault(b, mean)
    return shared


def _rounded(values: FloatArray, digits: int) -> list[float]:
    return [round(float(v), digits) for v in values]
