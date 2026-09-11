from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class EnvironmentState:
    altitude_m: float
    ambient_temp_c: float
    pressure_pa: float
    pressure_kpa: float
    density_kg_m3: float
    density_ratio: float


class EnvironmentModel:
    """Reduced-order ISA-inspired atmosphere model for prototype simulation."""

    P0 = 101325.0
    T0 = 288.15
    R = 287.05
    G = 9.80665
    L = 0.0065
    RHO0 = 1.225

    @staticmethod
    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))

    def compute(self, altitude_m: float, ambient_temp_c: float) -> EnvironmentState:
        h = self._clamp(altitude_m, 0.0, 11000.0)

        # ISA pressure profile in troposphere.
        t_isa = self.T0 - self.L * h
        pressure = self.P0 * ((t_isa / self.T0) ** (self.G / (self.R * self.L)))

        # Density from measured/mission ambient temperature.
        temp_k = max(ambient_temp_c + 273.15, 200.0)
        density = pressure / (self.R * temp_k)

        density_ratio = self._clamp(density / self.RHO0, 0.45, 1.2)

        return EnvironmentState(
            altitude_m=altitude_m,
            ambient_temp_c=ambient_temp_c,
            pressure_pa=pressure,
            pressure_kpa=pressure / 1000.0,
            density_kg_m3=density,
            density_ratio=density_ratio,
        )
