from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ThermalOutput:
    egt_target_c: float
    cht_target_c: float
    oil_temp_target_c: float


class ThermalModel:
    @staticmethod
    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))

    def targets(
        self,
        *,
        ambient_temp_c: float,
        egt_base_c: float,
        engine_load: float,
        rpm: float,
        thermal_health: float,
        friction_heat: float,
        fault_thermal_mult: float,
    ) -> ThermalOutput:
        th = self._clamp(thermal_health, 0.5, 1.0)

        egt = egt_base_c * fault_thermal_mult + 18.0 * (1.0 - th) + 0.002 * max(rpm - 2000.0, 0.0)
        cht = ambient_temp_c + 55.0 + 0.17 * max(egt - 500.0, 0.0) + 42.0 * engine_load + 12.0 * (1.0 - th)
        oil_temp = ambient_temp_c + 40.0 + 0.08 * max(egt - 500.0, 0.0) + 15.0 * engine_load + 10.0 * friction_heat

        return ThermalOutput(
            egt_target_c=egt,
            cht_target_c=cht,
            oil_temp_target_c=oil_temp,
        )

    def update_with_noise(self, current: float, target: float, dt_sec: float, tau_sec: float, noise_sigma: float, rng: np.random.Generator) -> float:
        alpha = self._clamp(dt_sec / max(tau_sec, 0.05), 0.0, 1.0)
        return current + alpha * (target - current) + float(rng.normal(0.0, noise_sigma))
