"""Diagnostic-only: recompute the diagnosis best_score distribution on healthy
trajectories (post baseline-correction) to calibrate the 'normal' cutoff.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.analytics.diagnosis import (  # noqa: E402
    BASELINE_BATTERY_NEG_PCT,
    BASELINE_CHT_POS_PCT,
    BASELINE_EGT_POS_PCT,
    BASELINE_FUEL_FLOW_SIGNED_PCT,
    BASELINE_MANIFOLD_POS_PCT,
    BASELINE_OIL_PRESSURE_NEG_PCT,
    BASELINE_OIL_TEMP_POS_PCT,
    BASELINE_RPM_INSTABILITY_PCT,
    BASELINE_VIBRATION_POS_PCT,
    DiagnosisEngine,
)
from app.services.pipeline import DigitalTwinPipeline  # noqa: E402
from scripts.trajectory_utils import PRESETS, run_healthy_trajectory  # noqa: E402


def compute_best_score(engine: DiagnosisEngine, telemetry, residuals, anomaly) -> float:
    engine.rpm_history.append(telemetry.rpm)
    engine.egt_history.append(telemetry.egt)
    rpm_instability_raw = engine._rpm_instability_pct()
    egt_instability = engine._egt_instability()

    egt_pos = max(0.0, max(0.0, residuals["egt"].residual_pct) - BASELINE_EGT_POS_PCT)
    cht_pos = max(0.0, max(0.0, residuals["cht"].residual_pct) - BASELINE_CHT_POS_PCT)
    oil_temp_pos = max(0.0, max(0.0, residuals["oil_temp"].residual_pct) - BASELINE_OIL_TEMP_POS_PCT)
    oil_pressure_neg = max(0.0, max(0.0, -residuals["oil_pressure"].residual_pct) - BASELINE_OIL_PRESSURE_NEG_PCT)
    manifold_pos = max(0.0, max(0.0, residuals["manifold_pressure"].residual_pct) - BASELINE_MANIFOLD_POS_PCT)
    vibration_pos = max(0.0, max(0.0, residuals["vibration"].residual_pct) - BASELINE_VIBRATION_POS_PCT)
    battery_neg = max(0.0, max(0.0, -residuals["battery_voltage"].residual_pct) - BASELINE_BATTERY_NEG_PCT)
    rpm_instability = max(0.0, rpm_instability_raw - BASELINE_RPM_INSTABILITY_PCT)

    fuel_flow_signed_excess = residuals["fuel_flow"].residual_pct - BASELINE_FUEL_FLOW_SIGNED_PCT
    fuel_flow_pos = max(0.0, fuel_flow_signed_excess)
    fuel_flow_neg = max(0.0, -fuel_flow_signed_excess)

    rpm_abs = abs(residuals["rpm"].residual_pct)
    eff_loss = max(0.0, (0.93 - telemetry.engine_efficiency) * 100.0)
    ambient_hot = max(0.0, telemetry.ambient_temp - 32.0)

    scores = {
        "injector_degradation": 1.2 * egt_pos + 1.4 * fuel_flow_pos + 0.8 * manifold_pos + 2.2 * rpm_instability + 0.45 * eff_loss,
        "misfire": 1.0 * rpm_abs + 4.8 * rpm_instability + 1.1 * vibration_pos + 0.18 * egt_instability,
        "lubrication_problem": 1.4 * oil_pressure_neg + 0.9 * oil_temp_pos + 0.75 * vibration_pos,
        "overheating": 1.1 * cht_pos + 0.8 * egt_pos + 1.0 * oil_temp_pos + 0.22 * ambient_hot,
        "excessive_vibration": 1.5 * vibration_pos + 5.8 * rpm_instability,
        "combustion_instability": 1.0 * egt_instability + 2.6 * rpm_instability + 0.85 * vibration_pos,
        "fuel_system_degradation": 1.2 * fuel_flow_neg + 0.9 * manifold_pos + 0.8 * egt_pos + 0.2 * vibration_pos,
        "alternator_problem": 1.1 * battery_neg,
    }
    anomaly_weight = 0.7 + 0.6 * anomaly.score
    return max(scores.values()) * anomaly_weight


def main() -> None:
    pipeline = DigitalTwinPipeline()
    all_scores = []
    for preset in PRESETS:
        frames = run_healthy_trajectory(pipeline, preset, seed=900, duration_sec=180)
        engine = DiagnosisEngine()
        window = frames[60:]
        scores = [compute_best_score(engine, f.telemetry, f.residuals, f.anomaly) for f in window]
        all_scores.extend(scores)
        print(f"{preset:28s} mean={np.mean(scores):7.2f} p50={np.percentile(scores,50):7.2f} p90={np.percentile(scores,90):7.2f} p99={np.percentile(scores,99):7.2f} max={np.max(scores):7.2f}")

    all_scores = np.array(all_scores)
    print(f"\nOVERALL: mean={all_scores.mean():.2f} p90={np.percentile(all_scores,90):.2f} p95={np.percentile(all_scores,95):.2f} p99={np.percentile(all_scores,99):.2f} max={all_scores.max():.2f}")


if __name__ == "__main__":
    main()
