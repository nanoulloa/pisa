"""The ghost runs on top of real motion and parts from motion real physics does not allow."""

from __future__ import annotations

import numpy as np
import pytest

from pisa_engine.physics.implied_g import Scale
from pisa_engine.physics.trajectory import Trajectory, segment_flight
from pisa_engine.render.ghost import OwnedFlight, evidence_series, ghosts
from pisa_engine.synthetic import BallScene

PX_PER_M = 400.0
EXACT = Scale(low_px_per_m=PX_PER_M, high_px_per_m=PX_PER_M)


def _owned(rows: np.ndarray, object_id: int = 0) -> OwnedFlight:
    trajectory = Trajectory(t=rows[:, 0], x=rows[:, 1], y=rows[:, 2])
    return OwnedFlight(phrase="ball", object_id=object_id, flight=segment_flight(trajectory))


def _scene(**kwargs: object) -> OwnedFlight:
    return _owned(BallScene(**kwargs).true_trajectory())  # type: ignore[arg-type]


def test_a_real_fall_has_its_ghost_on_top() -> None:
    (ghost,) = ghosts([_scene(hold_s=0.1, duration_s=0.7)], scale=None, slow_motion=False)
    assert ghost.model == "fit"
    assert ghost.deviation_px() < 0.5


def test_eased_motion_parts_from_the_closest_gravity_path() -> None:
    (ghost,) = ghosts(
        [_scene(profile="eased", hold_s=0.1, duration_s=0.7)], scale=None, slow_motion=False
    )
    assert ghost.model == "fit"
    assert ghost.deviation_px() > 10


def test_with_a_scale_the_ghost_falls_with_earths_gravity() -> None:
    moon = _scene(g_mps2=1.62, hold_s=0.1, duration_s=0.7)
    (ghost,) = ghosts([moon], scale=EXACT, slow_motion=False)
    assert ghost.model == "earth_gravity"
    assert ghost.acceleration == pytest.approx(9.81 * PX_PER_M)
    # Under Earth's gravity the ball would be far lower by the end.
    _, ghost_y = ghost.position(ghost.measured.t[-1:])
    assert ghost_y[0] - ghost.measured.y[-1] > 100
    # A real fall passes T4, so its ghost stays on the closest gravity path, on top of it.
    earth = _scene(g_mps2=9.81, hold_s=0.1, duration_s=0.7)
    (real,) = ghosts([earth], scale=EXACT, slow_motion=False)
    assert real.model == "fit"
    assert real.deviation_px() < 0.5


def test_slow_motion_keeps_the_ghost_on_the_closest_gravity_path() -> None:
    (ghost,) = ghosts([_scene(g_mps2=1.62, duration_s=0.7)], scale=EXACT, slow_motion=True)
    assert ghost.model == "fit"


def test_a_pair_shares_one_acceleration() -> None:
    def pair(companion_g: float) -> list[OwnedFlight]:
        scene = BallScene(companion_g_mps2=companion_g, hold_s=0.1, duration_s=0.7)
        companion = scene.companion_trajectory()
        assert companion is not None
        return [_owned(scene.true_trajectory(), 0), _owned(companion, 1)]

    apart = ghosts(pair(6.0), scale=None, slow_motion=False)
    assert [g.model for g in apart] == ["partner", "partner"]
    assert apart[0].acceleration == pytest.approx((9.81 + 6.0) / 2 * PX_PER_M, rel=1e-6)
    assert min(g.deviation_px() for g in apart) > 30
    together = ghosts(pair(9.81), scale=None, slow_motion=False)
    assert [g.model for g in together] == ["fit", "fit"]
    assert max(g.deviation_px() for g in together) < 0.5


def test_a_bounce_that_gains_energy_rises_above_its_ghost() -> None:
    bouncy = _scene(profile="bounce", restitution=1.2, y0_px=400.0, duration_s=1.0, vx_mps=0.5)
    found = ghosts([bouncy], scale=None, slow_motion=False)
    elastic = next(g for g in found if g.model == "elastic_bounce")
    assert found[0] is elastic  # The most telling ghost comes first.
    _, ghost_y = elastic.position(elastic.measured.t)
    # y points down: the object's highest point is above the highest point physics allows.
    assert elastic.measured.y.min() < ghost_y.min() - 50


def test_a_real_bounce_keeps_the_closest_gravity_path() -> None:
    found = ghosts(
        [_scene(profile="bounce", restitution=0.7, duration_s=1.4, vx_mps=0.5)],
        scale=None,
        slow_motion=False,
    )
    assert [g.model for g in found] == ["fit", "fit"]
    assert max(g.deviation_px() for g in found) < 0.5


def test_series_hold_the_measured_points_and_the_ghost_at_the_same_times() -> None:
    moon = _scene(g_mps2=1.62, hold_s=0.1, duration_s=0.7)
    found = ghosts([moon], scale=EXACT, slow_motion=False)
    (series,) = evidence_series(found)
    assert series.model == "earth_gravity"
    assert len(series.t_s) == len(series.y_px) == len(series.ghost_y_px) == len(found[0].measured)
    assert series.px_per_m == PX_PER_M
