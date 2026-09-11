from __future__ import annotations


class ManifoldPressureModel:
    """Simple manifold pressure approximation in kPa (absolute)."""

    @staticmethod
    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))

    def compute(self, *, throttle: float, rpm: float, pressure_kpa: float, engine_load: float, intake_health: float) -> float:
        throttle = self._clamp(throttle, 0.0, 1.0)
        load = self._clamp(engine_load, 0.0, 1.0)
        intake_health = self._clamp(intake_health, 0.5, 1.0)

        base = (22.0 + 80.0 * throttle) * (pressure_kpa / 101.325)
        rpm_pumping = 0.0035 * max(rpm - 1800.0, -1000.0)
        load_term = 4.0 * (load - 0.5)
        mp = (base - rpm_pumping + load_term) * intake_health

        return self._clamp(mp, 12.0, max(25.0, pressure_kpa * 1.05))
