"""Diagnostic-only: dump average evidence/feature values per fault post-injection
so diagnosis weight recalibration is based on real data, not guesswork.
"""
from __future__ import annotations

import sys
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pipeline import DigitalTwinPipeline  # noqa: E402
from scripts.trajectory_utils import FAULT_TYPES, run_fault_trajectory  # noqa: E402

WARMUP_SEC = 60
DURATION_SEC = 180
INJECT_AT = WARMUP_SEC


def main() -> None:
    pipeline = DigitalTwinPipeline()
    fields = [
        "egt_pos", "cht_pos", "oil_temp_pos", "oil_pressure_neg", "fuel_flow_pos",
        "fuel_flow_neg", "manifold_pos", "rpm_abs", "rpm_instability", "vibration_pos",
        "battery_neg", "egt_instability",
    ]

    for i, fault_type in enumerate(FAULT_TYPES):
        seed = 700 + i
        frames, sim = run_fault_trajectory(
            pipeline, "normal_endurance", seed, DURATION_SEC, fault_type, 0.75, 0.01, INJECT_AT,
        )
        window = frames[INJECT_AT + 30:]  # steady post-injection window
        r = {
            "egt_pos": mean(max(0.0, f.residuals["egt"].residual_pct) for f in window),
            "cht_pos": mean(max(0.0, f.residuals["cht"].residual_pct) for f in window),
            "oil_temp_pos": mean(max(0.0, f.residuals["oil_temp"].residual_pct) for f in window),
            "oil_pressure_neg": mean(max(0.0, -f.residuals["oil_pressure"].residual_pct) for f in window),
            "fuel_flow_pos": mean(max(0.0, f.residuals["fuel_flow"].residual_pct) for f in window),
            "fuel_flow_neg": mean(max(0.0, -f.residuals["fuel_flow"].residual_pct) for f in window),
            "manifold_pos": mean(max(0.0, f.residuals["manifold_pressure"].residual_pct) for f in window),
            "rpm_abs": mean(abs(f.residuals["rpm"].residual_pct) for f in window),
            "vibration_pos": mean(max(0.0, f.residuals["vibration"].residual_pct) for f in window),
            "battery_neg": mean(max(0.0, -f.residuals["battery_voltage"].residual_pct) for f in window),
            "rpm_instability_evidence": mean(f.diagnosis.evidence.get("rpm_instability_pct", 0.0) for f in window),
        }
        print(f"\n=== {fault_type} (severity_end={sim.get_faults().get(fault_type, {}).get('current_severity', 0):.2f}) ===")
        for k, v in r.items():
            print(f"  {k:24s} = {v:8.3f}")


if __name__ == "__main__":
    main()
