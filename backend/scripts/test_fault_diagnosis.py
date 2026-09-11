"""
Tier-1 Item 3: Fault diagnosis audit across all 10 implemented faults.

For each fault:
  1. Run healthy warmup.
  2. Inject the fault.
  3. Run for a fixed duration.
  4. Record anomaly score/level, diagnosis + confidence, per step.
  5. Determine "final predicted fault" = majority vote of diagnosis.probable_fault
     over the LAST 30 samples of the run (a stabilization window), excluding
     'normal' unless it is genuinely the majority.
  6. Detection latency = first step (after injection) where diagnosis.probable_fault
     == true fault AND confidence >= 0.5, relative to injection step.

Builds a confusion matrix (true fault x predicted fault) and macro P/R/F1.

DATA PROVENANCE: 100% synthetic (EngineSimulator + controlled fault injection).
This is NOT validated against any real engine fault dataset.
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pipeline import DigitalTwinPipeline  # noqa: E402
from scripts.trajectory_utils import FAULT_TYPES, run_fault_trajectory  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parents[1] / "validation_results"

WARMUP_SEC = 60
DURATION_SEC = 180  # total, including warmup
INJECT_AT = WARMUP_SEC
SEVERITY = 0.75
PROGRESSION = 0.01
STABILIZATION_WINDOW = 30
CONFIDENCE_THRESHOLD_FOR_LATENCY = 0.5

ALL_LABELS = FAULT_TYPES + ["normal"]


def run_one_fault(pipeline: DigitalTwinPipeline, fault_type: str, seed: int) -> Dict:
    frames, sim = run_fault_trajectory(
        pipeline,
        preset="normal_endurance",
        seed=seed,
        duration_sec=DURATION_SEC,
        fault_type=fault_type,
        severity=SEVERITY,
        progression_per_sec=PROGRESSION,
        inject_at_step=INJECT_AT,
    )

    diagnoses = [f.diagnosis.probable_fault for f in frames]
    confidences = [f.diagnosis.confidence for f in frames]
    anomaly_levels = [f.anomaly.level for f in frames]

    final_window = diagnoses[-STABILIZATION_WINDOW:]
    vote = Counter(final_window)
    predicted_fault = vote.most_common(1)[0][0]

    detection_latency = None
    first_anomaly_step = None
    for step in range(INJECT_AT, DURATION_SEC):
        if first_anomaly_step is None and anomaly_levels[step] in {"WARNING", "CRITICAL"}:
            first_anomaly_step = step - INJECT_AT
        if (
            detection_latency is None
            and diagnoses[step] == fault_type
            and confidences[step] >= CONFIDENCE_THRESHOLD_FOR_LATENCY
        ):
            detection_latency = step - INJECT_AT

    return {
        "fault_type": fault_type,
        "predicted_fault": predicted_fault,
        "correct": predicted_fault == fault_type,
        "final_window_vote": dict(vote),
        "diagnosis_confidence_at_end": round(confidences[-1], 4),
        "detection_latency_sec": detection_latency,
        "first_anomaly_latency_sec": first_anomaly_step,
        "max_confidence_observed": round(max(confidences[INJECT_AT:]), 4),
        "final_severity": round(sim.get_faults().get(fault_type, {}).get("current_severity", 0.0), 4),
    }


def main() -> None:
    t_start = time.time()
    pipeline = DigitalTwinPipeline()

    per_fault_results = []
    for i, fault_type in enumerate(FAULT_TYPES):
        seed = 700 + i
        result = run_one_fault(pipeline, fault_type, seed)
        per_fault_results.append(result)
        status = "CORRECT" if result["correct"] else "INCORRECT"
        print(
            f"{fault_type:26s} -> predicted={result['predicted_fault']:26s} "
            f"[{status}] conf_end={result['diagnosis_confidence_at_end']} "
            f"latency={result['detection_latency_sec']}"
        )

    # Confusion matrix: rows = true fault, cols = predicted fault (only over fault labels)
    confusion: Dict[str, Dict[str, int]] = {f: defaultdict(int) for f in FAULT_TYPES}
    for r in per_fault_results:
        confusion[r["fault_type"]][r["predicted_fault"]] += 1

    # Macro precision/recall/F1 computed per fault label (one trial per fault, so this
    # is a small-sample macro average; treat as indicative, not statistically robust).
    per_label_metrics = {}
    for f in FAULT_TYPES:
        tp = 1 if confusion[f].get(f, 0) > 0 else 0
        fn = 1 - tp
        # false positives for label f: other true-faults predicted as f
        fp = sum(1 for r in per_fault_results if r["fault_type"] != f and r["predicted_fault"] == f)
        precision = tp / max(tp + fp, 1) if (tp + fp) > 0 else (1.0 if fp == 0 and tp == 0 else 0.0)
        recall = tp / max(tp + fn, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-9) if (precision + recall) > 0 else 0.0
        per_label_metrics[f] = {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3)}

    n_correct = sum(1 for r in per_fault_results if r["correct"])
    accuracy = n_correct / len(per_fault_results)
    macro_f1 = sum(m["f1"] for m in per_label_metrics.values()) / len(per_label_metrics)

    latencies = [r["detection_latency_sec"] for r in per_fault_results if r["detection_latency_sec"] is not None]
    mean_latency = sum(latencies) / len(latencies) if latencies else None

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "config": {
            "warmup_sec": WARMUP_SEC,
            "duration_sec": DURATION_SEC,
            "severity": SEVERITY,
            "progression_per_sec": PROGRESSION,
            "stabilization_window": STABILIZATION_WINDOW,
            "confidence_threshold_for_latency": CONFIDENCE_THRESHOLD_FOR_LATENCY,
        },
        "per_fault_results": per_fault_results,
        "confusion_matrix": {k: dict(v) for k, v in confusion.items()},
        "per_label_metrics": per_label_metrics,
        "accuracy": round(accuracy, 3),
        "macro_f1": round(macro_f1, 3),
        "correctly_identified_count": n_correct,
        "total_faults_tested": len(per_fault_results),
        "mean_detection_latency_sec": round(mean_latency, 2) if mean_latency is not None else None,
        "faults_with_no_detection": [
            r["fault_type"] for r in per_fault_results if r["detection_latency_sec"] is None
        ],
        "elapsed_sec": round(time.time() - t_start, 1),
    }

    print(f"\nAccuracy: {n_correct}/{len(per_fault_results)} = {accuracy:.3f}")
    print(f"Macro F1: {macro_f1:.3f}")
    print(f"Faults with no confident detection: {report['faults_with_no_detection']}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "fault_diagnosis_audit.json"
    out_path.write_text(json.dumps(report, indent=2, default=str))
    print(f"\nFull report written to {out_path}")


if __name__ == "__main__":
    main()
