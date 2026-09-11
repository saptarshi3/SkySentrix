from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SubsystemHealthState:
    combustion: float = 1.0
    thermal: float = 1.0
    lubrication: float = 1.0
    mechanical: float = 1.0
    fuel: float = 1.0
    electrical: float = 1.0

    @property
    def overall(self) -> float:
        return max(0.0, min(1.0, (
            0.22 * self.combustion
            + 0.18 * self.thermal
            + 0.18 * self.lubrication
            + 0.17 * self.mechanical
            + 0.13 * self.fuel
            + 0.12 * self.electrical
        )))


@dataclass
class EngineTrueState:
    rpm: float = 850.0
    manifold_pressure_kpa: float = 45.0
    air_mass_flow_kg_s: float = 0.08
    fuel_flow_lph: float = 8.5
    egt_c: float = 560.0
    cht_c: float = 118.0
    oil_temp_c: float = 72.0
    oil_pressure: float = 34.0
    vibration: float = 0.22
    battery_voltage: float = 12.8
    alternator_health: float = 1.0
    injection_timing_deg: float = 16.0
    torque_nm: float = 120.0
    power_kw: float = 20.0
    engine_efficiency: float = 0.92
    propeller_load: float = 0.20
    pressure_kpa: float = 101.3
    density_ratio: float = 1.0
    airspeed_mps: float = 18.0


@dataclass
class SensorObservation:
    rpm: float
    manifold_pressure_kpa: float
    air_mass_flow_kg_s: float
    fuel_flow_lph: float
    egt_c: float
    cht_c: float
    oil_temp_c: float
    oil_pressure: float
    vibration: float
    battery_voltage: float
    alternator_health: float
    injection_timing_deg: float
    torque_nm: float
    power_kw: float
    propeller_load: float
    pressure_kpa: float
    density_ratio: float
    airspeed_mps: float
