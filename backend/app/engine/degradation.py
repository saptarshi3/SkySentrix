from __future__ import annotations

from app.engine.state import SubsystemHealthState


class DegradationModel:
    @staticmethod
    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))

    def update(
        self,
        *,
        health: SubsystemHealthState,
        dt_sec: float,
        engine_load: float,
        egt_c: float,
        cht_c: float,
        oil_temp_c: float,
        oil_pressure: float,
        vibration: float,
        fault_stress: dict[str, float],
    ) -> None:
        dt_h = dt_sec / 3600.0

        thermal_stress = max(0.0, (egt_c - 730.0) / 200.0) + max(0.0, (cht_c - 210.0) / 120.0)
        lub_stress = max(0.0, (45.0 - oil_pressure) / 30.0) + max(0.0, (oil_temp_c - 105.0) / 70.0)
        mech_stress = max(0.0, (vibration - 0.45) / 0.5) + 0.4 * max(0.0, engine_load - 0.75)

        base_wear = 0.0025 * dt_h * (0.35 + 0.65 * engine_load)

        health.combustion = self._clamp(health.combustion - base_wear * (1.2 + 0.8 * thermal_stress + fault_stress.get("combustion", 0.0)), 0.35, 1.0)
        health.thermal = self._clamp(health.thermal - base_wear * (1.0 + 1.1 * thermal_stress + fault_stress.get("thermal", 0.0)), 0.30, 1.0)
        health.lubrication = self._clamp(health.lubrication - base_wear * (1.0 + 1.4 * lub_stress + fault_stress.get("lubrication", 0.0)), 0.28, 1.0)
        health.mechanical = self._clamp(health.mechanical - base_wear * (1.0 + 1.3 * mech_stress + fault_stress.get("mechanical", 0.0)), 0.28, 1.0)
        health.fuel = self._clamp(health.fuel - base_wear * (0.9 + 0.8 * fault_stress.get("fuel", 0.0)), 0.35, 1.0)
        health.electrical = self._clamp(health.electrical - base_wear * (0.8 + 1.2 * fault_stress.get("electrical", 0.0)), 0.35, 1.0)

        # Mild recovery only in low-stress operation (prototype assumption)
        if thermal_stress < 0.05 and lub_stress < 0.05 and mech_stress < 0.05 and engine_load < 0.4:
            rec = 0.00035 * dt_h
            health.thermal = self._clamp(health.thermal + rec, 0.0, 1.0)
            health.lubrication = self._clamp(health.lubrication + rec, 0.0, 1.0)
            health.mechanical = self._clamp(health.mechanical + 0.8 * rec, 0.0, 1.0)
