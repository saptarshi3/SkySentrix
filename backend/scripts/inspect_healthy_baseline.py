"""Diagnostic-only: measure baseline (fault-free) rpm_instability and fuel_flow
residual levels so diagnosis thresholds can subtract a real baseline instead
of guessing one.
"""
from __future__ import annotations

import sys
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pipeline import DigitalTwinPipeline  # noqa: E402
from scripts.trajectory_utils import PRESETS, run_healthy_trajectory  # noqa: E402


def main() -> None:
    pipeline = DigitalTwinPipeline()
    for preset in PRESETS:
        frames = run_healthy_trajectory(pipeline, preset, seed=900, duration_sec=180)
        window = frames[60:]
        rpm_inst = mean(f.diagnosis.evidence.get("rpm_instability_pct", 0.0) for f in window)
        fuel_neg = mean(max(0.0, -f.residuals["fuel_flow"].residual_pct) for f in window)
        fuel_pos = mean(max(0.0, f.residuals["fuel_flow"].residual_pct) for f in window)
        egt_pos = mean(max(0.0, f.residuals["egt"].residual_pct) for f in window)
        cht_pos = mean(max(0.0, f.residuals["cht"].residual_pct) for f in window)
        oil_temp_pos = mean(max(0.0, f.residuals["oil_temp"].residual_pct) for f in window)
        oil_pressure_neg = mean(max(0.0, -f.residuals["oil_pressure"].residual_pct) for f in window)
        manifold_pos = mean(max(0.0, f.residuals["manifold_pressure"].residual_pct) for f in window)
        vibration_pos = mean(max(0.0, f.residuals["vibration"].residual_pct) for f in window)
        battery_neg = mean(max(0.0, -f.residuals["battery_voltage"].residual_pct) for f in window)
        print(
            f"{preset:28s} rpm_inst={rpm_inst:7.2f} fuel_neg={fuel_neg:7.2f} fuel_pos={fuel_pos:6.2f} "
            f"egt_pos={egt_pos:6.2f} cht_pos={cht_pos:6.2f} oil_temp_pos={oil_temp_pos:6.2f} "
            f"oil_pressure_neg={oil_pressure_neg:6.2f} manifold_pos={manifold_pos:6.2f} "
            f"vibration_pos={vibration_pos:6.2f} battery_neg={battery_neg:6.2f}"
        )


if __name__ == "__main__":
    main()
