from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy.orm import Session

from app.engine.simulator import EngineSimulator
from app.services.pipeline import DigitalTwinPipeline


@dataclass
class ScenarioResult:
    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0
    detection_step: Optional[int] = None
    fault_start_step: Optional[int] = None


def _synthetic_true_rul(
    degradation_idx: float,
    elapsed_hours: float,
    first_deg: float,
    failure_threshold: float = 80.0,
) -> float:
    rem = max(0.0, failure_threshold - degradation_idx)
    if elapsed_hours <= 1e-6:
        return rem / 0.25
    rate = max(0.08, (degradation_idx - first_deg) / elapsed_hours)
    return rem / rate


def _run_scenario(
    db: Session,
    *,
    sim: EngineSimulator,
    pipeline: DigitalTwinPipeline,
    steps: int,
    fault: Optional[Tuple[int, str, float, float]] = None,
    fault_detection_delay: int = 18,
) -> tuple[ScenarioResult, Dict[str, List[float]], List[float]]:
    out = ScenarioResult()
    residual_series: Dict[str, List[float]] = {
        "rpm": [],
        "egt": [],
        "cht": [],
        "oil_pressure": [],
        "oil_temp": [],
        "fuel_flow": [],
        "vibration": [],
        "battery_voltage": [],
        "manifold_pressure": [],
        "torque_nm": [],
    }
    rul_abs_errors: List[float] = []

    elapsed_h = 0.0
    first_deg: Optional[float] = None

    for step in range(steps):
        if fault is not None and step == fault[0]:
            _, ftype, sev, prog = fault
            sim.inject_fault(ftype, severity=sev, progression_per_sec=prog)
            out.fault_start_step = fault[0]

        point = sim.step(1.0)
        frame = pipeline.process(db, point)

        for k in residual_series:
            residual_series[k].append(frame.residuals[k].residual)

        # synthetic degradation truth from simulator hidden subsystem state
        deg_idx = max(0.0, min(100.0, (1.0 - sim.subsystem_health.overall) * 100.0))
        if first_deg is None:
            first_deg = deg_idx
        elapsed_h += 1.0 / 3600.0
        true_rul = _synthetic_true_rul(deg_idx, elapsed_h, first_deg)
        rul_abs_errors.append(abs(frame.rul.current_rul_hours - true_rul))

        if fault is None:
            is_true_anomaly = False
        else:
            is_true_anomaly = step >= (fault[0] + fault_detection_delay)

        residual_trigger = (
            (abs(frame.residuals["fuel_flow"].residual_pct) > 12.0 and abs(frame.residuals["egt"].residual_pct) > 5.0)
            or abs(frame.residuals["vibration"].residual_pct) > 15.0
            or abs(frame.residuals["rpm"].residual_pct) > 8.0
        )

        is_pred_anomaly = (
            frame.anomaly.level in {"WARNING", "CRITICAL"}
            or (
                residual_trigger
                and frame.diagnosis.probable_fault != "normal"
                and frame.diagnosis.confidence >= 0.55
            )
        )

        if is_true_anomaly and is_pred_anomaly:
            out.tp += 1
            if out.detection_step is None:
                out.detection_step = step
        elif is_true_anomaly and not is_pred_anomaly:
            out.fn += 1
        elif (not is_true_anomaly) and is_pred_anomaly:
            out.fp += 1
        else:
            out.tn += 1

    return out, residual_series, rul_abs_errors


def run_synthetic_validation(db: Session) -> Dict[str, float | Dict[str, int] | Dict[str, float] | str]:
    # Scenario A: baseline profile + progressive injector fault
    sim_a = EngineSimulator(seed=2026)
    sim_a.load_mission("normal_endurance", duration_sec=720, mission_name="validation_fault_case")
    pipe_a = DigitalTwinPipeline(engine_id="VAL-ENGINE-A")

    # Scenario B: unseen high-altitude profile (no explicit fault) for domain-shift false-alarm check
    sim_b = EngineSimulator(seed=2027)
    sim_b.load_mission("high_altitude", duration_sec=600, mission_name="validation_domain_shift")
    pipe_b = DigitalTwinPipeline(engine_id="VAL-ENGINE-B")

    res_a, residuals_a, rul_err_a = _run_scenario(
        db,
        sim=sim_a,
        pipeline=pipe_a,
        steps=620,
        fault=(190, "injector_degradation", 0.70, 0.007),
        fault_detection_delay=18,
    )
    res_b, residuals_b, rul_err_b = _run_scenario(
        db,
        sim=sim_b,
        pipeline=pipe_b,
        steps=420,
        fault=None,
        fault_detection_delay=18,
    )

    tp = res_a.tp + res_b.tp
    fp = res_a.fp + res_b.fp
    tn = res_a.tn + res_b.tn
    fn = res_a.fn + res_b.fn

    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    false_alarm_rate = fp / max(fp + tn, 1)
    f1 = 2.0 * precision * recall / max(precision + recall, 1e-9)

    if res_a.detection_step is None or res_a.fault_start_step is None:
        detection_latency_sec = float("inf")
    else:
        detection_latency_sec = max(0, res_a.detection_step - res_a.fault_start_step)

    # Twin prediction error metrics from residual series (RMSE only for response compatibility)
    merged_residuals: Dict[str, List[float]] = {}
    for key in residuals_a:
        merged_residuals[key] = residuals_a[key] + residuals_b[key]

    twin_rmse = {
        key: round(float(np.sqrt(np.mean(np.square(vals)))) if vals else 0.0, 4)
        for key, vals in merged_residuals.items()
    }

    rul_errors = rul_err_a + rul_err_b
    rul_mae_hours = float(np.mean(rul_errors)) if rul_errors else 0.0
    rul_rmse_hours = float(np.sqrt(np.mean(np.square(rul_errors)))) if rul_errors else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "false_alarm_rate": round(false_alarm_rate, 4),
        "detection_latency_sec": round(float(detection_latency_sec), 2) if np.isfinite(detection_latency_sec) else -1.0,
        "f1": round(f1, 4),
        "twin_rmse": twin_rmse,
        "confusion_matrix": {
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
        },
        "rul_mae_hours": round(rul_mae_hours, 3),
        "rul_rmse_hours": round(rul_rmse_hours, 3),
        "notes": (
            "Validation uses synthetic mission trajectories with trajectory-level split "
            "(faulted normal-endurance vs unseen high-altitude profile). Metrics are prototype indicators only."
        ),
    }
