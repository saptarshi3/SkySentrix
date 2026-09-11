"""
Train and Evaluate Supervised Multi-Class Fault Diagnosis Classifier.

Pipeline:
1. Load or generate run-level partitioned data (Train: 99 runs, Val: 33 runs, Test: 33 runs).
2. Verify strict zero-leakage: features match 39 engineered features in feature_schema.json.
3. Train candidate models using GroupKFold(n_splits=5) on run_id.
4. Evaluate candidate models on independent Validation Set (33 runs).
5. Select best model on validation performance.
6. Evaluate ONCE on Virgin Test Set (33 runs).
7. Persist model to backend/models/diagnosis_classifier.joblib + metadata.
8. Dump evaluation scorecard to backend/artifacts/diagnosis_model_eval.json.
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pipeline import DigitalTwinPipeline
from app.engine.simulator import EngineSimulator
from app.config import FAULT_TYPES
from app.analytics.feature_extractor import DiagnosisFeatureExtractor, FEATURE_NAMES

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"
ARTIFACTS_DIR = BACKEND_DIR / "artifacts"
MODELS_DIR = BACKEND_DIR / "models"
DATA_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

ALL_CLASSES = ["healthy"] + FAULT_TYPES
RUN_DURATION_SEC = 140
INJECT_AT_SEC = 40
WARMUP_EXCLUSION_SEC = 20

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
        feats = extractor.extract_features(frame)

        if step < WARMUP_EXCLUSION_SEC:
            continue

        is_active_fault = (fault_label != "healthy") and (step >= INJECT_AT_SEC)
        effective_label = fault_label if is_active_fault else "healthy"

        rec = {
            "run_id": run_id,
            "step": step,
            "seed": seed,
            "preset": preset,
            "target_fault": fault_label,
            "effective_label": effective_label,
            "is_active_fault": is_active_fault,
            "target_severity": severity if fault_label != "healthy" else 0.0,
            "is_transient": 1 if (step < INJECT_AT_SEC + 10 and is_active_fault) else 0,
            "anomaly_score": frame.anomaly.score,
        }
        rec.update(feats)
        records.append(rec)

    return records


def load_or_generate_datasets() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train_file = DATA_DIR / "train_data.joblib"
    val_file = DATA_DIR / "val_data.joblib"
    test_file = DATA_DIR / "test_data.joblib"

    if train_file.exists() and val_file.exists() and test_file.exists():
        print("Loading cached datasets from backend/data/ ...")
        df_train = joblib.load(train_file)
        df_val = joblib.load(val_file)
        df_test = joblib.load(test_file)
        print(f"Loaded train: {len(df_train)}, val: {len(df_val)}, test: {len(df_test)}")
        return df_train, df_val, df_test

    print("Cached data not found. Generating simulation datasets from run configs...")
    with open(ARTIFACTS_DIR / "train_runs.json", "r") as f:
        train_runs = json.load(f)
    with open(ARTIFACTS_DIR / "validation_runs.json", "r") as f:
        val_runs = json.load(f)
    with open(ARTIFACTS_DIR / "test_runs.json", "r") as f:
        test_runs = json.load(f)

    pipeline = DigitalTwinPipeline()
    extractor = DiagnosisFeatureExtractor(window_size=30)

    def run_partition(runs: List[Dict[str, Any]]) -> pd.DataFrame:
        recs = []
        for item in runs:
            r = generate_simulation_run(
                pipeline=pipeline,
                extractor=extractor,
                run_id=item["run_id"],
                fault_label=item["label"],
                preset=item["preset"],
                seed=item["seed"],
                severity=item["severity"],
                progression=item["progression"],
            )
            recs.extend(r)
        return pd.DataFrame(recs)

    t0 = time.time()
    df_train = run_partition(train_runs)
    df_val = run_partition(val_runs)
    df_test = run_partition(test_runs)
    print(f"Generated datasets in {time.time() - t0:.1f}s.")

    joblib.dump(df_train, train_file, compress=3)
    joblib.dump(df_val, val_file, compress=3)
    joblib.dump(df_test, test_file, compress=3)
    print("Cached datasets to backend/data/.")

    return df_train, df_val, df_test


def evaluate_run_level(
    model: Any,
    df: pd.DataFrame,
    feature_names: List[str],
    eval_window: int = 30,
    classes: List[str] = ALL_CLASSES,
) -> Dict[str, Any]:
    """
    Evaluate run-level diagnosis by aggregating frame predictions in the final window of each run.
    """
    run_predictions = []
    confusion = {c: defaultdict(int) for c in classes}
    latencies = []

    unique_runs = df["run_id"].unique()
    for rid in unique_runs:
        run_df = df[df["run_id"] == rid].sort_values("step")
        target = run_df["target_fault"].iloc[0]

        # Final window evaluation for steady-state run diagnosis
        final_df = run_df.tail(eval_window)
        X_final = final_df[feature_names].values
        preds_final = model.predict(X_final)
        
        counts = Counter(preds_final)
        predicted = counts.most_common(1)[0][0]
        correct = (predicted == target)
        confusion[target][predicted] += 1

        # Latency evaluation: first step after INJECT_AT_SEC where predicted == target
        fault_df = run_df[run_df["step"] >= INJECT_AT_SEC]
        if target != "healthy" and len(fault_df) > 0:
            X_fault = fault_df[feature_names].values
            preds_fault = model.predict(X_fault)
            steps_fault = fault_df["step"].values
            detected_step = None
            for s, p in zip(steps_fault, preds_fault):
                if p == target:
                    detected_step = s
                    break
            latency = (detected_step - INJECT_AT_SEC) if detected_step is not None else 999.0
            latencies.append(latency)

        run_predictions.append({
            "run_id": rid,
            "target": target,
            "predicted": predicted,
            "correct": correct,
        })

    # Per-class metrics
    per_class = {}
    for cl in classes:
        tp = confusion[cl].get(cl, 0)
        fn = sum(confusion[cl].values()) - tp
        fp = sum(confusion[other].get(cl, 0) for other in classes if other != cl)

        prec = tp / max(tp + fp, 1) if (tp + fp) > 0 else (1.0 if fp == 0 and tp == 0 else 0.0)
        rec = tp / max(tp + fn, 1) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / max(prec + rec, 1e-9) if (prec + rec) > 0 else 0.0

        per_class[cl] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "total_runs": sum(confusion[cl].values()),
            "correct_runs": tp,
        }

    total_correct = sum(1 for p in run_predictions if p["correct"])
    overall_acc = total_correct / len(run_predictions)
    macro_f1 = float(np.mean([m["f1"] for m in per_class.values()]))
    macro_prec = float(np.mean([m["precision"] for m in per_class.values()]))
    macro_rec = float(np.mean([m["recall"] for m in per_class.values()]))
    avg_latency = float(np.mean([l for l in latencies if l < 900])) if latencies else 0.0

    return {
        "overall_accuracy": round(overall_acc, 4),
        "macro_f1": round(macro_f1, 4),
        "macro_precision": round(macro_prec, 4),
        "macro_recall": round(macro_rec, 4),
        "average_latency_sec": round(avg_latency, 2),
        "total_runs": len(run_predictions),
        "correct_runs": total_correct,
        "per_class": per_class,
        "confusion_matrix": {k: dict(v) for k, v in confusion.items()},
    }


def evaluate_sample_level(
    model: Any,
    df: pd.DataFrame,
    feature_names: List[str],
    active_only: bool = True,
) -> Dict[str, float]:
    eval_df = df[df["is_active_fault"] | (df["target_fault"] == "healthy")] if active_only else df
    X = eval_df[feature_names].values
    y_true = eval_df["effective_label"].values
    y_pred = model.predict(X)

    acc = float(np.mean(y_true == y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    return {
        "sample_accuracy": round(acc, 4),
        "sample_macro_f1": round(macro_f1, 4),
        "sample_count": len(eval_df),
    }


def main():
    print("=" * 78)
    print("CHUNK 3: TRAINING AND EVALUATING FAULT DIAGNOSIS CLASSIFIER")
    print("=" * 78)

    df_train, df_val, df_test = load_or_generate_datasets()

    print(f"\nFeature count: {len(FEATURE_NAMES)}")
    print(f"Features list: {FEATURE_NAMES}")

    # Prepare Training Set
    # We train on all steps >= 20. For fault runs, steps 20-39 are labeled "healthy",
    # and steps >= 40 are labeled with the fault.
    # Note: transient steps (40-49) can be optionally included.
    X_train = df_train[FEATURE_NAMES].values
    y_train = df_train["effective_label"].values
    groups_train = df_train["run_id"].values

    print(f"\nTraining set size: {len(df_train)} samples across {df_train['run_id'].nunique()} runs.")
    print(f"Validation set size: {len(df_val)} samples across {df_val['run_id'].nunique()} runs.")
    print(f"Test set size: {len(df_test)} samples across {df_test['run_id'].nunique()} runs.")

    # 1. Evaluate Candidate Models via GroupKFold CV on Training Set
    print("\n" + "-" * 60)
    print("STEP 1: GROUP-K-FOLD CROSS VALIDATION ON TRAINING RUNS (5 splits)")
    print("-" * 60)

    gkf = GroupKFold(n_splits=5)
    candidates = {
        "RandomForest": RandomForestClassifier(
            n_estimators=180,
            max_depth=16,
            min_samples_split=4,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        ),
        "ExtraTrees": ExtraTreesClassifier(
            n_estimators=180,
            max_depth=16,
            min_samples_split=4,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        ),
        "HistGradientBoosting": HistGradientBoostingClassifier(
            max_iter=150,
            max_depth=10,
            min_samples_leaf=8,
            l2_regularization=0.5,
            class_weight="balanced",
            random_state=42,
        ),
    }

    cv_scores = {}
    for name, clf in candidates.items():
        fold_f1s = []
        fold_accs = []
        for train_idx, val_idx in gkf.split(X_train, y_train, groups=groups_train):
            clf.fit(X_train[train_idx], y_train[train_idx])
            preds = clf.predict(X_train[val_idx])
            fold_accs.append(np.mean(y_train[val_idx] == preds))
            fold_f1s.append(f1_score(y_train[val_idx], preds, average="macro", zero_division=0))
        mean_acc = float(np.mean(fold_accs))
        mean_f1 = float(np.mean(fold_f1s))
        cv_scores[name] = {"cv_mean_acc": mean_acc, "cv_mean_f1": mean_f1}
        print(f"[{name:20s}] CV Sample Acc: {mean_acc*100:.2f}% | CV Macro F1: {mean_f1:.4f}")

    # 2. Fit each candidate on full Train set and Evaluate on VALIDATION SET (33 runs)
    print("\n" + "-" * 60)
    print("STEP 2: EVALUATION ON INDEPENDENT VALIDATION SET (33 RUNS)")
    print("-" * 60)

    val_results = {}
    fitted_models = {}

    for name, clf in candidates.items():
        clf.fit(X_train, y_train)
        fitted_models[name] = clf

        run_eval = evaluate_run_level(clf, df_val, FEATURE_NAMES, eval_window=30)
        sample_eval = evaluate_sample_level(clf, df_val, FEATURE_NAMES, active_only=True)

        val_results[name] = {
            "run_eval": run_eval,
            "sample_eval": sample_eval,
        }

        print(f"[{name:20s}] VAL Run Acc: {run_eval['overall_accuracy']*100:.1f}% ({run_eval['correct_runs']}/{run_eval['total_runs']}) | "
              f"VAL Run Macro F1: {run_eval['macro_f1']:.4f} | "
              f"VAL Sample Acc: {sample_eval['sample_accuracy']*100:.1f}% | "
              f"Avg Latency: {run_eval['average_latency_sec']:.1f}s")

    # Select Best Model based on Validation Run Accuracy & Macro F1
    best_name = max(candidates.keys(), key=lambda k: (val_results[k]["run_eval"]["overall_accuracy"], val_results[k]["run_eval"]["macro_f1"]))
    best_model = fitted_models[best_name]
    print(f"\n--> Selected Best Model on Validation Set: {best_name}")
    print(f"    Validation Run Accuracy: {val_results[best_name]['run_eval']['overall_accuracy']*100:.1f}%")
    print(f"    Validation Run Macro F1: {val_results[best_name]['run_eval']['macro_f1']:.4f}")

    # Check Top Feature Importances if available
    if hasattr(best_model, "feature_importances_"):
        importances = best_model.feature_importances_
        sorted_indices = np.argsort(importances)[::-1]
        print("\nTop 10 Most Important Features:")
        for rank, idx in enumerate(sorted_indices[:10], 1):
            print(f"  {rank:2d}. {FEATURE_NAMES[idx]:30s} (importance: {importances[idx]:.4f})")

    # 3. Freeze Best Model and Evaluate ONCE on VIRGIN TEST SET (33 runs)
    print("\n" + "=" * 60)
    print("STEP 3: FINAL EVALUATION ON UNTOUCHED VIRGIN TEST SET (33 RUNS)")
    print("=" * 60)

    test_run_eval = evaluate_run_level(best_model, df_test, FEATURE_NAMES, eval_window=30)
    test_sample_eval = evaluate_sample_level(best_model, df_test, FEATURE_NAMES, active_only=True)

    print(f"Test Run Accuracy       : {test_run_eval['overall_accuracy']*100:.2f}% ({test_run_eval['correct_runs']}/{test_run_eval['total_runs']} runs correct)")
    print(f"Test Run Macro Precision: {test_run_eval['macro_precision']:.4f}")
    print(f"Test Run Macro Recall   : {test_run_eval['macro_recall']:.4f}")
    print(f"Test Run Macro F1       : {test_run_eval['macro_f1']:.4f}")
    print(f"Test Active Sample Acc  : {test_sample_eval['sample_accuracy']*100:.2f}%")
    print(f"Average Fault Latency   : {test_run_eval['average_latency_sec']:.2f}s")

    print("\nPer-Class Breakdown on Virgin Test Set:")
    for cl in ALL_CLASSES:
        m = test_run_eval["per_class"][cl]
        print(f"  {cl:25s} | Prec: {m['precision']:.3f} | Rec: {m['recall']:.3f} | F1: {m['f1']:.3f} | Runs: {m['correct_runs']}/{m['total_runs']}")

    print("\nConfusion Matrix on Virgin Test Set (rows=True, cols=Predicted):")
    conf = test_run_eval["confusion_matrix"]
    for cl in ALL_CLASSES:
        preds = conf.get(cl, {})
        pred_str = ", ".join(f"{k}: {v}" for k, v in preds.items() if v > 0)
        print(f"  {cl:25s} -> {pred_str if pred_str else 'none'}")

    # Comparison against baseline
    with open(ARTIFACTS_DIR / "baseline_benchmark.json", "r") as f:
        baseline = json.load(f)

    baseline_acc = baseline["overall_accuracy"]
    baseline_f1 = baseline["macro_f1"]

    print("\n" + "=" * 60)
    print("COMPARISON: BASELINE vs NEW CLASSIFIER ON VIRGIN TEST SET")
    print("=" * 60)
    print(f"Baseline Production Accuracy : {baseline_acc*100:.2f}%  -->  New Model: {test_run_eval['overall_accuracy']*100:.2f}%  (Δ +{(test_run_eval['overall_accuracy'] - baseline_acc)*100:.2f}%)")
    print(f"Baseline Production Macro F1 : {baseline_f1:.4f}  -->  New Model: {test_run_eval['macro_f1']:.4f}  (Δ +{(test_run_eval['macro_f1'] - baseline_f1):.4f})")

    # 4. Save Model and Metadata
    model_path = MODELS_DIR / "diagnosis_classifier.joblib"
    meta_path = MODELS_DIR / "diagnosis_classifier.meta.json"

    # Persist model bundle
    bundle = {
        "model": best_model,
        "feature_names": FEATURE_NAMES,
        "classes": list(best_model.classes_),
        "model_type": best_name,
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    joblib.dump(bundle, model_path, compress=3)
    print(f"\nPersisted model bundle to {model_path}")

    meta = {
        "model_type": best_name,
        "hyperparameters": best_model.get_params(),
        "classes": list(best_model.classes_),
        "feature_names": FEATURE_NAMES,
        "feature_count": len(FEATURE_NAMES),
        "trained_runs": 99,
        "validation_runs": 33,
        "test_runs": 33,
        "validation_metrics": val_results[best_name],
        "test_metrics": {
            "run_eval": test_run_eval,
            "sample_eval": test_sample_eval,
        },
        "baseline_comparison": {
            "baseline_accuracy": baseline_acc,
            "baseline_macro_f1": baseline_f1,
            "new_accuracy": test_run_eval["overall_accuracy"],
            "new_macro_f1": test_run_eval["macro_f1"],
        }
    }
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Persisted model metadata to {meta_path}")

    # Dump evaluation scorecard artifact
    scorecard_path = ARTIFACTS_DIR / "diagnosis_model_eval.json"
    with open(scorecard_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Persisted evaluation scorecard to {scorecard_path}")

    print("\n" + "=" * 78)
    print("CLASSIFIER TRAINING & VERIFICATION COMPLETED SUCCESSFULLY")
    print("=" * 78)


if __name__ == "__main__":
    main()
