"""
Phase 1E: Anomaly Detection Validation - Light contamination sweep.
Tests contamination values 0.01 to 0.10 on a compact split for speed.
"""
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.analytics.anomaly import AnomalyEngine, DEFAULT_WEIGHTS
from app.services.pipeline import DigitalTwinPipeline
from scripts.trajectory_utils import (
    FAULT_TYPES, PRESETS, labels_for_fault_trajectory,
    run_fault_trajectory, run_healthy_trajectory,
)

RESULTS_DIR = Path(__file__).resolve().parents[1] / "validation_results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

WARMUP_STEPS = 5
DURATION = 120
INJECT_AT = 40
DETECT_DELAY = 15


def collect_healthy_features(seeds, duration_sec):
    collector = AnomalyEngine(auto_load=False)
    pipeline = DigitalTwinPipeline()
    feats = []
    for preset in PRESETS:
        for seed in seeds:
            pipeline.reset_state()
            collector.reset_state()
            frames = run_healthy_trajectory(pipeline, preset, seed, duration_sec)
            for step, frame in enumerate(frames):
                if step >= WARMUP_STEPS:
                    feats.append(collector.build_feature_vector(frame.telemetry, frame.residuals))
                collector.prev_points.append(frame.telemetry)
    return np.array(feats, dtype=float)


def build_split(healthy_seeds, fault_seed_start, duration_sec):
    pipeline = DigitalTwinPipeline()
    trajectories = []
    for preset in PRESETS[:2]:  # Only 2 presets for speed
        for seed in healthy_seeds:
            frames = run_healthy_trajectory(pipeline, preset, seed, duration_sec)
            trajectories.append((frames, [False] * duration_sec, f"healthy:{preset}:{seed}"))
    for i, fault_type in enumerate(FAULT_TYPES[:5]):  # Only 5 faults for speed
        seed = fault_seed_start + i
        preset = PRESETS[i % 2]
        frames, _ = run_fault_trajectory(
            pipeline, preset, seed, duration_sec, fault_type,
            severity=0.75, progression_per_sec=0.01, inject_at_step=INJECT_AT,
        )
        labels = labels_for_fault_trajectory(duration_sec, INJECT_AT, DETECT_DELAY)
        trajectories.append((frames, labels, f"fault:{fault_type}:{preset}:{seed}"))
    return trajectories


def evaluate(engine_factory, trajectories):
    tp = fp = tn = fn = 0
    latencies = []
    for frames, labels, tag in trajectories:
        engine = engine_factory()
        is_fault = tag.startswith("fault:")
        inject_step = None
        detected_step = None
        for step, (frame, label) in enumerate(zip(frames, labels)):
            result = engine.score(frame.telemetry, frame.residuals)
            pred = result.level in {"WARNING", "CRITICAL"}
            if is_fault and inject_step is None and label:
                inject_step = step
            if label and pred:
                tp += 1
                if is_fault and detected_step is None:
                    detected_step = step
            elif label and not pred:
                fn += 1
            elif not label and pred:
                fp += 1
            else:
                tn += 1
        if is_fault and inject_step is not None and detected_step is not None:
            latencies.append(float(detected_step - inject_step))
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)
    far = fp / max(fp + tn, 1)
    mean_latency = float(np.mean(latencies)) if latencies else None
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_alarm_rate": round(far, 4),
        "mean_detection_latency_sec": round(mean_latency, 2) if mean_latency is not None else None,
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
    }


def main():
    t0 = time.time()
    print("Collecting train features...")
    train_feats = collect_healthy_features([101], DURATION)
    print(f"  train_feats.shape = {train_feats.shape}")

    print("Building eval split...")
    split = build_split([401], 501, DURATION)
    print(f"  {len(split)} trajectories")

    contamination_values = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10]
    sweep_results = []

    print(f"\n{'Contamination':<15} {'Precision':<11} {'Recall':<9} {'F1':<8} {'FAR':<8} {'Latency'}")
    print("-" * 70)
    best_f1 = -1
    best_contamination = None

    for contamination in contamination_values:
        engine = AnomalyEngine(contamination=contamination, auto_load=False)
        engine.fit_from_feature_matrix(train_feats, source="phase1e_sweep")
        scaler = engine.scaler
        model = engine.model
        score_mean = engine.score_mean
        score_std = engine.score_std

        def make_engine(c=contamination, sc=scaler, mo=model, sm=score_mean, ss=score_std):
            e = AnomalyEngine(contamination=c, auto_load=False)
            e.scaler = sc
            e.model = mo
            e.score_mean = sm
            e.score_std = ss
            e.training_source = "phase1e_sweep"
            return e

        metrics = evaluate(make_engine, split)
        metrics["contamination"] = contamination
        sweep_results.append(metrics)

        print(f"{contamination:<15.2f} {metrics['precision']:<11.4f} {metrics['recall']:<9.4f} {metrics['f1']:<8.4f} {metrics['false_alarm_rate']:<8.4f} {metrics['mean_detection_latency_sec']}")

        if metrics["f1"] > best_f1:
            best_f1 = metrics["f1"]
            best_contamination = contamination

    print(f"\nBest contamination = {best_contamination} (F1={best_f1:.4f})")

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "methodology": "Light sweep: 2 presets, 5 faults, seed 401/501, duration=120s",
        "contamination_sweep": sweep_results,
        "best_contamination": best_contamination,
        "best_f1": round(best_f1, 4),
        "elapsed_sec": round(time.time() - t0, 1),
    }
    out = RESULTS_DIR / "anomaly_contamination_sweep.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"\nReport saved to {out}")


if __name__ == "__main__":
    main()
