from __future__ import annotations


class PropellerModel:
    """Prototype propeller demand/load approximation."""

    @staticmethod
    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))

    def compute_load(
        self,
        *,
        rpm: float,
        airspeed_mps: float,
        density_ratio: float,
        pilot_load_command: float,
        prop_health: float,
    ) -> float:
        dr = self._clamp(density_ratio, 0.45, 1.2)
        rpm_norm = self._clamp(rpm / 2700.0, 0.0, 1.35)
        v_norm = self._clamp(airspeed_mps / 70.0, 0.0, 1.4)

        aerodynamic_demand = (0.35 * rpm_norm * rpm_norm + 0.25 * v_norm * v_norm + 0.22 * rpm_norm * v_norm) * dr
        commanded = self._clamp(pilot_load_command, 0.0, 1.0)

        load = (0.55 * aerodynamic_demand + 0.45 * commanded) / max(self._clamp(prop_health, 0.65, 1.0), 0.65)
        return self._clamp(load, 0.0, 1.0)
