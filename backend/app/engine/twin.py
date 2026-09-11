from __future__ import annotations

from typing import Dict

from app.engine.environment import EnvironmentModel
from app.engine.performance_map import PerformanceMap
from app.models.schemas import EstimatedState, ExpectedState, ResidualEntry, TelemetryPoint


class DigitalTwinModel:
    """
    Independent healthy baseline twin (not identical to simulator equations).
    """

    def __init__(self) -> None:
        self.environment = EnvironmentModel()
        self.map = PerformanceMap()

        self.expected_state: Dict[str, float] = {
            "rpm": 900.0,
            "cht": 115.0,
            "egt": 560.0,
            "oil_pressure": 35.0,
            "oil_temp": 75.0,
            "fuel_flow": 9.0,
            "vibration": 0.20,
            "battery_voltage": 12.8,
            "manifold_pressure": 45.0,
            "air_mass_flow": 0.09,
            "torque_nm": 110.0,
            "power_kw": 18.0,
            "propeller_load": 0.25,
        }

    @staticmethod
    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))

    def predict(self, telemetry: TelemetryPoint, estimated: EstimatedState, dt_sec: float = 1.0) -> ExpectedState:
        throttle = telemetry.throttle
        load = telemetry.engine_load
        altitude = telemetry.altitude
        ambient = telemetry.ambient_temp

        env = self.environment.compute(altitude, ambient)
        density = env.density_ratio

        # Healthy expected efficiency and load response (independent baseline model)
        expected_eff = self._clamp(
            0.94 - 0.0000018 * altitude - 0.0007 * max(ambient - 30.0, 0.0),
            0.78,
            0.98,
        )

        # Twin uses commanded/load context and estimator states for consistency,
        # but assumes healthy subsystem response.
        rpm_context = 0.6 * estimated.rpm + 0.4 * self.expected_state["rpm"]
        perf = self.map.sample(rpm_context, load, density)

        manifold_target = (20.0 + 78.0 * throttle) * (env.pressure_kpa / 101.325) - 0.0028 * max(rpm_context - 1800.0, 0.0)
        manifold_target = self._clamp(manifold_target, 12.0, env.pressure_kpa * 1.04)

        air_mass_target = (0.0036 * max(rpm_context, 0.0) / 120.0) * env.density_kg_m3 * self._clamp(0.62 + 0.30 * throttle, 0.45, 1.05)

        torque_target = perf.torque_nm * (0.94 + 0.06 * throttle)
        power_target = torque_target * max(rpm_context, 0.0) / 9550.0

        rpm_target = (720.0 + 2400.0 * (throttle ** 1.35) - 280.0 * load) * (0.89 + 0.11 * density)
        fuel_target = perf.fuel_flow_lph / max(expected_eff, 0.65)

        egt_target = perf.egt_c + 88.0 * (1.0 - expected_eff) + 14.0 * load
        cht_target = ambient + 58.0 + 0.155 * max(egt_target - 500.0, 0.0) + 44.0 * load
        oil_temp_target = ambient + 39.0 + 0.071 * max(egt_target - 500.0, 0.0) + 13.0 * load
        oil_pressure_target = 20.0 + 0.018 * max(self.expected_state["rpm"], 0.0) - 0.12 * max(self.expected_state["oil_temp"] - 88.0, 0.0)
        vibration_target = perf.vibration + 0.08 * load + 0.00007 * max(self.expected_state["rpm"] - 1800.0, 0.0)

        electrical_load = 0.25 + 0.50 * load
        battery_target = 12.2 + (1.75 if self.expected_state["rpm"] > 1200 else 0.45) * 0.98 - 0.42 * electrical_load

        targets = {
            "rpm": rpm_target,
            "cht": cht_target,
            "egt": egt_target,
            "oil_pressure": oil_pressure_target,
            "oil_temp": oil_temp_target,
            "fuel_flow": fuel_target,
            "vibration": vibration_target,
            "battery_voltage": battery_target,
            "manifold_pressure": manifold_target,
            "air_mass_flow": air_mass_target,
            "torque_nm": torque_target,
            "power_kw": power_target,
            "propeller_load": load,
        }

        taus = {
            "rpm": 1.5,
            "fuel_flow": 1.2,
            "egt": 2.4,
            "cht": 8.5,
            "oil_temp": 9.0,
            "oil_pressure": 3.1,
            "vibration": 1.8,
            "battery_voltage": 2.2,
            "manifold_pressure": 1.2,
            "air_mass_flow": 1.0,
            "torque_nm": 1.3,
            "power_kw": 1.2,
            "propeller_load": 1.0,
        }

        for k, tgt in targets.items():
            alpha = self._clamp(dt_sec / max(taus[k], 0.1), 0.0, 1.0)
            self.expected_state[k] = self.expected_state[k] + alpha * (tgt - self.expected_state[k])

        self.expected_state["rpm"] = self._clamp(self.expected_state["rpm"], 0.0, 3600.0)
        self.expected_state["cht"] = self._clamp(self.expected_state["cht"], -20.0, 420.0)
        self.expected_state["egt"] = self._clamp(self.expected_state["egt"], 0.0, 1200.0)
        self.expected_state["oil_pressure"] = self._clamp(self.expected_state["oil_pressure"], 0.0, 150.0)
        self.expected_state["oil_temp"] = self._clamp(self.expected_state["oil_temp"], -20.0, 250.0)
        self.expected_state["fuel_flow"] = self._clamp(self.expected_state["fuel_flow"], 0.0, 180.0)
        self.expected_state["vibration"] = self._clamp(self.expected_state["vibration"], 0.0, 7.0)
        self.expected_state["battery_voltage"] = self._clamp(self.expected_state["battery_voltage"], 0.0, 18.0)
        self.expected_state["manifold_pressure"] = self._clamp(self.expected_state["manifold_pressure"], 0.0, 120.0)
        self.expected_state["air_mass_flow"] = self._clamp(self.expected_state["air_mass_flow"], 0.0, 3.0)
        self.expected_state["torque_nm"] = self._clamp(self.expected_state["torque_nm"], 0.0, 600.0)
        self.expected_state["power_kw"] = self._clamp(self.expected_state["power_kw"], 0.0, 300.0)
        self.expected_state["propeller_load"] = self._clamp(self.expected_state["propeller_load"], 0.0, 1.0)

        return ExpectedState(**self.expected_state)


def compute_residuals(estimated: EstimatedState, expected: ExpectedState) -> Dict[str, ResidualEntry]:
    fields = [
        "rpm",
        "cht",
        "egt",
        "oil_pressure",
        "oil_temp",
        "fuel_flow",
        "vibration",
        "battery_voltage",
        "manifold_pressure",
        "air_mass_flow",
        "torque_nm",
        "power_kw",
        "propeller_load",
    ]

    residuals: Dict[str, ResidualEntry] = {}
    for field in fields:
        actual = float(getattr(estimated, field))
        exp = float(getattr(expected, field))
        residual = actual - exp
        denom = max(abs(exp), 1e-4)
        residual_pct = (residual / denom) * 100.0
        residuals[field] = ResidualEntry(
            actual=actual,
            expected=exp,
            residual=residual,
            residual_pct=residual_pct,
        )

    return residuals
