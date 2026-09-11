"""
Phase 1G: Anomaly model persistence verification.
3 experiments:
  1. Model missing: verify training occurs and artifact is saved.
  2. Artifact exists: verify it is loaded (not retrained).
  3. Determinism: identical inputs yield identical outputs.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.analytics.anomaly import AnomalyEngine


def exp1_missing_artifact():
    """When no artifact exists, engine trains and saves."""
    tmp = Path(tempfile.mkdtemp())
    try:
        engine = AnomalyEngine(model_dir=tmp, auto_load=True)
        artifact = tmp / "anomaly_model.joblib"
        meta = tmp / "anomaly_model.meta.json"
        trained = artifact.exists()
        meta_ok = meta.exists()
        src = engine.training_source
        return {
            "experiment": "exp1_missing_artifact",
            "artifact_created": trained,
            "meta_created": meta_ok,
            "training_source": src,
            "PASS": trained and meta_ok,
        }
    finally:
        shutil.rmtree(tmp)


def exp2_artifact_loaded():
    """When artifact exists, engine loads it without retraining."""
    tmp = Path(tempfile.mkdtemp())
    try:
        # Step 1: create artifact
        e1 = AnomalyEngine(model_dir=tmp, auto_load=True, seed=77)
        e1.training_source = "exp2_first_train"
        e1.save()
        
        # Step 2: load it
        e2 = AnomalyEngine(model_dir=tmp, auto_load=True, seed=77)
        loaded = e2.training_source in {"exp2_first_train", "loaded_artifact"}
        # Also verify it did NOT retrain (score_mean should be same)
        same_mean = abs(e1.score_mean - e2.score_mean) < 1e-6
        return {
            "experiment": "exp2_artifact_loaded",
            "loaded_source": e2.training_source,
            "score_mean_match": same_mean,
            "PASS": loaded and same_mean,
        }
    finally:
        shutil.rmtree(tmp)


def exp3_determinism():
    """Identical inputs yield identical anomaly scores."""
    import datetime
    from app.models.schemas import TelemetryPoint, ResidualEntry
    
    def make_telemetry():
        return TelemetryPoint(
            timestamp=datetime.datetime(2025, 1, 1, 0, 0, 0),
            mode="cruise", rpm=2400.0, cht=180.0, egt=620.0,
            oil_pressure=55.0, oil_temp=95.0, fuel_flow=18.0,
            vibration=0.12, battery_voltage=13.8, alternator_health=0.97,
            injection_timing=28.0, throttle=0.65, engine_load=0.60,
            altitude=3500.0, ambient_temp=8.0, engine_efficiency=0.92,
            manifold_pressure=25.0, air_mass_flow=0.18, torque_nm=110.0,
            power_kw=27.0, propeller_load=0.55, airspeed=145.0,
            pressure_kpa=65.0, density_ratio=0.78,
        )
    
    def make_residuals():
        return {k: ResidualEntry(actual=0.0, expected=0.0, residual=0.0, residual_pct=0.0)
                for k in ["rpm", "cht", "egt", "oil_pressure", "oil_temp",
                          "fuel_flow", "vibration", "battery_voltage",
                          "manifold_pressure", "air_mass_flow", "torque_nm", "power_kw"]}
    
    tmp = Path(tempfile.mkdtemp())
    try:
        e = AnomalyEngine(model_dir=tmp, auto_load=True, seed=42)
        t = make_telemetry()
        r = make_residuals()
        
        r1 = e.score(t, r)
        e.reset_state()
        r2 = e.score(t, r)
        
        same = abs(r1.score - r2.score) < 1e-9
        return {
            "experiment": "exp3_determinism",
            "score_run1": round(r1.score, 8),
            "score_run2": round(r2.score, 8),
            "PASS": same,
        }
    finally:
        shutil.rmtree(tmp)


def main():
    results = []
    for fn in [exp1_missing_artifact, exp2_artifact_loaded, exp3_determinism]:
        res = fn()
        results.append(res)
        status = "PASS" if res["PASS"] else "FAIL"
        print(f"[{status}] {res['experiment']}: {res}")
    
    all_pass = all(r["PASS"] for r in results)
    print(f"\nOverall: {'PASS' if all_pass else 'FAIL'} ({sum(r['PASS'] for r in results)}/3 passed)")
    
    out = Path(__file__).resolve().parents[1] / "validation_results" / "anomaly_persistence_verification.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"experiments": results, "all_pass": all_pass}, indent=2))
    print(f"Report saved to {out}")


if __name__ == "__main__":
    main()
