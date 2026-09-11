from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

from app.config import FAULT_TYPES


@dataclass
class FaultState:
    fault_type: str
    target_severity: float
    progression_per_sec: float
    sensor_name: Optional[str] = None
    current_severity: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class FaultInfluence:
    combustion_eff_mult: float = 1.0
    fuel_delivery_mult: float = 1.0
    lubrication_mult: float = 1.0
    electrical_output_mult: float = 1.0
    thermal_release_mult: float = 1.0
    propeller_health_mult: float = 1.0
    instability: float = 0.0
    battery_bias: float = 0.0
    extra_rpm_damping: float = 0.0
    fault_stress: dict[str, float] = field(default_factory=dict)


class FaultManager:
    def __init__(self) -> None:
        self.active_faults: Dict[str, FaultState] = {}
        self.sensor_drift_offsets: Dict[str, float] = {}
        self.sensor_failure_values: Dict[str, float] = {}

    def inject(self, fault_type: str, severity: float, progression_per_sec: float, sensor_name: Optional[str] = None) -> None:
        if fault_type not in FAULT_TYPES:
            raise ValueError(f"Unsupported fault type: {fault_type}")
        self.active_faults[fault_type] = FaultState(
            fault_type=fault_type,
            target_severity=max(0.0, min(1.0, severity)),
            progression_per_sec=max(0.0, min(0.05, progression_per_sec)),
            sensor_name=sensor_name,
        )

    def clear(self, fault_type: str) -> None:
        self.active_faults.pop(fault_type, None)
        if fault_type in {"sensor_drift", "sensor_failure"}:
            self.sensor_drift_offsets = {}
            self.sensor_failure_values = {}

    def clear_all(self) -> None:
        self.active_faults = {}
        self.sensor_drift_offsets = {}
        self.sensor_failure_values = {}

    def update(self, dt_sec: float) -> FaultInfluence:
        infl = FaultInfluence(fault_stress={
            "combustion": 0.0,
            "thermal": 0.0,
            "lubrication": 0.0,
            "mechanical": 0.0,
            "fuel": 0.0,
            "electrical": 0.0,
        })

        for fault in self.active_faults.values():
            fault.current_severity += (fault.target_severity - fault.current_severity) * min(1.0, fault.progression_per_sec * dt_sec * 5)
            s = fault.current_severity

            if fault.fault_type == "injector_degradation":
                infl.fuel_delivery_mult *= 1.0 + 0.55 * s
                infl.combustion_eff_mult *= 1.0 - 0.35 * s
                infl.instability += 0.18 * s
                infl.extra_rpm_damping += 0.08 * s
                infl.fault_stress["combustion"] += 1.8 * s
                infl.fault_stress["fuel"] += 2.4 * s
                infl.fault_stress["thermal"] += 1.1 * s

            elif fault.fault_type == "misfire":
                infl.combustion_eff_mult *= 1.0 - 0.32 * s
                infl.instability += 0.42 * s
                infl.extra_rpm_damping += 0.22 * s
                infl.fault_stress["combustion"] += 1.7 * s
                infl.fault_stress["mechanical"] += 1.0 * s

            elif fault.fault_type == "lubrication_problem":
                infl.lubrication_mult *= 1.0 - 0.35 * s
                infl.instability += 0.11 * s
                infl.fault_stress["lubrication"] += 2.0 * s
                infl.fault_stress["mechanical"] += 0.9 * s
                infl.fault_stress["thermal"] += 0.6 * s

            elif fault.fault_type == "overheating":
                infl.thermal_release_mult *= 1.0 + 0.22 * s
                infl.fault_stress["thermal"] += 2.1 * s
                infl.fault_stress["combustion"] += 0.7 * s
                infl.instability += 0.10 * s

            elif fault.fault_type == "excessive_vibration":
                infl.instability += 0.55 * s
                infl.propeller_health_mult *= 1.0 - 0.12 * s
                infl.fault_stress["mechanical"] += 2.2 * s

            elif fault.fault_type == "combustion_instability":
                infl.combustion_eff_mult *= 1.0 - 0.18 * s
                infl.instability += 0.46 * s
                infl.fault_stress["combustion"] += 1.6 * s
                infl.fault_stress["thermal"] += 0.5 * s

            elif fault.fault_type == "fuel_system_degradation":
                infl.fuel_delivery_mult *= 1.0 + 0.18 * s
                infl.combustion_eff_mult *= 1.0 - 0.14 * s
                infl.instability += 0.12 * s
                infl.fault_stress["fuel"] += 1.9 * s
                infl.fault_stress["combustion"] += 0.7 * s

            elif fault.fault_type == "alternator_problem":
                infl.electrical_output_mult *= 1.0 - 0.65 * s
                infl.battery_bias -= 1.6 * s
                infl.fault_stress["electrical"] += 2.2 * s

            elif fault.fault_type == "sensor_drift":
                sensor = fault.sensor_name or "egt"
                current = self.sensor_drift_offsets.get(sensor, 0.0)
                self.sensor_drift_offsets[sensor] = current + (0.02 + 0.12 * s) * dt_sec

            elif fault.fault_type == "sensor_failure":
                sensor = fault.sensor_name or "oil_pressure"
                if sensor not in self.sensor_failure_values and s >= 0.5:
                    self.sensor_failure_values[sensor] = 0.0

        infl.combustion_eff_mult = max(0.3, infl.combustion_eff_mult)
        infl.lubrication_mult = max(0.3, infl.lubrication_mult)
        infl.electrical_output_mult = max(0.2, infl.electrical_output_mult)
        infl.propeller_health_mult = max(0.6, infl.propeller_health_mult)
        infl.thermal_release_mult = max(0.6, infl.thermal_release_mult)

        return infl

    def apply_sensor_effects(self, values: Dict[str, float]) -> Dict[str, float]:
        for key, drift in self.sensor_drift_offsets.items():
            if key in values:
                values[key] += drift

        for key, failure_value in self.sensor_failure_values.items():
            if key in values:
                values[key] = failure_value

        return values

    def snapshot(self) -> Dict[str, dict]:
        out: Dict[str, dict] = {}
        for k, v in self.active_faults.items():
            out[k] = {
                "target_severity": v.target_severity,
                "current_severity": v.current_severity,
                "progression_per_sec": v.progression_per_sec,
                "sensor_name": v.sensor_name,
            }
        return out
