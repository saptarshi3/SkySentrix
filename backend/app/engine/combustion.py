from __future__ import annotations

from dataclasses import dataclass

from app.engine.performance_map import PerformanceSample


@dataclass(frozen=True)
class CombustionOutput:
    fuel_flow_lph: float
    combustion_efficiency: float
    thermal_power_kw: float
    torque_nm: float
    egt_base_c: float


class CombustionModel:
    AFR_STOICH = 14.7
    GASOLINE_DENSITY_KG_L = 0.74
    LHV_MJ_KG = 43.0

    @staticmethod
    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))

    def compute(
        self,
        *,
        rpm: float,
        load: float,
        air_mass_flow_kg_s: float,
        injection_timing_deg: float,
        perf: PerformanceSample,
        combustion_health: float,
        fuel_health: float,
        fault_fuel_mult: float,
        fault_combustion_mult: float,
        throttle: float,
    ) -> CombustionOutput:
        rpm_safe = max(rpm, 300.0)

        throttle_effect = self._clamp(0.12 + 0.95 * throttle, 0.05, 1.05)
        base_fuel = perf.fuel_flow_lph * throttle_effect * fault_fuel_mult / max(self._clamp(fuel_health, 0.6, 1.0), 0.45)

        fuel_kg_s = (base_fuel * self.GASOLINE_DENSITY_KG_L) / 3600.0
        afr_actual = air_mass_flow_kg_s / max(fuel_kg_s, 1e-5)
        lambda_ratio = afr_actual / self.AFR_STOICH

        timing_effect = 1.0 - 0.0015 * abs(injection_timing_deg - 24.0)
        mixture_effect = 1.0 - 0.22 * abs(lambda_ratio - 1.0)

        combustion_eff = perf.efficiency * self._clamp(combustion_health, 0.5, 1.0) * self._clamp(fault_combustion_mult, 0.5, 1.2)
        combustion_eff *= self._clamp(timing_effect, 0.70, 1.03) * self._clamp(mixture_effect, 0.60, 1.03)
        combustion_eff = self._clamp(combustion_eff, 0.45, 0.98)

        thermal_power_kw = fuel_kg_s * self.LHV_MJ_KG * 1000.0 * combustion_eff
        torque_from_power = 9550.0 * max(thermal_power_kw * 0.32, 0.0) / rpm_safe

        # Blend map-torque with combustion-derived torque.
        torque = 0.45 * perf.torque_nm + 0.55 * torque_from_power
        torque *= (0.38 + 0.70 * throttle)
        torque *= (0.90 + 0.10 * self._clamp(load, 0.0, 1.0))
        torque = max(0.0, torque)

        egt_base = perf.egt_c + 120.0 * (1.0 - combustion_eff) + 30.0 * max(0.0, 1.0 - lambda_ratio) + 22.0 * throttle

        return CombustionOutput(
            fuel_flow_lph=base_fuel,
            combustion_efficiency=combustion_eff,
            thermal_power_kw=thermal_power_kw,
            torque_nm=torque,
            egt_base_c=egt_base,
        )
