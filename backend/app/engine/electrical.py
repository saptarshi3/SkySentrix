from __future__ import annotations


class ElectricalModel:
    @staticmethod
    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))

    def alternator_health(self, *, electrical_health: float, base_degradation: float, fault_electrical_mult: float) -> float:
        val = (1.0 - 0.18 * base_degradation) * self._clamp(electrical_health, 0.4, 1.0) * fault_electrical_mult
        return self._clamp(val, 0.0, 1.0)

    def battery_target(self, *, rpm: float, alternator_health: float, engine_load: float, battery_bias: float) -> float:
        electrical_load = 0.25 + 0.55 * self._clamp(engine_load, 0.0, 1.0)
        charging = 1.9 if rpm > 1200 else 0.35
        return 12.1 + charging * alternator_health - 0.48 * electrical_load + battery_bias
