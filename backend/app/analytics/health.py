from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime
from typing import Deque, Dict, Tuple

from app.models.schemas import AnomalyResult, DiagnosisResult, HealthResult, ResidualEntry, TelemetryPoint


class HealthEngine:
    def __init__(self) -> None:
        self.health_index = 100.0
        self.degradation_index = 0.0
        self.history: Deque[Tuple[datetime, float]] = deque(maxlen=2000)
        self.persistence: Dict[str, float] = defaultdict(float)
        self.rate_ewma = 0.170

    @staticmethod
    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))

    def reset_state(self) -> None:
        self.health_index = 100.0
        self.degradation_index = 0.0
        self.history.clear()
        self.persistence.clear()
        self.rate_ewma = 0.170

    def update(
        self,
        telemetry: TelemetryPoint,
        residuals: Dict[str, ResidualEntry],
        anomaly: AnomalyResult,
        diagnosis: DiagnosisResult,
        dt_sec: float = 1.0,
    ) -> HealthResult:
        thresholds = {
            "egt": 12.0,
            "cht": 10.0,
            "oil_pressure": 12.0,
            "oil_temp": 10.0,
            "vibration": 20.0,
            "fuel_flow": 15.0,
            "rpm": 10.0,
            "battery_voltage": 4.0,
            "manifold_pressure": 10.0,
        }

        for key, threshold in thresholds.items():
            val = abs(residuals[key].residual_pct)
            if val > threshold:
                self.persistence[key] = min(1.0, self.persistence[key] + 0.04)
            else:
                self.persistence[key] = max(0.0, self.persistence[key] - 0.02)

        persistent_score = (
            0.18 * self.persistence["egt"]
            + 0.15 * self.persistence["cht"]
            + 0.15 * self.persistence["oil_pressure"]
            + 0.11 * self.persistence["oil_temp"]
            + 0.14 * self.persistence["vibration"]
            + 0.10 * self.persistence["fuel_flow"]
            + 0.07 * self.persistence["rpm"]
            + 0.10 * self.persistence["manifold_pressure"]
        )

        ss = telemetry.subsystem_health or {}
        subsystem = {
            "combustion": float(ss.get("combustion", telemetry.engine_efficiency)),
            "thermal": float(ss.get("thermal", telemetry.engine_efficiency)),
            "lubrication": float(ss.get("lubrication", telemetry.engine_efficiency)),
            "mechanical": float(ss.get("mechanical", telemetry.engine_efficiency)),
            "fuel": float(ss.get("fuel", telemetry.engine_efficiency)),
            "electrical": float(ss.get("electrical", telemetry.alternator_health)),
        }
        for k in subsystem:
            subsystem[k] = self._clamp(subsystem[k], 0.0, 1.0)

        subsystem_health_score = (
            0.22 * subsystem["combustion"]
            + 0.18 * subsystem["thermal"]
            + 0.18 * subsystem["lubrication"]
            + 0.17 * subsystem["mechanical"]
            + 0.13 * subsystem["fuel"]
            + 0.12 * subsystem["electrical"]
        )

        # Confirmed active fault requires confirmed model diagnosis (confidence >= 0.40),
        # or diagnosis with warning anomaly, or sustained critical anomaly
        is_confirmed_fault = (
            (diagnosis.probable_fault != "normal" and diagnosis.confidence >= 0.40)
            or (anomaly.level in ("WARNING", "CRITICAL") and diagnosis.probable_fault != "normal")
            or (anomaly.level == "CRITICAL")
        )

        if not is_confirmed_fault:
            # Nominal operating wear: degradation proceeds at nominal flight-hour burn rate
            # (0.170% / hour = 0.0000472% / sec)
            instant_damage = 0.170 / 3600.0
            recovery = 0.0
        else:
            temp_abnormal = max(0.0, residuals["egt"].residual_pct - 12.0) * 0.06 + max(0.0, residuals["cht"].residual_pct - 10.0) * 0.05
            oil_abnormal = max(0.0, -residuals["oil_pressure"].residual_pct - 12.0) * 0.085 + max(0.0, residuals["oil_temp"].residual_pct - 10.0) * 0.06
            vib_abnormal = max(0.0, residuals["vibration"].residual_pct - 20.0) * 0.05
            anomaly_component = max(0.0, anomaly.score - 0.35) * 1.5
            diagnosis_component = (diagnosis.confidence * 1.2) if diagnosis.probable_fault != "normal" else 0.0
            subsystem_damage = max(0.0, 1.0 - subsystem_health_score) * 2.2

            fault_damage = (
                1.3 * max(0.0, persistent_score - 0.4)
                + temp_abnormal
                + oil_abnormal
                + vib_abnormal
                + anomaly_component
                + diagnosis_component
                + subsystem_damage
            ) * 0.05

            instant_damage = (0.170 / 3600.0) + fault_damage
            recovery = 0.0

        self.health_index = self._clamp(self.health_index - instant_damage * dt_sec + recovery * dt_sec, 0.0, 100.0)
        self.degradation_index = self._clamp(100.0 - self.health_index, 0.0, 100.0)

        now = telemetry.timestamp
        self.history.append((now, self.degradation_index))

        degradation_rate_per_hour = self.rate_ewma
        if len(self.history) >= 2:
            t0, d0 = self.history[0]
            t1, d1 = self.history[-1]
            dt_hours = max((t1 - t0).total_seconds() / 3600.0, 1e-6)
            if dt_hours >= 0.05:
                raw_rate = max(0.0, (d1 - d0) / dt_hours)
                raw_rate = self._clamp(raw_rate, 0.0, 8.0)
                self.rate_ewma = 0.88 * self.rate_ewma + 0.12 * raw_rate
            degradation_rate_per_hour = self.rate_ewma

        if is_confirmed_fault:
            state = "CRITICAL" if anomaly.level == "CRITICAL" or self.health_index < 55 else "WARNING"
        elif self.health_index >= 90:
            state = "HEALTHY"
        elif self.health_index >= 75:
            state = "DEGRADING"
        elif self.health_index >= 55:
            state = "WARNING"
        else:
            state = "CRITICAL"

        return HealthResult(
            health_index=round(self.health_index, 3),
            degradation_index=round(self.degradation_index, 3),
            degradation_rate_per_hour=round(degradation_rate_per_hour, 5),
            subsystem_health={
                **{k: round(v * 100.0, 2) for k, v in subsystem.items()},
                "overall": round(subsystem_health_score * 100.0, 2),
            },
            state=state,
        )
