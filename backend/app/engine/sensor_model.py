from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.engine.state import EngineTrueState, SensorObservation


@dataclass
class SensorNoiseConfig:
    rpm_sigma: float = 6.0
    manifold_sigma: float = 0.6
    airflow_sigma: float = 0.006
    fuel_sigma: float = 0.18
    egt_sigma: float = 1.8
    cht_sigma: float = 0.8
    oil_temp_sigma: float = 0.45
    oil_pressure_sigma: float = 0.55
    vibration_sigma: float = 0.012
    battery_sigma: float = 0.03
    alternator_sigma: float = 0.004
    timing_sigma: float = 0.035
    torque_sigma: float = 1.4
    power_sigma: float = 0.45


class SensorModel:
    def __init__(self) -> None:
        self.noise = SensorNoiseConfig()

    @staticmethod
    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))

    def observe(self, true: EngineTrueState, rng: np.random.Generator, instability: float) -> SensorObservation:
        isf = max(0.0, instability)

        def n(sig: float) -> float:
            return float(rng.normal(0.0, sig * (1.0 + 1.1 * isf)))

        return SensorObservation(
            rpm=self._clamp(true.rpm + n(self.noise.rpm_sigma), 0.0, 3600.0),
            manifold_pressure_kpa=self._clamp(true.manifold_pressure_kpa + n(self.noise.manifold_sigma), 0.0, 120.0),
            air_mass_flow_kg_s=self._clamp(true.air_mass_flow_kg_s + n(self.noise.airflow_sigma), 0.0, 3.0),
            fuel_flow_lph=self._clamp(true.fuel_flow_lph + n(self.noise.fuel_sigma), 0.0, 180.0),
            egt_c=self._clamp(true.egt_c + n(self.noise.egt_sigma), 0.0, 1200.0),
            cht_c=self._clamp(true.cht_c + n(self.noise.cht_sigma), -20.0, 420.0),
            oil_temp_c=self._clamp(true.oil_temp_c + n(self.noise.oil_temp_sigma), -30.0, 250.0),
            oil_pressure=self._clamp(true.oil_pressure + n(self.noise.oil_pressure_sigma), 0.0, 150.0),
            vibration=self._clamp(true.vibration + n(self.noise.vibration_sigma), 0.0, 7.0),
            battery_voltage=self._clamp(true.battery_voltage + n(self.noise.battery_sigma), 0.0, 18.0),
            alternator_health=self._clamp(true.alternator_health + n(self.noise.alternator_sigma), 0.0, 1.1),
            injection_timing_deg=self._clamp(true.injection_timing_deg + n(self.noise.timing_sigma), 0.0, 45.0),
            torque_nm=max(0.0, true.torque_nm + n(self.noise.torque_sigma)),
            power_kw=max(0.0, true.power_kw + n(self.noise.power_sigma)),
            propeller_load=self._clamp(true.propeller_load + float(rng.normal(0.0, 0.004)), 0.0, 1.0),
            pressure_kpa=self._clamp(true.pressure_kpa + float(rng.normal(0.0, 0.12)), 20.0, 110.0),
            density_ratio=self._clamp(true.density_ratio + float(rng.normal(0.0, 0.002)), 0.4, 1.2),
            airspeed_mps=self._clamp(true.airspeed_mps + float(rng.normal(0.0, 0.25)), 0.0, 130.0),
        )
