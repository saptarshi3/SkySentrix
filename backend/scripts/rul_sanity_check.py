"""
Phase 1H: RUL Scale Sanity Check.
Measures actual RUL outputs vs initial_rul_hours and computes a proxy
MAE/RMSE for healthy and fault trajectories.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pipeline import DigitalTwinPipeline
from scripts.trajectory_utils import FAULT_TYPES, run_fault_trajectory, run_healthy_trajectory

RESULTS_DIR = Path(__file__).resolve().parents[1] / "validation_results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

INITIAL_RUL = 480.0  # From config.py

def main():
    pipeline = DigitalTwinPipeline()

    print("=== Phase 1H: RUL Scale Sanity Check ===")
    print(f"Initial RUL (config): {INITIAL_RUL} hours")
    print(f"Failure threshold (health):  20.0 (i.e. failure at deg_index=80)")
    print()

    # 1. Healthy trajectory: RUL should stay near initial
    frames = run_healthy_trajectory(pipeline, "normal_endurance", seed=999, duration_sec=120)
    ruls_healthy = [f.rul.current_rul_hours for f in frames]
    print(f"Healthy trajectory (120s, normal_endurance):")
    print(f"  RUL start:  {ruls_healthy[0]:.1f} h")
    print(f"  RUL end:    {ruls_healthy[-1]:.1f} h")
    print(f"  RUL min:    {min(ruls_healthy):.1f} h")
    print(f"  RUL max:    {max(ruls_healthy):.1f} h")
    rul_drop_healthy = ruls_healthy[0] - ruls_healthy[-1]
    expected_rul_drop = INITIAL_RUL * (120 / 3600) * 0.17  # 1s ticks * 120 steps * base rate
    print(f"  RUL drop:   {rul_drop_healthy:.2f} h  (expected ~{expected_rul_drop:.2f} at base rate 0.17 deg/h)")
    print()

    # 2. Fault trajectories: RUL should decrease faster
    print(f"{'Fault':<25} {'RUL_start':>10} {'RUL_end':>10} {'Delta':>8} {'Rate/h (app)':>14}")
    print("-" * 75)
    fault_results = []
    for i, fault_type in enumerate(FAULT_TYPES):
        pipeline2 = DigitalTwinPipeline()
        frames_f, _ = run_fault_trajectory(
            pipeline2, "normal_endurance", seed=2000+i, duration_sec=120,
            fault_type=fault_type, severity=0.75, progression_per_sec=0.01,
            inject_at_step=60,
        )
        ruls_f = [f.rul.current_rul_hours for f in frames_f]
        rul_start = ruls_f[0]
        rul_end = ruls_f[-1]
        delta = rul_end - rul_start
        # Approximate deg rate = delta / (120/3600)
        elapsed_h = 120 / 3600
        rate = abs(delta) / elapsed_h if elapsed_h > 0 else 0
        print(f"{fault_type:<25} {rul_start:>10.1f} {rul_end:>10.1f} {delta:>8.1f} {rate:>14.1f}")
        fault_results.append({"fault": fault_type, "rul_start": rul_start, "rul_end": rul_end, "delta": delta})

    # 3. Quick MAE/RMSE — ground truth = simple linear RUL (healthy at constant base rate)
    # (This is a proxy only since we have no real run-to-failure data)
    healthy_rul_true = [INITIAL_RUL - (i / 3600) * 0.17 for i in range(120)]
    rul_errors = [abs(ruls_healthy[i] - healthy_rul_true[i]) for i in range(120)]
    mae_healthy = np.mean(rul_errors)
    rmse_healthy = np.sqrt(np.mean([e**2 for e in rul_errors]))
    mae_pct = mae_healthy / INITIAL_RUL * 100
    rmse_pct = rmse_healthy / INITIAL_RUL * 100

    print(f"\nRUL MAE vs naive linear (healthy, 120s):")
    print(f"  MAE  = {mae_healthy:.3f} h  ({mae_pct:.3f}% of {INITIAL_RUL}h)")
    print(f"  RMSE = {rmse_healthy:.3f} h  ({rmse_pct:.3f}% of {INITIAL_RUL}h)")
    print()
    print("NOTE: This is a synthetic proxy. No real run-to-failure data used.")

    report = {
        "initial_rul_hours": INITIAL_RUL,
        "failure_health_threshold": 20.0,
        "healthy_120s": {
            "rul_start": ruls_healthy[0],
            "rul_end": ruls_healthy[-1],
            "rul_drop": rul_drop_healthy,
            "rul_mae_vs_naive_linear_hours": round(mae_healthy, 4),
            "rul_rmse_vs_naive_linear_hours": round(rmse_healthy, 4),
            "rul_mae_pct": round(mae_pct, 4),
            "rul_rmse_pct": round(rmse_pct, 4),
        },
        "fault_trajectories": fault_results,
        "notes": "Proxy only — no real engine run-to-failure data. Synthetic limitation acknowledged.",
    }
    out = RESULTS_DIR / "rul_sanity_check.json"
    out.write_text(json.dumps(report, indent=2, default=str))
    print(f"Report saved to {out}")


if __name__ == "__main__":
    main()
