from __future__ import annotations


class LubricationModel:
    @staticmethod
    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))

    def oil_pressure_target(
        self,
        *,
        rpm: float,
        oil_temp_c: float,
        lubrication_health: float,
        fault_lubrication_mult: float,
    ) -> float:
        lh = self._clamp(lubrication_health, 0.45, 1.0)

        viscosity_term = max(oil_temp_c - 85.0, 0.0)
        pressure = 18.0 + 0.019 * max(rpm, 0.0) - 0.13 * viscosity_term
        pressure *= lh * fault_lubrication_mult
        return self._clamp(pressure, 0.0, 120.0)

    def friction_heat_factor(self, *, oil_pressure: float, lubrication_health: float) -> float:
        p_norm = self._clamp(oil_pressure / 60.0, 0.0, 1.5)
        h = self._clamp(lubrication_health, 0.4, 1.0)
        return self._clamp((1.1 - p_norm) + (1.0 - h), 0.0, 1.5)
