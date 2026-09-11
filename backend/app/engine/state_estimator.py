from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.models.schemas import EstimatedState, TelemetryPoint


@dataclass
class KalmanState:
    x: np.ndarray
    p: np.ndarray


class StateEstimator:
    """Linear Kalman filter over primary measured states."""

    def __init__(self) -> None:
        self.n = 8
        self.a = np.eye(self.n)
        self.h = np.eye(self.n)
        self.q = np.diag([15.0, 2.0, 0.8, 0.7, 0.9, 0.003, 0.25, 0.02])
        self.r = np.diag([35.0, 4.0, 1.2, 1.2, 1.6, 0.01, 0.55, 0.05])
        self.initialized = False
        self.state = KalmanState(x=np.zeros(self.n), p=np.eye(self.n) * 15.0)

    def reset_state(self) -> None:
        self.initialized = False
        self.state = KalmanState(x=np.zeros(self.n), p=np.eye(self.n) * 15.0)

    def _measurement_vector(self, t: TelemetryPoint) -> np.ndarray:
        return np.array(
            [
                t.rpm,
                t.egt,
                t.cht,
                t.oil_temp,
                t.oil_pressure,
                t.vibration,
                t.fuel_flow,
                t.battery_voltage,
            ],
            dtype=float,
        )

    def update(self, telemetry: TelemetryPoint, dt_sec: float) -> EstimatedState:
        z = self._measurement_vector(telemetry)

        if not self.initialized:
            self.state.x = z.copy()
            self.state.p = np.eye(self.n)
            self.initialized = True
        else:
            q = self.q * max(dt_sec, 0.2)
            x_pred = self.a @ self.state.x
            p_pred = self.a @ self.state.p @ self.a.T + q

            y = z - (self.h @ x_pred)
            s = self.h @ p_pred @ self.h.T + self.r
            k = p_pred @ self.h.T @ np.linalg.inv(s)

            self.state.x = x_pred + k @ y
            self.state.p = (np.eye(self.n) - k @ self.h) @ p_pred

        x = self.state.x

        rpm = float(x[0])
        pressure_ratio = max(0.45, 1.0 - telemetry.altitude / 15000.0)
        manifold_default = (18.0 + 80.0 * telemetry.throttle) * pressure_ratio - 0.0025 * max(rpm - 1800.0, 0.0)
        manifold_default = max(12.0, min(110.0, manifold_default))

        manifold = telemetry.manifold_pressure if telemetry.manifold_pressure > 1.0 else manifold_default
        air_mass_default = max(0.01, 0.000055 * max(rpm, 0.0) * (0.58 + 0.34 * telemetry.throttle) * pressure_ratio)
        air_mass = telemetry.air_mass_flow if telemetry.air_mass_flow > 1e-4 else air_mass_default

        torque_default = max(15.0, (42.0 + 190.0 * telemetry.engine_load) * max(0.55, telemetry.engine_efficiency))
        torque = telemetry.torque_nm if telemetry.torque_nm > 0.1 else torque_default
        power_default = max(0.0, torque * max(rpm, 0.0) / 9550.0)
        power = telemetry.power_kw if telemetry.power_kw > 0.05 else power_default

        prop_load = telemetry.propeller_load if telemetry.propeller_load > 0.0 else telemetry.engine_load

        return EstimatedState(
            rpm=rpm,
            egt=float(x[1]),
            cht=float(x[2]),
            oil_temp=float(x[3]),
            oil_pressure=float(x[4]),
            vibration=float(x[5]),
            fuel_flow=float(x[6]),
            battery_voltage=float(x[7]),
            manifold_pressure=float(manifold),
            air_mass_flow=float(air_mass),
            torque_nm=float(torque),
            power_kw=float(power),
            propeller_load=float(prop_load),
            engine_efficiency=float(telemetry.engine_efficiency),
            alternator_health=float(telemetry.alternator_health),
        )
