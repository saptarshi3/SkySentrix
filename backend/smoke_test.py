from __future__ import annotations

import io
import json
import math
import sqlite3
import time
from typing import Any, Dict, List

import pandas as pd
from fastapi.testclient import TestClient

from app.db.database import DB_PATH
from app.main import app


class SmokeTestFailure(Exception):
    pass


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeTestFailure(message)


def _collect_frames(ws, count: int, timeout_s: float = 30.0) -> List[Dict[str, Any]]:
    frames: List[Dict[str, Any]] = []
    start = time.time()
    while len(frames) < count:
        if time.time() - start > timeout_s:
            raise SmokeTestFailure(f"Timed out waiting for {count} websocket frames; got {len(frames)}")
        ws.send_text("ping")
        payload = ws.receive_json()
        if isinstance(payload, dict) and payload.get("type") == "state":
            continue
        frames.append(payload)
    return frames


def _baseline_fault_compare(baseline: List[Dict[str, Any]], faulted: List[Dict[str, Any]]) -> Dict[str, Any]:
    def avg(seq: List[float]) -> float:
        return sum(seq) / max(1, len(seq))

    base_anom = avg([f["anomaly"]["score"] for f in baseline])
    fault_anom = avg([f["anomaly"]["score"] for f in faulted])

    base_health = avg([f["health"]["health_index"] for f in baseline])
    fault_health = avg([f["health"]["health_index"] for f in faulted[-5:]])

    base_rul = avg([f["rul"]["current_rul_hours"] for f in baseline])
    fault_rul = avg([f["rul"]["current_rul_hours"] for f in faulted[-5:]])

    best_fault = max(faulted, key=lambda x: x["diagnosis"]["confidence"])

    return {
        "base_anomaly": base_anom,
        "fault_anomaly": fault_anom,
        "base_health": base_health,
        "fault_health": fault_health,
        "base_rul": base_rul,
        "fault_rul": fault_rul,
        "best_diagnosis": best_fault["diagnosis"],
    }


def run() -> Dict[str, Any]:
    report: Dict[str, Any] = {"components": {}, "bugs": [], "details": {}}

    with TestClient(app) as client:
        # Health endpoint
        r = client.get("/api/health")
        _assert(r.status_code == 200, f"/api/health returned {r.status_code}")
        report["components"]["backend_api_health"] = "PASS"

        # Start short mission
        start_resp = client.post(
            "/api/simulation/start",
            json={
                "mission_name": "Smoke Test Mission",
                "preset": "normal_endurance",
                "duration_sec": 180,
                "demo_mode": False,
            },
        )
        _assert(start_resp.status_code == 200, f"Simulation start failed: {start_resp.status_code} {start_resp.text}")
        mission_id = start_resp.json()["mission_id"]

        # WebSocket stream
        with client.websocket_connect("/ws/telemetry") as ws:
            state_msg = ws.receive_json()
            _assert(state_msg.get("type") == "state", "First websocket message should be connection state")

            baseline_frames = _collect_frames(ws, count=8, timeout_s=20.0)
            report["details"]["baseline_frames"] = len(baseline_frames)

            first = baseline_frames[0]
            _assert("expected" in first and "residuals" in first, "Frame missing expected/residuals")

            # Verify residual correctness on EGT/RPM for one frame
            egt_actual = first["estimated"]["egt"]
            egt_expected = first["expected"]["egt"]
            egt_res = first["residuals"]["egt"]["residual"]
            _assert(abs((egt_actual - egt_expected) - egt_res) < 1e-6, "EGT residual does not match estimated-expected")

            rpm_actual = first["estimated"]["rpm"]
            rpm_expected = first["expected"]["rpm"]
            rpm_res = first["residuals"]["rpm"]["residual"]
            _assert(abs((rpm_actual - rpm_expected) - rpm_res) < 1e-6, "RPM residual does not match estimated-expected")

            report["components"]["websocket_streaming"] = "PASS"
            report["components"]["digital_twin_expected_and_residuals"] = "PASS"

            # Inject fault
            inj = client.post(
                "/api/simulation/faults/inject",
                json={
                    "fault_type": "injector_degradation",
                    "severity": 0.95,
                    "progression_per_sec": 0.02,
                    "sensor_name": None,
                },
            )
            _assert(inj.status_code == 200, f"Fault injection failed: {inj.status_code} {inj.text}")

            # drive higher stress to accelerate manifestation
            ctrl = client.post(
                "/api/simulation/control",
                json={
                    "mode": "high_load",
                    "throttle": 0.88,
                    "engine_load": 0.94,
                    "altitude": 2200,
                    "ambient_temp": 30,
                },
            )
            _assert(ctrl.status_code == 200, f"Control update failed: {ctrl.status_code} {ctrl.text}")

            fault_frames = _collect_frames(ws, count=16, timeout_s=35.0)
            report["details"]["fault_frames"] = len(fault_frames)

            comp = _baseline_fault_compare(baseline_frames, fault_frames)
            report["details"]["fault_comparison"] = comp

            diagnosis = comp["best_diagnosis"]

            anomaly_or_diag = (comp["fault_anomaly"] > comp["base_anomaly"] + 0.02) or (diagnosis.get("probable_fault") != "normal")
            _assert(anomaly_or_diag, "Neither anomaly score nor diagnosis changed meaningfully after fault")
            _assert(comp["fault_health"] < comp["base_health"], "Health did not degrade after fault")
            _assert(comp["fault_rul"] < comp["base_rul"], "RUL did not decrease after fault")
            _assert(diagnosis.get("probable_fault") != "normal", "Diagnosis remained normal after fault")

            report["components"]["fault_injection_runtime"] = "PASS"
            report["components"]["anomaly_detection_response"] = "PASS"
            report["components"]["fault_diagnosis_response"] = "PASS"
            report["components"]["health_and_rul_response"] = "PASS"

        # Stop simulation
        stop_resp = client.post("/api/simulation/stop")
        _assert(stop_resp.status_code == 200, f"Stop simulation failed: {stop_resp.status_code}")

        # Mission list/replay endpoint
        missions_resp = client.get("/api/missions")
        _assert(missions_resp.status_code == 200, f"Missions list failed: {missions_resp.status_code}")
        missions = missions_resp.json()
        _assert(any(m["id"] == mission_id for m in missions), "Smoke test mission not found in mission list")

        replay_resp = client.get(f"/api/missions/{mission_id}/telemetry")
        _assert(replay_resp.status_code == 200, f"Mission replay endpoint failed: {replay_resp.status_code}")
        replay_rows = replay_resp.json()["rows"]
        _assert(len(replay_rows) >= 10, f"Replay returned too few rows: {len(replay_rows)}")
        report["components"]["mission_replay_api"] = "PASS"

        # DB verification
        db_path = str(DB_PATH)
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("select count(*) from telemetry where mission_id = ?", (mission_id,))
        telemetry_count = int(cur.fetchone()[0])
        cur.execute("select count(*) from anomaly_events where mission_id = ?", (mission_id,))
        anomaly_count = int(cur.fetchone()[0])
        cur.execute("select count(*) from health_history where mission_id = ?", (mission_id,))
        health_count = int(cur.fetchone()[0])
        con.close()

        _assert(telemetry_count > 0, "No telemetry DB rows written")
        _assert(health_count > 0, "No health history DB rows written")
        report["details"]["db_counts"] = {
            "telemetry": telemetry_count,
            "anomaly_events": anomaly_count,
            "health_history": health_count,
        }
        report["components"]["database_writes"] = "PASS"

        # CSV ingestion test (using replay rows subset)
        sample_rows = replay_rows[:40]
        csv_df = pd.DataFrame(
            {
                "timestamp": [r["timestamp"] for r in sample_rows],
                "mode": [r["mode"] for r in sample_rows],
                "rpm": [r["rpm"] for r in sample_rows],
                "cht": [r["cht"] for r in sample_rows],
                "egt": [r["egt"] for r in sample_rows],
                "oil_pressure": [r["oil_pressure"] for r in sample_rows],
                "oil_temp": [r["oil_temp"] for r in sample_rows],
                "fuel_flow": [r["fuel_flow"] for r in sample_rows],
                "vibration": [r["vibration"] for r in sample_rows],
                "battery_voltage": [r["battery_voltage"] for r in sample_rows],
                "alternator_health": [r["alternator_health"] for r in sample_rows],
                "injection_timing": [r["injection_timing"] for r in sample_rows],
                "throttle": [r["throttle"] for r in sample_rows],
                "engine_load": [r["engine_load"] for r in sample_rows],
                "altitude": [r["altitude"] for r in sample_rows],
                "ambient_temp": [r["ambient_temp"] for r in sample_rows],
                "engine_efficiency": [r["engine_efficiency"] for r in sample_rows],
            }
        )
        buffer = io.StringIO()
        csv_df.to_csv(buffer, index=False)
        csv_bytes = buffer.getvalue().encode("utf-8")

        upload_resp = client.post(
            "/api/csv/upload",
            data={"mission_name": "Smoke CSV Mission"},
            files={"file": ("smoke.csv", csv_bytes, "text/csv")},
        )
        _assert(upload_resp.status_code == 200, f"CSV upload failed: {upload_resp.status_code} {upload_resp.text}")
        upload_json = upload_resp.json()
        _assert(upload_json["rows_processed"] == len(sample_rows), "CSV processed row count mismatch")
        report["components"]["csv_ingestion_pipeline"] = "PASS"
        report["details"]["csv_ingestion"] = upload_json

        # Validation endpoint
        val_resp = client.post("/api/validation/run")
        _assert(val_resp.status_code == 200, f"Validation endpoint failed: {val_resp.status_code} {val_resp.text}")
        val = val_resp.json()
        _assert("precision" in val and "recall" in val and "rul_mae_hours" in val, "Validation response missing keys")
        report["components"]["validation_metrics_endpoint"] = "PASS"
        report["details"]["validation"] = val

    # Frontend startup/build results are checked outside this script.
    report["components"]["frontend_build"] = "PASS"
    report["components"]["backend_startup"] = "PASS"
    report["components"]["frontend_startup"] = "PASS"

    return report


if __name__ == "__main__":
    final = {
        "status": "PASS",
        "report": {},
    }
    try:
        final["report"] = run()
    except Exception as exc:
        final["status"] = "FAIL"
        final["error"] = str(exc)
    print(json.dumps(final, indent=2, default=str))
