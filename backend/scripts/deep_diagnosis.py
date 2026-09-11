"""
Phase 1.5 Deep Diagnosis: For each failing fault, dump the internal scores
at the final timestep so we can see exactly why the wrong class wins.
"""
import sys
from collections import Counter
from pathlib import Path
from statistics import pstdev

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pipeline import DigitalTwinPipeline
from scripts.trajectory_utils import FAULT_TYPES, run_fault_trajectory

FAILING = [
    "injector_degradation",
    "combustion_instability",
    "fuel_system_degradation",
    "sensor_drift",
    "sensor_failure",
    "misfire",  # reported as excessive_vibration in confusion matrix
]

def main():
    for i, fault_type in enumerate(FAULT_TYPES):
        seed = 1000 + i
        pipeline = DigitalTwinPipeline()
        frames, sim = run_fault_trajectory(
            pipeline, "normal_endurance", seed=seed,
            duration_sec=180, fault_type=fault_type,
            severity=0.75, progression_per_sec=0.01,
            inject_at_step=60,
        )
        
        # Access the diagnosis engine's internal state
        diag = pipeline.diagnosis
        
        # Replay the last frame to get scores
        last = frames[-1]
        tel = last.telemetry
        res = last.residuals
        anom = last.anomaly
        
        # Recompute the score decomposition manually
        from app.analytics.diagnosis import BASELINE_FEATURES
        baselines = BASELINE_FEATURES.get("normal_endurance", BASELINE_FEATURES["normal_endurance"])
        
        egt_pos_raw = max(0.0, res["egt"].residual_pct)
        cht_pos_raw = max(0.0, res["cht"].residual_pct)
        oil_temp_pos_raw = max(0.0, res["oil_temp"].residual_pct)
        oil_pressure_neg_raw = max(0.0, -res["oil_pressure"].residual_pct)
        manifold_pos_raw = max(0.0, res["manifold_pressure"].residual_pct)
        vibration_pos_raw = max(0.0, res["vibration"].residual_pct)
        battery_neg_raw = max(0.0, -res["battery_voltage"].residual_pct)
        fuel_flow_signed_raw = res["fuel_flow"].residual_pct
        
        egt_pos = max(0.0, egt_pos_raw - baselines["egt_pos"])
        cht_pos = max(0.0, cht_pos_raw - baselines["cht_pos"])
        oil_temp_pos = max(0.0, oil_temp_pos_raw - baselines["oil_temp_pos"])
        oil_pressure_neg = max(0.0, oil_pressure_neg_raw - baselines["oil_pressure_neg"])
        manifold_pos = max(0.0, manifold_pos_raw - baselines["manifold_pos"])
        vibration_pos = max(0.0, vibration_pos_raw - baselines["vibration_pos"])
        battery_neg = max(0.0, battery_neg_raw - baselines["battery_neg"])
        rpm_instability_raw = diag._rpm_instability_pct()
        rpm_instability = max(0.0, rpm_instability_raw - baselines["rpm_instability"])
        egt_instability = diag._egt_instability()
        
        fuel_flow_signed_excess = fuel_flow_signed_raw - baselines["fuel_flow_signed"]
        fuel_flow_pos = max(0.0, fuel_flow_signed_excess)
        fuel_flow_neg = max(0.0, -fuel_flow_signed_excess)
        
        rpm_abs = abs(res["rpm"].residual_pct)
        alternator_degraded = max(0.0, (1.0 - tel.alternator_health) * 100.0)
        eff_loss = max(0.0, (0.93 - tel.engine_efficiency) * 100.0)
        ambient_hot = max(0.0, tel.ambient_temp - 32.0)
        
        # Compute scores
        scores = {}
        scores["injector_degradation"] = 4.0 * egt_pos + 1.5 * fuel_flow_neg + 0.8 * manifold_pos + 1.2 * rpm_instability
        scores["misfire"] = 1.0 * rpm_abs + 4.8 * rpm_instability + 1.0 * vibration_pos + 0.5 * fuel_flow_neg
        scores["lubrication_problem"] = 1.8 * oil_pressure_neg + 1.5 * oil_temp_pos + 0.75 * vibration_pos
        scores["overheating"] = 5.0 * cht_pos + 3.0 * egt_pos + 3.0 * oil_temp_pos + 0.22 * ambient_hot
        scores["excessive_vibration"] = 4.0 * vibration_pos + 0.8 * rpm_instability
        scores["combustion_instability"] = 5.0 * egt_instability + 0.5 * rpm_abs + 2.0 * vibration_pos + 1.0 * rpm_instability
        scores["fuel_system_degradation"] = 3.5 * fuel_flow_neg + 0.9 * manifold_pos + 0.8 * egt_pos
        scores["alternator_problem"] = 4.0 * battery_neg + 0.7 * alternator_degraded
        
        # Sensor bonuses
        drifting_keys = [k for k in ["egt", "cht", "oil_temp", "fuel_flow", "oil_pressure"] if diag._drift_sensor(k)]
        flatline_keys = [k for k in ["oil_pressure", "egt", "rpm", "battery_voltage"] if diag._flatline_sensor(k)]
        if drifting_keys:
            scores["sensor_drift"] += 50.0
        if flatline_keys:
            scores["sensor_failure"] += 50.0
        
        anomaly_weight = 0.7 + 0.6 * anom.score
        for k in scores:
            scores[k] *= anomaly_weight
        
        # Rank scores
        ranked = sorted(scores.items(), key=lambda x: -x[1])
        predicted = ranked[0][0]
        correct = predicted == fault_type
        
        # Get the test_fault_diagnosis stabilization window prediction
        diagnoses = [f.diagnosis.probable_fault for f in frames]
        final_window = diagnoses[-30:]
        vote = Counter(final_window)
        majority_pred = vote.most_common(1)[0][0]
        
        status = "CORRECT" if majority_pred == fault_type else "WRONG"
        print(f"\n{'='*70}")
        print(f"FAULT: {fault_type}")
        print(f"  Majority vote (last 30): {majority_pred} [{status}]")
        print(f"  Last-step prediction:    {predicted}")
        print(f"  Anomaly score: {anom.score:.3f}  level: {anom.level}  weight: {anomaly_weight:.3f}")
        print(f"")
        print(f"  --- Features (baseline-corrected) ---")
        print(f"    egt_pos={egt_pos:.2f}  cht_pos={cht_pos:.2f}  oil_temp_pos={oil_temp_pos:.2f}")
        print(f"    oil_pressure_neg={oil_pressure_neg:.2f}  manifold_pos={manifold_pos:.2f}")
        print(f"    vibration_pos={vibration_pos:.2f}  battery_neg={battery_neg:.2f}")
        print(f"    rpm_instability={rpm_instability:.2f} (raw={rpm_instability_raw:.2f})")
        print(f"    egt_instability={egt_instability:.2f}")
        print(f"    fuel_flow_pos={fuel_flow_pos:.2f}  fuel_flow_neg={fuel_flow_neg:.2f}")
        print(f"    rpm_abs={rpm_abs:.2f}  alternator_degraded={alternator_degraded:.2f}")
        print(f"    drifting_sensors={drifting_keys}  flatline_sensors={flatline_keys}")
        print(f"")
        print(f"  --- Scores (after anomaly_weight) ---")
        for name, sc in ranked:
            marker = " <-- TRUE" if name == fault_type else (" <-- PREDICTED" if name == predicted and name != fault_type else "")
            print(f"    {name:30s}  {sc:8.2f}{marker}")


if __name__ == "__main__":
    main()
