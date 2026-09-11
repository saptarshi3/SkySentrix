"""
Phase 2 Investigation: Separability analysis for the five confused fault classes.

Runs each fault trajectory and extracts raw residual/feature statistics from the
stabilised post-injection window (last 30 steps of a 180 s run, 60 s warmup).

Does NOT modify any core files.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.engine.simulator import EngineSimulator          # noqa: E402
from app.services.pipeline import DigitalTwinPipeline    # noqa: E402
from scripts.trajectory_utils import run_fault_trajectory # noqa: E402

FAULTS = [
    "injector_degradation",
    "misfire",
    "excessive_vibration",
    "combustion_instability",
    "fuel_system_degradation",
]

WARMUP = 60
DURATION = 180
SEVERITY = 0.75
PROGRESSION = 0.01
MEASURE_WINDOW = 30   # last N steps (stabilised fault)

RESULTS_DIR = Path(__file__).resolve().parents[1] / "validation_results"


def run_investigation() -> None:
    pipeline = DigitalTwinPipeline()
    results: dict = {}

    for i, fault in enumerate(FAULTS):
        seed = 700 + i
        print(f"Running {fault} (seed={seed}) ...", flush=True)
        frames, sim = run_fault_trajectory(
            pipeline, "normal_endurance", seed, DURATION,
            fault, SEVERITY, PROGRESSION, inject_at_step=WARMUP,
        )

        window = frames[-MEASURE_WINDOW:]

        def feat_dict(f):
            res = f.residuals
            tel = f.telemetry
            return {
                "rpm_residual":   res["rpm"].residual_pct,
                "egt_residual":   res["egt"].residual_pct,
                "cht_residual":   res["cht"].residual_pct,
                "oil_temp_res":   res["oil_temp"].residual_pct,
                "oil_pres_res":   res["oil_pressure"].residual_pct,
                "fuel_flow_res":  res["fuel_flow"].residual_pct,
                "vibration_res":  res["vibration"].residual_pct,
                "manifold_res":   res["manifold_pressure"].residual_pct,
                "battery_res":    res["battery_voltage"].residual_pct,
                "rpm_val":        tel.rpm,
                "egt_val":        tel.egt,
                "vibration_val":  tel.vibration,
                "fuel_flow_val":  tel.fuel_flow,
                "engine_eff":     tel.engine_efficiency,
            }

        feat_series = [feat_dict(f) for f in window]
        keys = list(feat_series[0].keys())

        summary: dict = {}
        for k in keys:
            vals = [s[k] for s in feat_series]
            summary[k] = {
                "mean": round(mean(vals), 3),
                "std":  round(pstdev(vals), 3),
                "min":  round(min(vals), 3),
                "max":  round(max(vals), 3),
            }

        egt_vals = [f.telemetry.egt for f in window]
        summary["egt_instability_pstdev"] = round(pstdev(egt_vals), 3)

        rpm_vals = [f.telemetry.rpm for f in window]
        mean_rpm = mean(rpm_vals)
        summary["rpm_instability_pct"] = round(
            100.0 * pstdev(rpm_vals) / mean_rpm if mean_rpm > 0 else 0.0, 3
        )

        vib_vals = [f.telemetry.vibration for f in window]
        summary["vibration_pstdev"] = round(pstdev(vib_vals), 3)

        votes: dict = defaultdict(int)
        for f in window:
            votes[f.diagnosis.probable_fault] += 1
        summary["_diagnosis_vote"] = dict(votes)
        summary["_predicted"] = max(votes, key=votes.get)

        results[fault] = summary

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "phase2_separability.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nReport written to {out_path}")

    # Print compact comparison table
    print("\n--- FEATURE COMPARISON TABLE ---")
    key_features = [
        "rpm_residual", "egt_residual", "cht_residual", "oil_pres_res",
        "fuel_flow_res", "vibration_res", "manifold_res",
        "egt_instability_pstdev", "rpm_instability_pct", "vibration_pstdev",
        "engine_eff",
    ]
    header = f"{'Feature':<30}" + "".join(f"{f[:14]:>16}" for f in FAULTS)
    print(header)
    print("-" * len(header))
    for feat in key_features:
        row = f"{feat:<30}"
        for fault in FAULTS:
            val = results[fault].get(feat)
            if isinstance(val, dict):
                v = val.get("mean", "?")
            else:
                v = val
            row += f"{str(v):>16}"
        print(row)

    print("\n--- DIAGNOSIS VOTES (last 30 steps) ---")
    for fault in FAULTS:
        votes = results[fault]["_diagnosis_vote"]
        predicted = results[fault]["_predicted"]
        correct = "✓" if predicted == fault else "✗"
        print(f"  {fault:<30} predicted={predicted:<30} {correct}  votes={votes}")


if __name__ == "__main__":
    run_investigation()
