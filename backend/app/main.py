from __future__ import annotations

import json
import logging
import os
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import FAULT_TYPES, MISSION_PRESETS
from app.db import crud
from app.db.database import get_db
from app.models.schemas import (
    FaultInjectionRequest,
    ManualControlUpdateRequest,
    MissionResponse,
    StartSimulationRequest,
    ValidationResult,
)
from app.services.csv_ingest import process_csv_upload
from app.services.pipeline import DigitalTwinPipeline
from app.services.realtime import RealtimeEngine
from app.services.validation import run_synthetic_validation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


app = FastAPI(
    title="SkySentrix SIH 2026 DRDO Digital Twin Prototype",
    version="0.1.0",
    description="Synthetic digital twin prototype for aero-piston engine analytics.",
)

# Environment-configurable CORS origins
cors_env = os.getenv("CORS_ORIGINS", os.getenv("ALLOWED_ORIGINS", "")).strip()
cors_allow_all = os.getenv("CORS_ALLOW_ALL", "true").lower() in ("1", "true", "yes")

if cors_env:
    allowed_origins = [orig.strip() for orig in cors_env.split(",") if orig.strip()]
elif cors_allow_all:
    allowed_origins = ["*"]
else:
    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

# When wildcard '*' is allowed, allow_credentials must be False per CORS specification
allow_creds = "*" not in allowed_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_creds,
    allow_methods=["*"],
    allow_headers=["*"],
)

realtime_engine = RealtimeEngine()


def _safe_parse_json(raw: Optional[str], fallback):
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except Exception:
        return fallback


@app.on_event("startup")
def on_startup() -> None:
    crud.init_db()


@app.get("/health")
@app.head("/health")
def root_health() -> dict:
    """Standard deployment health check endpoint for cloud platforms (e.g. Render)."""
    return {
        "status": "healthy",
        "service": "SkySentrix Backend",
        "version": "0.1.0",
    }


@app.get("/api/health")
def api_health() -> dict:
    return {
        "service": "ok",
        "note": "Telemetry and analytics are synthetic unless CSV telemetry is uploaded.",
    }


@app.get("/api/fault-types")
def api_fault_types() -> dict:
    return {"fault_types": FAULT_TYPES}


@app.get("/api/mission-presets")
def api_mission_presets() -> dict:
    return {"presets": MISSION_PRESETS}


@app.post("/api/simulation/start")
async def api_start_simulation(req: StartSimulationRequest) -> dict:
    if req.preset not in MISSION_PRESETS:
        raise HTTPException(status_code=400, detail=f"Unknown preset: {req.preset}")
    return await realtime_engine.start(
        mission_name=req.mission_name,
        preset=req.preset,
        duration_sec=req.duration_sec,
        demo_mode=req.demo_mode,
    )


@app.post("/api/simulation/stop")
async def api_stop_simulation() -> dict:
    return await realtime_engine.stop()


@app.post("/api/simulation/demo")
async def api_start_demo() -> dict:
    req = StartSimulationRequest(
        mission_name="SIH One-Click Demo",
        preset="normal_endurance",
        duration_sec=420,
        demo_mode=True,
    )
    return await realtime_engine.start(
        mission_name=req.mission_name,
        preset=req.preset,
        duration_sec=req.duration_sec,
        demo_mode=req.demo_mode,
    )


@app.get("/api/simulation/state")
def api_simulation_state() -> dict:
    return realtime_engine.get_state()


@app.post("/api/simulation/control")
def api_update_control(req: ManualControlUpdateRequest) -> dict:
    return realtime_engine.update_manual_controls(req)


@app.post("/api/simulation/faults/inject")
async def api_inject_fault(req: FaultInjectionRequest) -> dict:
    if req.fault_type not in FAULT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported fault type: {req.fault_type}")
    return await realtime_engine.inject_fault(
        fault_type=req.fault_type,
        severity=req.severity,
        progression_per_sec=req.progression_per_sec,
        sensor_name=req.sensor_name,
    )


@app.delete("/api/simulation/faults/{fault_type}")
async def api_clear_fault(fault_type: str) -> dict:
    if fault_type not in FAULT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported fault type: {fault_type}")
    return await realtime_engine.clear_fault(fault_type)


@app.delete("/api/simulation/faults")
async def api_clear_all_faults() -> dict:
    return await realtime_engine.clear_all_faults()


@app.post("/api/simulation/reset")
async def api_reset_simulation() -> dict:
    return await realtime_engine.reset_to_standby()


@app.websocket("/ws/telemetry")
async def ws_telemetry(websocket: WebSocket) -> None:
    await realtime_engine.register_connection(websocket)
    try:
        state = realtime_engine.get_state()
        await websocket.send_json({"type": "state", **state})

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await realtime_engine.unregister_connection(websocket)
    except Exception:
        await realtime_engine.unregister_connection(websocket)


@app.get("/api/missions", response_model=list[MissionResponse])
def api_list_missions(db: Session = Depends(get_db)) -> list[MissionResponse]:
    missions = crud.list_missions(db)
    return [
        MissionResponse(
            id=m.id,
            name=m.name,
            source=m.source,
            status=m.status,
            preset=m.preset,
            engine_id=m.engine_id,
            started_at=m.started_at,
            ended_at=m.ended_at,
        )
        for m in missions
    ]


@app.get("/api/missions/{mission_id}")
def api_get_mission(mission_id: int, db: Session = Depends(get_db)) -> dict:
    mission = crud.get_mission(db, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")

    metadata = {}
    if mission.metadata_json:
        try:
            metadata = json.loads(mission.metadata_json)
        except Exception:
            metadata = {"raw": mission.metadata_json}

    return {
        "id": mission.id,
        "name": mission.name,
        "source": mission.source,
        "status": mission.status,
        "preset": mission.preset,
        "engine_id": mission.engine_id,
        "metadata": metadata,
        "started_at": mission.started_at,
        "ended_at": mission.ended_at,
    }


@app.get("/api/missions/{mission_id}/telemetry")
def api_get_mission_telemetry(
    mission_id: int,
    limit: Optional[int] = Query(default=None, ge=1, le=50000),
    db: Session = Depends(get_db),
) -> dict:
    mission = crud.get_mission(db, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")

    rows = crud.get_mission_telemetry(db, mission_id, limit=limit)
    data = [
        {
            "sequence": r.sequence,
            "timestamp": r.timestamp.isoformat(),
            "mode": r.mode,
            "rpm": r.rpm,
            "cht": r.cht,
            "egt": r.egt,
            "oil_pressure": r.oil_pressure,
            "oil_temp": r.oil_temp,
            "fuel_flow": r.fuel_flow,
            "vibration": r.vibration,
            "battery_voltage": r.battery_voltage,
            "alternator_health": r.alternator_health,
            "injection_timing": r.injection_timing,
            "throttle": r.throttle,
            "engine_load": r.engine_load,
            "altitude": r.altitude,
            "ambient_temp": r.ambient_temp,
            "engine_efficiency": r.engine_efficiency,
            "manifold_pressure": r.manifold_pressure or 0.0,
            "air_mass_flow": r.air_mass_flow or 0.0,
            "torque_nm": r.torque_nm or 0.0,
            "power_kw": r.power_kw or 0.0,
            "propeller_load": r.propeller_load or 0.0,
            "airspeed": r.airspeed or 0.0,
            "pressure_kpa": r.pressure_kpa or 0.0,
            "density_ratio": r.density_ratio or 1.0,
            "est_rpm": r.est_rpm or r.rpm,
            "est_egt": r.est_egt or r.egt,
            "est_cht": r.est_cht or r.cht,
            "est_oil_pressure": r.est_oil_pressure or r.oil_pressure,
            "est_oil_temp": r.est_oil_temp or r.oil_temp,
            "est_fuel_flow": r.est_fuel_flow or r.fuel_flow,
            "est_vibration": r.est_vibration or r.vibration,
            "est_battery_voltage": r.est_battery_voltage or r.battery_voltage,
            "est_manifold_pressure": r.est_manifold_pressure or (r.manifold_pressure or 0.0),
            "est_air_mass_flow": r.est_air_mass_flow or (r.air_mass_flow or 0.0),
            "est_torque_nm": r.est_torque_nm or (r.torque_nm or 0.0),
            "est_power_kw": r.est_power_kw or (r.power_kw or 0.0),
            "est_propeller_load": r.est_propeller_load or (r.propeller_load or 0.0),
            "expected_rpm": r.expected_rpm,
            "expected_egt": r.expected_egt,
            "expected_cht": r.expected_cht,
            "expected_oil_pressure": r.expected_oil_pressure,
            "expected_oil_temp": r.expected_oil_temp,
            "expected_fuel_flow": r.expected_fuel_flow,
            "expected_vibration": r.expected_vibration,
            "expected_battery_voltage": r.expected_battery_voltage,
            "expected_manifold_pressure": r.expected_manifold_pressure or 0.0,
            "expected_air_mass_flow": r.expected_air_mass_flow or 0.0,
            "expected_torque_nm": r.expected_torque_nm or 0.0,
            "expected_power_kw": r.expected_power_kw or 0.0,
            "expected_propeller_load": r.expected_propeller_load or 0.0,
            "residual_rpm_pct": r.residual_rpm_pct,
            "residual_egt_pct": r.residual_egt_pct,
            "residual_cht_pct": r.residual_cht_pct,
            "residual_oil_pressure_pct": r.residual_oil_pressure_pct,
            "residual_oil_temp_pct": r.residual_oil_temp_pct,
            "residual_fuel_flow_pct": r.residual_fuel_flow_pct,
            "residual_vibration_pct": r.residual_vibration_pct,
            "residual_battery_voltage_pct": r.residual_battery_voltage_pct,
            "residual_manifold_pressure_pct": r.residual_manifold_pressure_pct or 0.0,
            "residual_air_mass_flow_pct": r.residual_air_mass_flow_pct or 0.0,
            "residual_torque_nm_pct": r.residual_torque_nm_pct or 0.0,
            "residual_power_kw_pct": r.residual_power_kw_pct or 0.0,
            "residual_propeller_load_pct": r.residual_propeller_load_pct or 0.0,
            "anomaly_score": r.anomaly_score,
            "anomaly_level": r.anomaly_level,
            "diagnosis_fault": r.diagnosis_fault,
            "diagnosis_confidence": r.diagnosis_confidence,
            "diagnosis_explanation": r.diagnosis_explanation,
            "diagnosis_affected_subsystems": _safe_parse_json(r.diagnosis_affected_subsystems_json, []),
            "health_index": r.health_index,
            "degradation_index": r.degradation_index,
            "degradation_rate_per_hour": r.degradation_rate_per_hour,
            "health_state": r.health_state,
            "subsystem_health": _safe_parse_json(r.subsystem_health_json, {}),
            "rul_hours": r.rul_hours,
            "rul_trend": r.rul_trend,
            "rul_confidence_low": r.rul_confidence_low,
            "rul_confidence_high": r.rul_confidence_high,
            "maintenance_level": r.maintenance_level,
            "maintenance_message": r.maintenance_message,
        }
        for r in rows
    ]

    return {
        "mission": {
            "id": mission.id,
            "name": mission.name,
            "source": mission.source,
            "status": mission.status,
        },
        "rows": data,
    }


@app.post("/api/csv/upload")
def api_csv_upload(
    file: UploadFile = File(...),
    mission_name: str = Form("CSV Mission"),
    db: Session = Depends(get_db),
) -> dict:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    pipeline = DigitalTwinPipeline()
    result = process_csv_upload(db=db, pipeline=pipeline, file=file, mission_name=mission_name)
    return result.model_dump()


@app.post("/api/validation/run", response_model=ValidationResult)
def api_run_validation(db: Session = Depends(get_db)) -> ValidationResult:
    out = run_synthetic_validation(db)
    return ValidationResult(**out)


@app.get("/api/architecture")
def api_architecture() -> dict:
    return {
        "pipeline": [
            "Telemetry Acquisition (Simulator/CSV)",
            "State Estimation (Kalman)",
            "Digital Twin (Healthy Expected State)",
            "Residual Analysis",
            "AI/ML Anomaly Detection",
            "Fault Diagnosis",
            "Health + Degradation",
            "RUL Estimation",
            "Maintenance Advisory",
            "Dashboard + Mission Replay",
        ],
        "note": "Prototype with synthetic telemetry unless CSV telemetry is provided.",
    }
