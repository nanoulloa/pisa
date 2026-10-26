"""Constant-acceleration fits with honest uncertainty, shared by the physics tests."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from pisa_engine.physics.trajectory import FloatArray, Trajectory

# Tracking quantization: residuals below this (pixels RMS) are not signal. Without the floor a
# perfect synthetic fit would claim zero uncertainty.
NOISE_FLOOR_PX = 0.05


@dataclass(frozen=True, slots=True)
class FreeFallFit:
    """y(t) = c2 (t - t_mid)^2 + c1 (t - t_mid) + c0 in image pixels (y down)."""

    coefficients: FloatArray  # c2, c1, c0
    covariance: FloatArray  # 3 x 3, for the coefficients
    t_mid: float
    residual_rms: float
    samples: int

    @property
    def acceleration(self) -> float:
        return 2 * float(self.coefficients[0])

    @property
    def acceleration_se(self) -> float:
        return 2 * math.sqrt(float(self.covariance[0, 0]))

    def polynomial(self) -> FloatArray:
        """The same parabola as coefficients of absolute time t, highest power first."""
        c2, c1, c0 = (float(c) for c in self.coefficients)
        m = self.t_mid
        return np.array([c2, c1 - 2 * c2 * m, c2 * m * m - c1 * m + c0])

    def velocity(self, t: float) -> tuple[float, float]:
        """Vertical velocity at time t and its standard error."""
        tau = t - self.t_mid
        gradient = np.array([2 * tau, 1.0, 0.0])
        value = float(gradient @ self.coefficients)
        variance = float(gradient @ self.covariance @ gradient)
        return value, math.sqrt(max(variance, 0.0))


def fit_free_fall(phase: Trajectory) -> FreeFallFit:
    t_mid = float(phase.t.mean())
    tau = phase.t - t_mid
    design = np.column_stack([tau**2, tau, np.ones_like(tau)])
    coefficients, *_ = np.linalg.lstsq(design, phase.y, rcond=None)
    residuals = phase.y - design @ coefficients
    n = len(phase)
    sigma2 = max(float(residuals @ residuals) / max(n - 3, 1), NOISE_FLOOR_PX**2)
    covariance = sigma2 * np.linalg.inv(design.T @ design)
    return FreeFallFit(
        coefficients=coefficients,
        covariance=covariance,
        t_mid=t_mid,
        residual_rms=math.sqrt(float(residuals @ residuals) / n),
        samples=n,
    )
