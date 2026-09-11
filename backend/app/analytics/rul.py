from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque

import numpy as np

from app.config import RuntimeConfig
from app.models.schemas import HealthResult, RULResult


@dataclass
class TrajectoryPoint:
    t_hours: float
    degradation: float


class RULEstimator:
    """
    Sequential synthetic RUL estimator.

    Uses persistent degradation trajectory + effective wear-rate fusion:
    - health-derived degradation rate
    - trajectory slope over recent window
    - anomaly/diagnosis acceleration factors

    Outputs uncertainty interval from recent rate variability.
    """

    def __init__(self, config: RuntimeConfig | None = None) -> None:
        self.config = config or RuntimeConfig()
        self.initial_rul_hours = float(self.config.initial_rul_hours)
        self.failure_degradation_threshold = 100.0 - float(self.config.failure_health_threshold)

        self.elapsed_hours = 0.0
        self.rate_ewma = 0.17
        self.rul_history: Deque[float] = deque(maxlen=120)
        self.rate_history: Deque[float] = deque(maxlen=120)
        self.degradation_history: Deque[TrajectoryPoint] = deque(maxlen=240)

    @staticmethod
    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))

    def reset_state(self) -> None:
        self.elapsed_hours = 0.0
        self.rate_ewma = 0.17
        self.rul_history.clear()
        self.rate_history.clear()
        self.degradation_history.clear()

    def _trajectory_rate(self) -> float:
        if len(self.degradation_history) < 8:
            return 0.0

        recent = list(self.degradation_history)[-36:]
        t = np.array([p.t_hours for p in recent], dtype=float)
        d = np.array([p.degradation for p in recent], dtype=float)
        t = t - float(t[0])

        span_h = float(t[-1])
        if span_h <= 0.03:
            return 0.0

        # Linear trend over recent degradation trajectory
        slope, _ = np.polyfit(t, d, 1)
        return self._clamp(float(slope), 0.0, 6.0)

    def _trend_label(self, current_rul: float) -> str:
        self.rul_history.append(current_rul)
        if len(self.rul_history) < 8:
            return "stable"

        delta = self.rul_history[-1] - self.rul_history[-8]
        if delta < -24.0:
            return "decreasing_fast"
        if delta < -7.0:
            return "decreasing"
        if delta > 7.0:
            return "improving"
        return "stable"

    def update(
        self,
        health: HealthResult,
        anomaly_score: float,
        diagnosis_confidence: float = 0.0,
        dt_sec: float = 1.0,
    ) -> RULResult:
        dt_h = self._clamp(dt_sec / 3600.0, 1e-6, 5.0 / 3600.0)
        self.elapsed_hours += dt_h

        current_deg = self._clamp(float(health.degradation_index), 0.0, 100.0)
        self.degradation_history.append(TrajectoryPoint(self.elapsed_hours, current_deg))

        if health.state == "HEALTHY":
            base_rate = 0.17
            fused_rate = 0.17
            self.rate_ewma = 0.17
            degradation_remaining = max(0.0, self.failure_degradation_threshold - current_deg)
            current_rul = degradation_remaining / base_rate - self.elapsed_hours
            current_rul = self._clamp(current_rul, 0.0, self.initial_rul_hours * 1.35)
        else:
            base_rate = max(0.17, float(health.degradation_rate_per_hour))
            anomaly_factor = 1.0 + 0.80 * max(0.0, anomaly_score - 0.35)
            diagnosis_factor = 1.0 + 0.35 * max(0.0, diagnosis_confidence - 0.65)
            state_factor = {
                "DEGRADING": 1.10,
                "WARNING": 1.28,
                "CRITICAL": 1.55,
            }.get(health.state, 1.0)

            effective_inst_rate = base_rate * anomaly_factor * diagnosis_factor * state_factor
            effective_inst_rate = self._clamp(effective_inst_rate, 0.02, 4.0)

            ewma_alpha = 0.08 if dt_h < 0.001 else 0.12
            self.rate_ewma = (1.0 - ewma_alpha) * self.rate_ewma + ewma_alpha * effective_inst_rate

            traj_rate = self._trajectory_rate()
            if traj_rate <= 0.0:
                fused_rate = self.rate_ewma
            else:
                fused_rate = 0.72 * self.rate_ewma + 0.28 * traj_rate
            fused_rate = self._clamp(fused_rate, 0.03, 6.0)

            degradation_remaining = max(0.0, self.failure_degradation_threshold - current_deg)
            current_rul = degradation_remaining / max(fused_rate, 1e-6)
            current_rul = self._clamp(current_rul, 0.0, self.initial_rul_hours * 1.35)

        self.rate_history.append(fused_rate)

        if len(self.rate_history) >= 8:
            rates = np.array(list(self.rate_history)[-32:], dtype=float)
            mean_r = float(np.mean(rates))
            std_r = float(np.std(rates))
            rel_unc = std_r / max(mean_r, 1e-6)
        else:
            rel_unc = 0.22

        rel_unc += 0.18 * max(0.0, anomaly_score - 0.45)
        if health.state == "WARNING":
            rel_unc += 0.05
        elif health.state == "CRITICAL":
            rel_unc += 0.10

        rel_unc = self._clamp(rel_unc, 0.10, 0.70)

        rate_low = max(0.02, fused_rate * (1.0 - rel_unc))
        rate_high = fused_rate * (1.0 + rel_unc)
        confidence_high = self._clamp(degradation_remaining / rate_low, 0.0, self.initial_rul_hours * 1.6)
        confidence_low = self._clamp(degradation_remaining / max(rate_high, 1e-6), 0.0, self.initial_rul_hours * 1.6)

        trend = self._trend_label(current_rul)

        return RULResult(
            initial_rul_hours=round(self.initial_rul_hours, 3),
            current_rul_hours=round(current_rul, 3),
            degradation_rate_per_hour=round(fused_rate, 5),
            trend=trend,
            confidence_low_hours=round(min(confidence_low, confidence_high), 3),
            confidence_high_hours=round(max(confidence_low, confidence_high), 3),
            note=(
                "Prototype sequential RUL estimate from synthetic degradation trajectory; "
                "not flight-certified and not based on real engine run-to-failure data."
            ),
        )
