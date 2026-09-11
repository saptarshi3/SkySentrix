from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np

from app.config import MISSION_PRESETS, MODE_DEFAULTS
from app.engine.airflow import AirflowModel
from app.engine.combustion import CombustionModel
from app.engine.degradation import DegradationModel
from app.engine.electrical import ElectricalModel
from app.engine.environment import EnvironmentModel
from app.engine.faults import FaultManager
from app.engine.lubrication import LubricationModel
from app.engine.manifold import ManifoldPressureModel
from app.engine.performance_map import PerformanceMap
from app.engine.propeller import PropellerModel
from app.engine.sensor_model import SensorModel
from app.engine.state import EngineTrueState, SubsystemHealthState
from app.engine.thermal import ThermalModel
from app.models.schemas import TelemetryPoint


@dataclass
class MissionSegment:
    name: str
    start_sec: float
    end_sec: float
    throttle: float
    engine_load: float
    altitude: float
    ambient_temp: float


class EngineSimulator:
    """Synthetic but coupled reduced-order aero-piston engine model."""

    def __init__(self, seed: int = 42) -> None:
        self.rng = np.random.default_rng(seed)
        self.fault_manager = FaultManager()

        self.environment = EnvironmentModel()
        self.map = PerformanceMap()
        self.manifold = ManifoldPressureModel()
        self.airflow = AirflowModel()
        self.combustion = CombustionModel()
        self.propeller = PropellerModel()
        self.thermal = ThermalModel()
        self.lubrication = LubricationModel()
        self.electrical = ElectricalModel()
        self.sensor_model = SensorModel()
        self.degradation = DegradationModel()

        self.mode = "idle"
        defaults = MODE_DEFAULTS[self.mode]
        self.throttle = defaults.throttle
        self.engine_load_cmd = defaults.engine_load
        self.altitude = defaults.altitude
        self.ambient_temp = defaults.ambient_temp
        self.airspeed = 18.0

        self.time_sec = 0.0
        self.mission_elapsed_sec = 0.0
        self.mission_duration_sec = 0.0
        self.mission_name: Optional[str] = None
        self.mission_preset: Optional[str] = None
        self.mission_segments: List[MissionSegment] = []

        self.base_degradation = 0.0
        self.true = EngineTrueState()
        self.subsystem_health = SubsystemHealthState()

        self.manual_override = False

    @staticmethod
    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))

    def reset(self) -> None:
        seed = int(self.rng.integers(0, 10_000_000))
        self.__init__(seed=seed)

    def set_manual_controls(
        self,
        *,
        mode: Optional[str] = None,
        throttle: Optional[float] = None,
        engine_load: Optional[float] = None,
        altitude: Optional[float] = None,
        ambient_temp: Optional[float] = None,
    ) -> None:
        self.manual_override = True
        if mode is not None:
            if mode not in MODE_DEFAULTS:
                raise ValueError(f"Unsupported mode: {mode}")
            self.mode = mode
        if throttle is not None:
            self.throttle = self._clamp(throttle, 0.0, 1.0)
        if engine_load is not None:
            self.engine_load_cmd = self._clamp(engine_load, 0.0, 1.0)
        if altitude is not None:
            self.altitude = self._clamp(altitude, 0.0, 12000.0)
        if ambient_temp is not None:
            self.ambient_temp = self._clamp(ambient_temp, -50.0, 70.0)

    def set_mode(self, mode: str) -> None:
        if mode not in MODE_DEFAULTS:
            raise ValueError(f"Unsupported mode: {mode}")
        self.mode = mode
        defaults = MODE_DEFAULTS[mode]
        self.throttle = defaults.throttle
        self.engine_load_cmd = defaults.engine_load
        self.altitude = defaults.altitude
        self.ambient_temp = defaults.ambient_temp
        self.manual_override = True

    def load_mission(self, preset: str, duration_sec: int, mission_name: str) -> None:
        if preset not in MISSION_PRESETS:
            raise ValueError(f"Unsupported mission preset: {preset}")

        self.mission_name = mission_name
        self.mission_preset = preset
        self.mission_elapsed_sec = 0.0
        self.mission_duration_sec = float(duration_sec)
        self.manual_override = False

        cfg = MISSION_PRESETS[preset]
        segments = cfg["segments"]
        self.mission_segments = []

        start = 0.0
        for seg in segments:
            seg_dur = duration_sec * float(seg["duration_ratio"])
            end = start + seg_dur
            self.mission_segments.append(
                MissionSegment(
                    name=seg["name"],
                    start_sec=start,
                    end_sec=end,
                    throttle=float(seg["throttle"]),
                    engine_load=float(seg["engine_load"]),
                    altitude=float(seg["altitude"]),
                    ambient_temp=float(seg["ambient_temp"]),
                )
            )
            start = end

        if self.mission_segments:
            first = self.mission_segments[0]
            self.mode = first.name
            self.throttle = first.throttle
            self.engine_load_cmd = first.engine_load
            self.altitude = first.altitude
            self.ambient_temp = first.ambient_temp

    def _apply_mission_profile(self, dt_sec: float) -> None:
        if self.manual_override or not self.mission_segments:
            return

        self.mission_elapsed_sec += dt_sec
        current = self.mission_segments[-1]
        idx = len(self.mission_segments) - 1
        for i, seg in enumerate(self.mission_segments):
            if seg.start_sec <= self.mission_elapsed_sec < seg.end_sec:
                current = seg
                idx = i
                break

        self.mode = current.name

        # Smooth transitions
        next_seg = self.mission_segments[idx + 1] if idx + 1 < len(self.mission_segments) else None
        transition_sec = 8.0
        blend = 0.0
        if next_seg is not None and current.end_sec - transition_sec <= self.mission_elapsed_sec <= current.end_sec:
            blend = (self.mission_elapsed_sec - (current.end_sec - transition_sec)) / transition_sec

        if next_seg is not None and blend > 0:
            self.throttle = (1 - blend) * current.throttle + blend * next_seg.throttle
            self.engine_load_cmd = (1 - blend) * current.engine_load + blend * next_seg.engine_load
            self.altitude = (1 - blend) * current.altitude + blend * next_seg.altitude
            self.ambient_temp = (1 - blend) * current.ambient_temp + blend * next_seg.ambient_temp
        else:
            self.throttle = current.throttle
            self.engine_load_cmd = current.engine_load
            self.altitude = current.altitude
            self.ambient_temp = current.ambient_temp

        # Mission-derived airspeed profile (prototype)
        self.airspeed = self._clamp(10.0 + 62.0 * self.throttle + 8.0 * (self.mode in {"cruise", "high_load", "climb"}), 0.0, 110.0)

    def inject_fault(self, fault_type: str, severity: float, progression_per_sec: float, sensor_name: Optional[str] = None) -> None:
        self.fault_manager.inject(fault_type, severity, progression_per_sec, sensor_name)

    def clear_fault(self, fault_type: str) -> None:
        self.fault_manager.clear(fault_type)

    def clear_all_faults(self) -> None:
        self.fault_manager.clear_all()

    def get_faults(self) -> Dict[str, dict]:
        return self.fault_manager.snapshot()

    def _first_order(self, current: float, target: float, dt_sec: float, tau: float, sigma: float) -> float:
        alpha = self._clamp(dt_sec / max(tau, 0.05), 0.0, 1.0)
        return current + alpha * (target - current) + float(self.rng.normal(0.0, sigma))

    def step(self, dt_sec: float = 1.0) -> TelemetryPoint:
        self._apply_mission_profile(dt_sec)
        self.time_sec += dt_sec

        infl = self.fault_manager.update(dt_sec)

        # Environment
        env = self.environment.compute(self.altitude, self.ambient_temp)
        self.true.pressure_kpa = env.pressure_kpa
        self.true.density_ratio = env.density_ratio
        self.true.airspeed_mps = self.airspeed

        # Progressive base wear
        wear_increment = dt_sec * (0.000002 + 0.000012 * (0.45 * self.throttle + 0.55 * self.engine_load_cmd))
        self.base_degradation = self._clamp(self.base_degradation + wear_increment, 0.0, 0.30)

        # Manifold and airflow
        mp_target = self.manifold.compute(
            throttle=self.throttle,
            rpm=self.true.rpm,
            pressure_kpa=env.pressure_kpa,
            engine_load=self.true.propeller_load,
            intake_health=self.subsystem_health.combustion,
        )
        self.true.manifold_pressure_kpa = self._first_order(self.true.manifold_pressure_kpa, mp_target, dt_sec, tau=1.2, sigma=0.25)

        air_mdot = self.airflow.compute(
            rpm=self.true.rpm,
            manifold_pressure_kpa=self.true.manifold_pressure_kpa,
            ambient_pressure_kpa=env.pressure_kpa,
            density_kg_m3=env.density_kg_m3,
            throttle=self.throttle,
            combustion_health=self.subsystem_health.combustion,
        )
        self.true.air_mass_flow_kg_s = self._first_order(self.true.air_mass_flow_kg_s, air_mdot, dt_sec, tau=0.9, sigma=0.002)

        # Propeller demand and load
        prop_health = self.subsystem_health.mechanical * infl.propeller_health_mult
        load_target = self.propeller.compute_load(
            rpm=self.true.rpm,
            airspeed_mps=self.airspeed,
            density_ratio=env.density_ratio,
            pilot_load_command=self.engine_load_cmd,
            prop_health=prop_health,
        )
        self.true.propeller_load = self._first_order(self.true.propeller_load, load_target, dt_sec, tau=1.0, sigma=0.004)

        # Injection timing target
        inj_target = 14.0 + 12.0 * self.throttle + 2.0 * self.true.propeller_load - 0.0002 * self.altitude
        self.true.injection_timing_deg = self._first_order(self.true.injection_timing_deg, inj_target, dt_sec, tau=2.0, sigma=0.03)

        # Performance-map sampling around current operating point
        perf = self.map.sample(self.true.rpm, self.true.propeller_load, env.density_ratio)

        # Combustion / torque / power
        comb = self.combustion.compute(
            rpm=self.true.rpm,
            load=self.true.propeller_load,
            air_mass_flow_kg_s=self.true.air_mass_flow_kg_s,
            injection_timing_deg=self.true.injection_timing_deg,
            perf=perf,
            combustion_health=self.subsystem_health.combustion,
            fuel_health=self.subsystem_health.fuel,
            fault_fuel_mult=infl.fuel_delivery_mult,
            fault_combustion_mult=infl.combustion_eff_mult,
            throttle=self.throttle,
        )

        # Mechanical response
        mech_eff = self.subsystem_health.mechanical * (1.0 - 0.4 * self.base_degradation)
        mech_eff = self._clamp(mech_eff, 0.45, 1.0)
        damping = 0.030 + 0.022 * self.true.propeller_load + infl.extra_rpm_damping
        rpm_drive = (comb.torque_nm * mech_eff) - 95.0 * self.true.propeller_load
        rpm_target = self._clamp(800.0 + 14.0 * rpm_drive - 420.0 * damping, 0.0, 3300.0)

        if self.mode == "shutdown" or self.throttle <= 0.01:
            rpm_target = 0.0

        rpm_noise = 6.0 + 20.0 * infl.instability
        self.true.rpm = self._first_order(self.true.rpm, rpm_target, dt_sec, tau=1.35, sigma=rpm_noise)
        if self.mode == "shutdown" and self.true.rpm < 35.0:
            self.true.rpm = max(0.0, self.true.rpm)

        self.true.torque_nm = self._first_order(self.true.torque_nm, comb.torque_nm, dt_sec, tau=1.1, sigma=1.0 + 2.0 * infl.instability)
        self.true.power_kw = max(0.0, self.true.torque_nm * self.true.rpm / 9550.0)

        # Thermal and lubrication coupling
        friction_heat = self.lubrication.friction_heat_factor(oil_pressure=self.true.oil_pressure, lubrication_health=self.subsystem_health.lubrication)
        th_out = self.thermal.targets(
            ambient_temp_c=self.ambient_temp,
            egt_base_c=comb.egt_base_c,
            engine_load=self.true.propeller_load,
            rpm=self.true.rpm,
            thermal_health=self.subsystem_health.thermal,
            friction_heat=friction_heat,
            fault_thermal_mult=infl.thermal_release_mult,
        )

        self.true.egt_c = self.thermal.update_with_noise(self.true.egt_c, th_out.egt_target_c, dt_sec, 2.1, 1.4 + 2.6 * infl.instability, self.rng)
        self.true.cht_c = self.thermal.update_with_noise(self.true.cht_c, th_out.cht_target_c, dt_sec, 7.6, 0.65 + 1.0 * infl.instability, self.rng)
        self.true.oil_temp_c = self.thermal.update_with_noise(self.true.oil_temp_c, th_out.oil_temp_target_c, dt_sec, 8.8, 0.38 + 0.7 * infl.instability, self.rng)

        oil_p_target = self.lubrication.oil_pressure_target(
            rpm=self.true.rpm,
            oil_temp_c=self.true.oil_temp_c,
            lubrication_health=self.subsystem_health.lubrication,
            fault_lubrication_mult=infl.lubrication_mult,
        )
        self.true.oil_pressure = self._first_order(self.true.oil_pressure, oil_p_target, dt_sec, tau=2.8, sigma=0.55 + 0.6 * infl.instability)

        # Vibration from map + instability + degradation
        vib_target = (
            perf.vibration
            + 0.11 * self.true.propeller_load
            + 0.22 * (1.0 - self.subsystem_health.mechanical)
            + 0.18 * infl.instability
            + 0.00009 * max(self.true.rpm - 1800.0, 0.0)
        )
        self.true.vibration = self._first_order(self.true.vibration, vib_target, dt_sec, tau=1.5, sigma=0.010 + 0.03 * infl.instability)

        # Electrical model
        alt_health = self.electrical.alternator_health(
            electrical_health=self.subsystem_health.electrical,
            base_degradation=self.base_degradation,
            fault_electrical_mult=infl.electrical_output_mult,
        )
        self.true.alternator_health = alt_health
        batt_target = self.electrical.battery_target(
            rpm=self.true.rpm,
            alternator_health=self.true.alternator_health,
            engine_load=self.true.propeller_load,
            battery_bias=infl.battery_bias,
        )
        self.true.battery_voltage = self._first_order(self.true.battery_voltage, batt_target, dt_sec, tau=2.0, sigma=0.03 + 0.05 * infl.instability)

        # Fuel flow and global efficiency
        self.true.fuel_flow_lph = self._first_order(self.true.fuel_flow_lph, comb.fuel_flow_lph, dt_sec, tau=1.0, sigma=0.18 + 0.22 * infl.instability)
        self.true.engine_efficiency = self._clamp(
            comb.combustion_efficiency * self.subsystem_health.overall,
            0.45,
            0.99,
        )

        # Subsystem degradation update (persistent state)
        self.degradation.update(
            health=self.subsystem_health,
            dt_sec=dt_sec,
            engine_load=self.true.propeller_load,
            egt_c=self.true.egt_c,
            cht_c=self.true.cht_c,
            oil_temp_c=self.true.oil_temp_c,
            oil_pressure=self.true.oil_pressure,
            vibration=self.true.vibration,
            fault_stress=infl.fault_stress,
        )

        # Sensor observation layer
        obs = self.sensor_model.observe(self.true, self.rng, infl.instability)

        values = {
            "rpm": obs.rpm,
            "manifold_pressure": obs.manifold_pressure_kpa,
            "air_mass_flow": obs.air_mass_flow_kg_s,
            "fuel_flow": obs.fuel_flow_lph,
            "egt": obs.egt_c,
            "cht": obs.cht_c,
            "oil_temp": obs.oil_temp_c,
            "oil_pressure": obs.oil_pressure,
            "vibration": obs.vibration,
            "battery_voltage": obs.battery_voltage,
            "alternator_health": obs.alternator_health,
            "injection_timing": obs.injection_timing_deg,
            "torque_nm": obs.torque_nm,
            "power_kw": obs.power_kw,
            "propeller_load": obs.propeller_load,
            "pressure_kpa": obs.pressure_kpa,
            "density_ratio": obs.density_ratio,
            "airspeed": obs.airspeed_mps,
        }

        values = self.fault_manager.apply_sensor_effects(values)

        return TelemetryPoint(
            timestamp=datetime.utcnow(),
            mode=self.mode,
            rpm=float(self._clamp(values["rpm"], 0.0, 3600.0)),
            cht=float(self._clamp(values["cht"], -20.0, 420.0)),
            egt=float(self._clamp(values["egt"], 0.0, 1200.0)),
            oil_pressure=float(self._clamp(values["oil_pressure"], 0.0, 150.0)),
            oil_temp=float(self._clamp(values["oil_temp"], -30.0, 250.0)),
            fuel_flow=float(self._clamp(values["fuel_flow"], 0.0, 180.0)),
            vibration=float(self._clamp(values["vibration"], 0.0, 7.0)),
            battery_voltage=float(self._clamp(values["battery_voltage"], 0.0, 18.0)),
            alternator_health=float(self._clamp(values["alternator_health"], 0.0, 1.1)),
            injection_timing=float(self._clamp(values["injection_timing"], 0.0, 45.0)),
            throttle=float(self.throttle),
            engine_load=float(self._clamp(values["propeller_load"], 0.0, 1.0)),
            altitude=float(self.altitude),
            ambient_temp=float(self.ambient_temp),
            engine_efficiency=float(self._clamp(self.true.engine_efficiency, 0.0, 1.0)),
            manifold_pressure=float(self._clamp(values["manifold_pressure"], 0.0, 120.0)),
            air_mass_flow=float(self._clamp(values["air_mass_flow"], 0.0, 3.0)),
            torque_nm=float(max(0.0, values["torque_nm"])),
            power_kw=float(max(0.0, values["power_kw"])),
            propeller_load=float(self._clamp(values["propeller_load"], 0.0, 1.0)),
            airspeed=float(self._clamp(values["airspeed"], 0.0, 130.0)),
            pressure_kpa=float(self._clamp(values["pressure_kpa"], 20.0, 110.0)),
            density_ratio=float(self._clamp(values["density_ratio"], 0.4, 1.2)),
            subsystem_health={
                "combustion": self.subsystem_health.combustion,
                "thermal": self.subsystem_health.thermal,
                "lubrication": self.subsystem_health.lubrication,
                "mechanical": self.subsystem_health.mechanical,
                "fuel": self.subsystem_health.fuel,
                "electrical": self.subsystem_health.electrical,
                "overall": self.subsystem_health.overall,
            },
            true_state={
                "rpm": self.true.rpm,
                "egt": self.true.egt_c,
                "cht": self.true.cht_c,
                "oil_pressure": self.true.oil_pressure,
                "oil_temp": self.true.oil_temp_c,
                "fuel_flow": self.true.fuel_flow_lph,
                "vibration": self.true.vibration,
                "battery_voltage": self.true.battery_voltage,
                "manifold_pressure": self.true.manifold_pressure_kpa,
                "air_mass_flow": self.true.air_mass_flow_kg_s,
                "torque_nm": self.true.torque_nm,
                "power_kw": self.true.power_kw,
            },
        )
