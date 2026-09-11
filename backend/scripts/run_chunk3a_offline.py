"""
Offline Standalone Training and Evaluation of Fault Diagnosis Classifier.
Strictly loads existing cached data from backend/data/*.joblib.
Does NOT invoke simulator or live pipeline.
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
from sklearn.metrics import classification_report, confusion_matrix, f1_score, precision_score, recall_score, accuracy_score
from sklearn.model_selection import GroupKFold

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"
ARTIFACTS_DIR = BACKEND_DIR / "artifacts"
MODELS_DIR = BACKEND_DIR / "models"

sys.path.insert(0, str(BACKEND_DIR))
from app.analytics.feature_extractor import FEATURE_NAMES

def main():
    start_time = time.time()
    print("=" * 80)
    print("CHUNK 3A: OFFLINE FAULT CLASSIFIER TRAINING (CACHED DATA ONLY)")
    print("=" * 80)

    # 1. Verify FEATURE_NAMES assertion
    print(f"\n--- STEP 1: VERIFY FEATURE NAMES ---")
    print(f"Number of engineered features in FEATURE_NAMES: {len(FEATURE_NAMES)}")
    assert len(FEATURE_NAMES) == 39, f"Assertion failed: expected 39 features, got {len(FEATURE_NAMES)}"
    print(f"Features (39): {FEATURE_NAMES}")

    # 2. Load cached DataFrames
    print(f"\n--- STEP 2: LOAD EXISTING CACHED DATA ---")
    train_path = DATA_DIR / "train_data.joblib"
    val_path = DATA_DIR / "val_data.joblib"
    test_path = DATA_DIR / "test_data.joblib"

    if not (train_path.exists() and val_path.exists() and test_path.exists()):
        raise FileNotFoundError("Cached dataset joblib files not found in backend/data/!")

    print(f"Loading {train_path} ...")
    df_train = joblib.load(train_path)
    print(f"Loading {val_path} ...")
    df_val = joblib.load(val_path)
    print(f"Loading {test_path} ...")
    df_test = joblib.load(test_path)

    print(f"\nDataset Shapes:")
    print(f"  Train:      {df_train.shape}")
    print(f"  Validation: {df_val.shape}")
    print(f"  Test:       {df_test.shape}")

    metadata_cols = [c for c in df_train.columns if c not in FEATURE_NAMES]
    print(f"\nMetadata columns ({len(metadata_cols)}): {metadata_cols}")
    print(f"Engineered feature count: {len(FEATURE_NAMES)}")

    # Run counts and distributions
    print(f"\nDataset Summary Statistics:")
    print(f"  Train:      {df_train['run_id'].nunique()} unique runs, {df_train['seed'].nunique()} unique seeds, {list(df_train['preset'].unique())} presets")
    print(f"  Validation: {df_val['run_id'].nunique()} unique runs, {df_val['seed'].nunique()} unique seeds, {list(df_val['preset'].unique())} presets")
    print(f"  Test:       {df_test['run_id'].nunique()} unique runs, {df_test['seed'].nunique()} unique seeds, {list(df_test['preset'].unique())} presets")

    print(f"\nClass distributions (effective_label):")
    print(f"  Train:\n{df_train['effective_label'].value_counts().to_string()}")
    print(f"  Validation:\n{df_val['effective_label'].value_counts().to_string()}")
    print(f"  Test:\n{df_test['effective_label'].value_counts().to_string()}")

    # 3. Leakage Checks
    print(f"\n--- STEP 3: STRICT DATA LEAKAGE CHECKS ---")
    train_runs = set(df_train["run_id"].unique())
    val_runs = set(df_val["run_id"].unique())
    test_runs = set(df_test["run_id"].unique())

    overlap_tr_val = len(train_runs.intersection(val_runs))
    overlap_tr_te = len(train_runs.intersection(test_runs))
    overlap_val_te = len(val_runs.intersection(test_runs))

    print(f"  TRAIN INTERSECT VAL runs  = {overlap_tr_val}")
    print(f"  TRAIN INTERSECT TEST runs = {overlap_tr_te}")
    print(f"  VAL INTERSECT TEST runs   = {overlap_val_te}")

    assert overlap_tr_val == 0, "Data leakage: Train and Val runs overlap!"
    assert overlap_tr_te == 0, "Data leakage: Train and Test runs overlap!"
    assert overlap_val_te == 0, "Data leakage: Val and Test runs overlap!"

    # Verify no metadata in feature matrix
    for prohibited in ["run_id", "step", "seed", "preset", "target_fault", "effective_label", "is_active_fault", "target_severity", "is_transient", "anomaly_score"]:
        assert prohibited not in FEATURE_NAMES, f"Data leakage: {prohibited} in FEATURE_NAMES!"
    print("  CONFIRMED: Zero metadata or label columns in FEATURE_NAMES.")

    # 4. Construct Feature Matrices
    X_train = df_train[FEATURE_NAMES].values
    y_train = df_train["effective_label"].values
    groups_train = df_train["run_id"].values

    X_val = df_val[FEATURE_NAMES].values
    y_val = df_val["effective_label"].values

    X_test = df_test[FEATURE_NAMES].values
    y_test = df_test["effective_label"].values

    classes = sorted(list(np.unique(y_train)))
    print(f"\nTarget Classes ({len(classes)}): {classes}")

    # 5. Model Candidates
    print(f"\n--- STEP 4: MODEL CANDIDATES & GROUP-K-FOLD CV (5 folds on TRAIN) ---")
    candidates = {
        "RandomForest_300": RandomForestClassifier(
            n_estimators=300,
            max_depth=18,
            min_samples_split=4,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        ),
        "ExtraTrees_300": ExtraTreesClassifier(
            n_estimators=300,
            max_depth=18,
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

    gkf = GroupKFold(n_splits=5)
    cv_summary = {}

    for name, clf in candidates.items():
        t_cv0 = time.time()
        accs = []
        precs = []
        recs = []
        f1s = []

        for fold, (trn_idx, vld_idx) in enumerate(gkf.split(X_train, y_train, groups=groups_train), 1):
            clf.fit(X_train[trn_idx], y_train[trn_idx])
            y_pred = clf.predict(X_train[vld_idx])
            accs.append(accuracy_score(y_train[vld_idx], y_pred))
            precs.append(precision_score(y_train[vld_idx], y_pred, average="macro", zero_division=0))
            recs.append(recall_score(y_train[vld_idx], y_pred, average="macro", zero_division=0))
            f1s.append(f1_score(y_train[vld_idx], y_pred, average="macro", zero_division=0))

        cv_time = time.time() - t_cv0
        cv_summary[name] = {
            "acc_mean": float(np.mean(accs)),
            "acc_std": float(np.std(accs)),
            "prec_mean": float(np.mean(precs)),
            "prec_std": float(np.std(precs)),
            "rec_mean": float(np.mean(recs)),
            "rec_std": float(np.std(recs)),
            "f1_mean": float(np.mean(f1s)),
            "f1_std": float(np.std(f1s)),
            "time_sec": cv_time,
        }
        print(f"[{name:22s}] CV Acc: {np.mean(accs)*100:.2f}% +/- {np.std(accs)*100:.2f}% | "
              f"Macro F1: {np.mean(f1s):.4f} +/- {np.std(f1s):.4f} | "
              f"Macro Prec: {np.mean(precs):.4f} +/- {np.std(precs):.4f} | "
              f"Macro Rec: {np.mean(recs):.4f} +/- {np.std(recs):.4f} ({cv_time:.1f}s)")

    # 6. Fit candidates on full TRAIN and Evaluate on VALIDATION
    print(f"\n--- STEP 5: EVALUATION ON VALIDATION DATASET ---")
    val_summary = {}
    fitted_models = {}

    for name, clf in candidates.items():
        t_fit = time.time()
        clf.fit(X_train, y_train)
        fitted_models[name] = clf

        val_pred = clf.predict(X_val)
        val_acc = accuracy_score(y_val, val_pred)
        val_prec = precision_score(y_val, val_pred, average="macro", zero_division=0)
        val_rec = recall_score(y_val, val_pred, average="macro", zero_division=0)
        val_f1 = f1_score(y_val, val_pred, average="macro", zero_division=0)
        val_wf1 = f1_score(y_val, val_pred, average="weighted", zero_division=0)

        # Also calculate run-level accuracy on validation (tail 30 steps majority vote per run)
        val_run_correct = 0
        val_run_total = 0
        for rid in df_val["run_id"].unique():
            rdf = df_val[df_val["run_id"] == rid].sort_values("step").tail(30)
            target = rdf["target_fault"].iloc[0]
            preds = clf.predict(rdf[FEATURE_NAMES].values)
            majority_vote = Counter(preds).most_common(1)[0][0]
            if majority_vote == target:
                val_run_correct += 1
            val_run_total += 1
        val_run_acc = val_run_correct / val_run_total

        val_summary[name] = {
            "sample_acc": float(val_acc),
            "macro_prec": float(val_prec),
            "macro_rec": float(val_rec),
            "macro_f1": float(val_f1),
            "weighted_f1": float(val_wf1),
            "run_acc": float(val_run_acc),
            "run_correct": val_run_correct,
            "run_total": val_run_total,
            "fit_time_sec": time.time() - t_fit,
        }

        print(f"[{name:22s}] Val Sample Acc: {val_acc*100:.2f}% | Val Macro F1: {val_f1:.4f} | "
              f"Val Macro Prec: {val_prec:.4f} | Val Macro Rec: {val_rec:.4f} | "
              f"Val Run Acc (majority vote): {val_run_acc*100:.1f}% ({val_run_correct}/{val_run_total})")

    # Select Best Model based on Validation Macro F1 (primary) and Accuracy (secondary)
    best_name = max(candidates.keys(), key=lambda k: (val_summary[k]["macro_f1"], val_summary[k]["sample_acc"]))
    best_model = fitted_models[best_name]
    print(f"\n--> Selected Model based on Validation: {best_name}")
    print(f"    Validation Macro F1: {val_summary[best_name]['macro_f1']:.4f}")
    print(f"    Validation Sample Acc: {val_summary[best_name]['sample_acc']*100:.2f}%")

    # 7. Single Evaluation on VIRGIN TEST SET
    print(f"\n--- STEP 6: SINGLE EVALUATION ON VIRGIN TEST DATASET ---")
    test_pred = best_model.predict(X_test)
    has_proba = hasattr(best_model, "predict_proba")
    test_proba = best_model.predict_proba(X_test) if has_proba else None

    test_acc = accuracy_score(y_test, test_pred)
    test_prec = precision_score(y_test, test_pred, average="macro", zero_division=0)
    test_rec = recall_score(y_test, test_pred, average="macro", zero_division=0)
    test_f1 = f1_score(y_test, test_pred, average="macro", zero_division=0)
    test_wf1 = f1_score(y_test, test_pred, average="weighted", zero_division=0)

    print(f"Virgin Test Sample Accuracy  : {test_acc*100:.2f}%")
    print(f"Virgin Test Macro Precision  : {test_prec:.4f}")
    print(f"Virgin Test Macro Recall     : {test_rec:.4f}")
    print(f"Virgin Test Macro F1         : {test_f1:.4f}")
    print(f"Virgin Test Weighted F1      : {test_wf1:.4f}")
    print(f"Supports predict_proba()     : {has_proba} (Model probability exposed; uncalibrated)")

    # Per-Class Metrics
    rep = classification_report(y_test, test_pred, output_dict=True, zero_division=0)
    print(f"\nPer-Class Breakdown on Virgin Test Set:")
    print(f"{'Class':<28} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'Support':<8}")
    print("-" * 75)
    per_class_results = {}
    for cl in classes:
        p = rep[cl]["precision"]
        r = rep[cl]["recall"]
        f = rep[cl]["f1-score"]
        s = rep[cl]["support"]
        per_class_results[cl] = {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f, 4), "support": int(s)}
        print(f"{cl:<28} | {p:<10.4f} | {r:<10.4f} | {f:<10.4f} | {s:<8}")

    # Confusion Matrix
    cm = confusion_matrix(y_test, test_pred, labels=classes)
    hdr = "True / Pred"
    col_hdrs = " ".join(f"{c[:4]:>5}" for c in classes)
    print(f"\nConfusion Matrix on Virgin Test Set (Rows=True, Cols=Predicted):")
    print(f"{hdr:<26} {col_hdrs}")
    for i, cl in enumerate(classes):
        row_str = " ".join(f"{cm[i, j]:>5}" for j in range(len(classes)))
        print(f"{cl:<26} {row_str}")

    # Run-level test evaluation (steady-state majority vote over last 30 steps)
    test_run_correct = 0
    test_run_total = 0
    run_breakdown = defaultdict(lambda: {"correct": 0, "total": 0})
    for rid in df_test["run_id"].unique():
        rdf = df_test[df_test["run_id"] == rid].sort_values("step").tail(30)
        target = rdf["target_fault"].iloc[0]
        preds = best_model.predict(rdf[FEATURE_NAMES].values)
        maj = Counter(preds).most_common(1)[0][0]
        is_corr = (maj == target)
        if is_corr:
            test_run_correct += 1
            run_breakdown[target]["correct"] += 1
        run_breakdown[target]["total"] += 1
        test_run_total += 1
    test_run_acc = test_run_correct / test_run_total
    print(f"\nVirgin Test Run-Level Accuracy (30-step majority vote): {test_run_acc*100:.2f}% ({test_run_correct}/{test_run_total} runs)")

    # 8. Feature Importance
    print(f"\n--- STEP 7: FEATURE IMPORTANCE ANALYSIS ---")
    feature_importances = {}
    if hasattr(best_model, "feature_importances_"):
        imps = best_model.feature_importances_
        sorted_idx = np.argsort(imps)[::-1]
        print("Top 15 Most Important Features:")
        for rank, idx in enumerate(sorted_idx[:15], 1):
            fname = FEATURE_NAMES[idx]
            imp_val = float(imps[idx])
            feature_importances[fname] = round(imp_val, 4)
            print(f"  {rank:2d}. {fname:<32} : {imp_val:.4f}")
    else:
        print("Model does not expose feature_importances_ directly.")

    # 9. Persist Model and Metadata
    print(f"\n--- STEP 8: PERSIST MODEL AND METADATA ---")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_file = MODELS_DIR / "diagnosis_classifier.joblib"
    meta_file = MODELS_DIR / "diagnosis_classifier_metadata.json"

    bundle = {
        "model": best_model,
        "feature_names": FEATURE_NAMES,
        "classes": list(best_model.classes_),
        "model_type": best_name,
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    joblib.dump(bundle, model_file, compress=3)
    print(f"Saved model bundle to: {model_file}")

    metadata = {
        "model_type": best_name,
        "hyperparameters": {k: str(v) if not isinstance(v, (int, float, bool, str, type(None))) else v for k, v in best_model.get_params().items()},
        "classes": list(best_model.classes_),
        "feature_count": len(FEATURE_NAMES),
        "feature_names": FEATURE_NAMES,
        "random_seed": 42,
        "training_date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dataset_info": {
            "train_samples": len(df_train),
            "train_runs": int(df_train["run_id"].nunique()),
            "val_samples": len(df_val),
            "val_runs": int(df_val["run_id"].nunique()),
            "test_samples": len(df_test),
            "test_runs": int(df_test["run_id"].nunique()),
        },
        "group_kfold_cv_metrics": cv_summary,
        "validation_metrics": val_summary[best_name],
        "test_metrics": {
            "accuracy": round(test_acc, 4),
            "macro_precision": round(test_prec, 4),
            "macro_recall": round(test_rec, 4),
            "macro_f1": round(test_f1, 4),
            "weighted_f1": round(test_wf1, 4),
            "run_level_accuracy": round(test_run_acc, 4),
            "per_class": per_class_results,
            "confusion_matrix": {classes[i]: {classes[j]: int(cm[i, j]) for j in range(len(classes))} for i in range(len(classes))},
        },
        "top_feature_importances": feature_importances,
    }

    with open(meta_file, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved model metadata to: {meta_file}")

    total_time = time.time() - start_time
    print(f"\nExecution finished in {total_time:.1f} seconds ({total_time/60:.2f} minutes).")
    print("=" * 80)

if __name__ == "__main__":
    main()
