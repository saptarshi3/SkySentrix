import json
import csv
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pipeline import DigitalTwinPipeline
from scripts.trajectory_utils import FAULT_TYPES, run_fault_trajectory

RESULTS_DIR = Path(__file__).resolve().parents[1] / "validation_results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

WARMUP_SEC = 60
DURATION_SEC = 180
INJECT_AT = WARMUP_SEC
SEVERITY = 0.75
PROGRESSION = 0.01
STABILIZATION_WINDOW = 30
PRESET = "normal_endurance"

def run_one_fault(fault_type: str, seed: int) -> Dict:
    pipeline = DigitalTwinPipeline()
    frames, sim = run_fault_trajectory(
        pipeline,
        preset=PRESET,
        seed=seed,
        duration_sec=DURATION_SEC,
        fault_type=fault_type,
        severity=SEVERITY,
        progression_per_sec=PROGRESSION,
        inject_at_step=INJECT_AT,
    )

    diagnoses = [f.diagnosis.probable_fault for f in frames]
    confidences = [f.diagnosis.confidence for f in frames]
    anomaly_scores = [f.anomaly.score for f in frames]
    health_indices = [f.health.health_index for f in frames]
    ruls = [f.rul.current_rul_hours for f in frames]
    
    final_window_diagnoses = diagnoses[-STABILIZATION_WINDOW:]
    vote = Counter(final_window_diagnoses)
    predicted_fault = vote.most_common(1)[0][0]
    
    final_conf = confidences[-1]
    final_anomaly = anomaly_scores[-1]
    health_before = health_indices[INJECT_AT - 1]
    health_after = health_indices[-1]
    health_delta = health_after - health_before
    rul_before = ruls[INJECT_AT - 1]
    rul_after = ruls[-1]
    rul_delta = rul_after - rul_before
    
    final_evidence_dict = frames[-1].diagnosis.evidence
    if final_evidence_dict:
        sorted_evidence = sorted(final_evidence_dict.items(), key=lambda x: abs(x[1]), reverse=True)
        primary_evidence = ", ".join([f"{k}={v:.2f}" for k, v in sorted_evidence[:2]])
    else:
        primary_evidence = "None"
        
    detection_latency = None
    for step in range(INJECT_AT, DURATION_SEC):
        if (
            detection_latency is None
            and diagnoses[step] == fault_type
            and confidences[step] >= 0.5
        ):
            detection_latency = step - INJECT_AT

    return {
        "fault_type": fault_type,
        "predicted_fault": predicted_fault,
        "correct": predicted_fault == fault_type,
        "confidence": final_conf,
        "anomaly_score": final_anomaly,
        "health_before": health_before,
        "health_after": health_after,
        "health_delta": health_delta,
        "rul_before": rul_before,
        "rul_after": rul_after,
        "rul_delta": rul_delta,
        "primary_evidence": primary_evidence,
        "detection_latency": detection_latency
    }

def main():
    print("Starting Phase 1A & 1B Validation...")
    results = []
    print(f"{'Injected Fault':<25} {'Predicted Fault':<25} {'Conf':<6} {'Correct':<7} {'Anom':<6} {'H_Bef':<7} {'H_Aft':<7} {'H_Del':<7} {'RUL_Bef':<8} {'RUL_Aft':<8} {'RUL_Del':<8} {'Primary Evidence'}")
    print("-" * 140)
    for i, fault_type in enumerate(FAULT_TYPES):
        seed = 1000 + i
        res = run_one_fault(fault_type, seed)
        results.append(res)
        print(f"{res['fault_type']:<25} {res['predicted_fault']:<25} {res['confidence']:<6.2f} {str(res['correct']):<7} {res['anomaly_score']:<6.2f} {res['health_before']:<7.1f} {res['health_after']:<7.1f} {res['health_delta']:<7.1f} {res['rul_before']:<8.1f} {res['rul_after']:<8.1f} {res['rul_delta']:<8.1f} {res['primary_evidence']}")
        
    confusion = {f: {p: 0 for p in FAULT_TYPES + ["normal"]} for f in FAULT_TYPES}
    for r in results:
        confusion[r["fault_type"]][r["predicted_fault"]] += 1

    per_label_metrics = {}
    for f in FAULT_TYPES:
        tp = confusion[f].get(f, 0)
        fn = sum(confusion[f].values()) - tp
        fp = sum(1 for r in results if r["fault_type"] != f and r["predicted_fault"] == f)
        
        precision = tp / max(tp + fp, 1) if (tp + fp) > 0 else (1.0 if fp == 0 and tp == 0 else 0.0)
        recall = tp / max(tp + fn, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-9) if (precision + recall) > 0 else 0.0
        
        per_label_metrics[f] = {
            "precision": round(precision, 3), 
            "recall": round(recall, 3), 
            "f1": round(f1, 3),
            "accuracy": tp
        }
        
    n_correct = sum(1 for r in results if r["correct"])
    overall_accuracy = n_correct / len(results)
    macro_precision = sum(m["precision"] for m in per_label_metrics.values()) / len(per_label_metrics)
    macro_recall = sum(m["recall"] for m in per_label_metrics.values()) / len(per_label_metrics)
    macro_f1 = sum(m["f1"] for m in per_label_metrics.values()) / len(per_label_metrics)
    weighted_f1 = macro_f1
    
    with open(RESULTS_DIR / "diagnosis_confusion_matrix.json", "w") as f:
        json.dump(confusion, f, indent=2)
        
    with open(RESULTS_DIR / "diagnosis_confusion_matrix.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["True_Fault"] + FAULT_TYPES + ["normal"])
        for true_fault in FAULT_TYPES:
            writer.writerow([true_fault] + [confusion[true_fault].get(pred, 0) for pred in FAULT_TYPES + ["normal"]])
            
    metrics_report = {
        "overall_accuracy": round(overall_accuracy, 3),
        "macro_precision": round(macro_precision, 3),
        "macro_recall": round(macro_recall, 3),
        "macro_f1": round(macro_f1, 3),
        "weighted_f1": round(weighted_f1, 3),
        "per_fault_metrics": per_label_metrics
    }
    with open(RESULTS_DIR / "diagnosis_metrics.json", "w") as f:
        json.dump(metrics_report, f, indent=2)
        
    print("\nConfusion Matrix:")
    print(f"{'True / Pred':<25}", end="")
    for p in FAULT_TYPES: print(f"{p[:6]:<7}", end="")
    print()
    for true_fault in FAULT_TYPES:
        print(f"{true_fault:<25}", end="")
        for pred in FAULT_TYPES: print(f"{confusion[true_fault][pred]:<7}", end="")
        print()
        
    print("\nMetrics:")
    print(json.dumps(metrics_report, indent=2))

if __name__ == "__main__":
    main()
