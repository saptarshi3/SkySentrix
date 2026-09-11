"""
Build a Leakage-Free Fault Diagnosis Dataset and Benchmark.

Requirements:
- Unit of split is the INDEPENDENT RUN (Seed + Mission), NOT individual rows.
- 60% Train Runs, 20% Validation Runs, 20% Test Runs.
- 11 Classes: healthy + 10 faults.
- Multiple mission presets (normal_endurance, long_endurance, high_altitude, hot_weather, high_load).
- Extract 35+ engineered features (residuals, temporal dynamics, physical ratios, sensor fault tests).
- Benchmark current production DiagnosisEngine on the virgin TEST partition.
- Generate full reproducibility artifacts in backend/data/ and backend/artifacts/.
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pipeline import DigitalTwinPipeline
from app.engine.simulator import EngineSimulator
from app.config import FAULT_TYPES
from scripts.feature_extractor import DiagnosisFeatureExtractor

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"
DATA_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

PRESETS = ["normal_endurance", "long_endurance", "high_altitude", "hot_weather", "high_load"]
ALL_CLASSES = ["healthy"] + FAULT_TYPES

RUN_DURATION_SEC = 140
INJECT_AT_SEC = 40
WARMUP_EXCLUSION_SEC = 20  # Exclude initial 20s startup noise

RUNS_PER_CLASS = 15  # 15 runs per class = 165 total independent simulation runs
# Split: 9 Train (60%), 3 Val (20%), 3 Test (20%) per class

def generate_simulation_run(
    pipeline: DigitalTwinPipeline,
    extractor: DiagnosisFeatureExtractor,
    run_id: str,
    fault_label: str,
    preset: str,
    seed: int,
    severity: float,
    progression: float,
) -> List[Dict[str, Any]]:
    pipeline.reset_state()
    pipeline.current_preset = preset
    extractor.reset()

    sim = EngineSimulator(seed=seed)
    sim.load_mission(preset, duration_sec=RUN_DURATION_SEC, mission_name=run_id)

    records: List[Dict[str, Any]] = []

    for step in range(RUN_DURATION_SEC):
        if fault_label != "healthy" and step == INJECT_AT_SEC:
            sim.inject_fault(fault_label, severity=severity, progression_per_sec=progression)

        point = sim.step(1.0)
        frame = pipeline.process(None, point)

        # Feature extraction
        feats = extractor.extract_features(frame)

        # Skip initial engine ignition startup transient (<20s)
        if step < WARMUP_EXCLUSION_SEC:
            continue

        # Effective ground truth label at this second:
        # Before injection, it is strictly healthy. After injection, it is the fault label.
        is_active_fault = (fault_label != "healthy") and (step >= INJECT_AT_SEC)
        effective_label = fault_label if is_active_fault else "healthy"

        rec = {
            "run_id": run_id,
            "step": step,
            "seed": seed,
            "preset": preset,
            "operating_regime": point.mode,
            "target_fault": fault_label,
            "effective_label": effective_label,
            "is_active_fault": is_active_fault,
            "target_severity": severity if fault_label != "healthy" else 0.0,
            "is_transient": 1 if (step < INJECT_AT_SEC + 10 and is_active_fault) else 0,
            # Telemetry & pipeline diagnoses for benchmark evaluation
            "pred_diagnosis": frame.diagnosis.probable_fault,
            "diagnosis_conf": frame.diagnosis.confidence,
            "anomaly_score": frame.anomaly.score,
            "anomaly_level": frame.anomaly.level,
        }
        rec.update(feats)
        records.append(rec)

    return records


def main():
    print("=" * 70)
    print("CHUNK 2: BUILDING LEAKAGE-FREE DATASET & BENCHMARK")
    print("=" * 70)

    pipeline = DigitalTwinPipeline()
    extractor = DiagnosisFeatureExtractor(window_size=30)

    # 1. Define strict run-level splits
    # For each class, create 15 runs (9 train, 3 val, 3 test)
    run_catalog = []
    run_id_counter = 0

    for c_idx, label in enumerate(ALL_CLASSES):
        for r_idx in range(RUNS_PER_CLASS):
            run_id = f"run_{run_id_counter:04d}_{label}"
            run_id_counter += 1

            # Determine split
            if r_idx < 9:
                split = "train"
            elif r_idx < 12:
                split = "val"
            else:
                split = "test"

            preset = PRESETS[r_idx % len(PRESETS)]
            seed = 10000 + c_idx * 100 + r_idx

            # Varied severities between 0.35 and 0.85
            severity = 0.35 + (r_idx % 5) * 0.12
            progression = 0.005 + (r_idx % 3) * 0.005

            run_catalog.append({
                "run_id": run_id,
                "label": label,
                "preset": preset,
                "seed": seed,
                "severity": round(severity, 3),
                "progression": round(progression, 4),
                "split": split,
            })

    print(f"Configured {len(run_catalog)} independent simulation runs across {len(ALL_CLASSES)} classes.")
    print("Splits: 99 Train runs (60%), 33 Val runs (20%), 33 Test runs (20%).")

    # 2. Execute runs and gather data
    train_data = []
    val_data = []
    test_data = []

    t0 = time.time()
    for item in run_catalog:
        records = generate_simulation_run(
            pipeline=pipeline,
            extractor=extractor,
            run_id=item["run_id"],
            fault_label=item["label"],
            preset=item["preset"],
            seed=item["seed"],
            severity=item["severity"],
            progression=item["progression"],
        )
        if item["split"] == "train":
            train_data.extend(records)
        elif item["split"] == "val":
            val_data.extend(records)
        else:
            test_data.extend(records)

    elapsed = time.time() - t0
    print(f"Data generation complete in {elapsed:.1f}s.")
    print(f"Train samples: {len(train_data)} | Val samples: {len(val_data)} | Test samples: {len(test_data)}")

    # 3. Save run partition lists
    train_runs = [r for r in run_catalog if r["split"] == "train"]
    val_runs = [r for r in run_catalog if r["split"] == "val"]
    test_runs = [r for r in run_catalog if r["split"] == "test"]

    with open(ARTIFACTS_DIR / "train_runs.json", "w") as f:
        json.dump(train_runs, f, indent=2)
    with open(ARTIFACTS_DIR / "validation_runs.json", "w") as f:
        json.dump(val_runs, f, indent=2)
    with open(ARTIFACTS_DIR / "test_runs.json", "w") as f:
        json.dump(test_runs, f, indent=2)

    # 4. Feature Schema
    all_keys = list(train_data[0].keys())
    meta_keys = {"run_id", "step", "seed", "preset", "operating_regime", "target_fault", "effective_label", "is_active_fault", "target_severity", "is_transient", "pred_diagnosis", "diagnosis_conf", "anomaly_score", "anomaly_level"}
    feature_keys = [k for k in all_keys if k not in meta_keys]

    with open(ARTIFACTS_DIR / "feature_schema.json", "w") as f:
        json.dump({"feature_count": len(feature_keys), "features": feature_keys}, f, indent=2)

    # 5. Feature Separability & Quality Report
    print("\nComputing feature quality and class separability analysis...")
    # Group features by effective_label
    class_feature_stats = {}
    for cl in ALL_CLASSES:
        cl_rows = [r for r in train_data if r["effective_label"] == cl and r["is_active_fault"]]
        if not cl_rows and cl == "healthy":
            cl_rows = [r for r in train_data if r["effective_label"] == "healthy"]
        
        stats = {}
        for fk in feature_keys:
            vals = [r[fk] for r in cl_rows]
            stats[fk] = {
                "mean": round(float(np.mean(vals)), 4) if vals else 0.0,
                "std": round(float(np.std(vals)), 4) if vals else 0.0,
            }
        class_feature_stats[cl] = stats

    # Identify most useful separating features by variance between classes vs within class (F-ratio proxy)
    feature_importance_scores = {}
    for fk in feature_keys:
        means = [class_feature_stats[cl][fk]["mean"] for cl in ALL_CLASSES]
        stds = [class_feature_stats[cl][fk]["std"] for cl in ALL_CLASSES]
        between_var = np.var(means)
        within_var = np.mean([s**2 for s in stds]) + 1e-5
        f_proxy = float(between_var / within_var)
        feature_importance_scores[fk] = round(f_proxy, 3)

    sorted_features = sorted(feature_importance_scores.items(), key=lambda x: x[1], reverse=True)

    separability_report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "top_separating_features": dict(sorted_features[:15]),
        "class_feature_means": {
            cl: {k: class_feature_stats[cl][k]["mean"] for k in [sf[0] for sf in sorted_features[:10]]}
            for cl in ALL_CLASSES
        }
    }
    with open(ARTIFACTS_DIR / "feature_separability_report.json", "w") as f:
        json.dump(separability_report, f, indent=2)

    # 6. Baseline Benchmark on VIRGIN TEST SET
    print("\nEvaluating EXISTING production DiagnosisEngine on the VIRGIN TEST SET...")
    # Evaluate at the final window of each test run (last 30 samples of fault injection)
    test_run_predictions = []
    confusion: Dict[str, Dict[str, int]] = {f: defaultdict(int) for f in ALL_CLASSES}

    for tr in test_runs:
        target_f = tr["label"]
        run_samples = [r for r in test_data if r["run_id"] == tr["run_id"]]
        final_window = run_samples[-30:]
        votes = Counter([r["pred_diagnosis"] for r in final_window])
        # Win-mode vote
        predicted = votes.most_common(1)[0][0]
        correct = (predicted == target_f)
        confusion[target_f][predicted] += 1
        test_run_predictions.append({
            "run_id": tr["run_id"],
            "true_fault": target_f,
            "predicted_fault": predicted,
            "correct": correct,
            "votes": dict(votes),
        })

    # Per-class metrics
    per_class_metrics = {}
    for cl in ALL_CLASSES:
        tp = confusion[cl].get(cl, 0)
        fn = sum(confusion[cl].values()) - tp
        fp = sum(confusion[other].get(cl, 0) for other in ALL_CLASSES if other != cl)

        prec = tp / max(tp + fp, 1) if (tp + fp) > 0 else (1.0 if fp == 0 and tp == 0 else 0.0)
        rec = tp / max(tp + fn, 1) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / max(prec + rec, 1e-9) if (prec + rec) > 0 else 0.0

        per_class_metrics[cl] = {
            "precision": round(prec, 3),
            "recall": round(rec, 3),
            "f1": round(f1, 3),
            "test_runs": sum(confusion[cl].values()),
            "correct_runs": tp,
        }

    total_correct = sum(1 for p in test_run_predictions if p["correct"])
    overall_acc = total_correct / len(test_run_predictions)
    macro_f1 = float(np.mean([m["f1"] for m in per_class_metrics.values()]))
    macro_prec = float(np.mean([m["precision"] for m in per_class_metrics.values()]))
    macro_rec = float(np.mean([m["recall"] for m in per_class_metrics.values()]))

    baseline_benchmark = {
        "benchmark_type": "CLEAN_LEAKAGE_FREE_TEST_SET",
        "total_test_runs": len(test_run_predictions),
        "overall_accuracy": round(overall_acc, 4),
        "macro_precision": round(macro_prec, 4),
        "macro_recall": round(macro_rec, 4),
        "macro_f1": round(macro_f1, 4),
        "per_class": per_class_metrics,
        "confusion_matrix": {k: dict(v) for k, v in confusion.items()},
        "comparisons": {
            "old_historical_benchmark": {
                "accuracy": 0.40,
                "macro_f1": 0.325,
                "flaw": "Only tested on 1 run per fault (10 runs total) with hardcoded seeds 700-709 and normal_endurance only."
            },
            "new_leakage_free_benchmark": {
                "accuracy": round(overall_acc, 4),
                "macro_f1": round(macro_f1, 4),
                "rigor": "Tested across 33 independent runs (3 per class) with varied mission presets, unseen seeds, and varied severities."
            }
        }
    }

    with open(ARTIFACTS_DIR / "baseline_benchmark.json", "w") as f:
        json.dump(baseline_benchmark, f, indent=2)

    # Save summary metadata
    summary = {
        "dataset_created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_runs": len(run_catalog),
        "total_samples": len(train_data) + len(val_data) + len(test_data),
        "train_samples": len(train_data),
        "val_samples": len(val_data),
        "test_samples": len(test_data),
        "feature_count": len(feature_keys),
        "classes": ALL_CLASSES,
        "runs_per_class": RUNS_PER_CLASS,
        "presets_used": PRESETS,
    }
    with open(DATA_DIR / "fault_diagnosis_dataset_metadata.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 70)
    print(f"BENCHMARK COMPLETE:")
    print(f"Clean Test Set Accuracy : {overall_acc*100:.1f}% ({total_correct}/{len(test_run_predictions)} runs correct)")
    print(f"Clean Test Set Macro F1 : {macro_f1:.3f}")
    print(f"Top 5 Separating Features : {[x[0] for x in sorted_features[:5]]}")
    print("=" * 70)

if __name__ == "__main__":
    main()
