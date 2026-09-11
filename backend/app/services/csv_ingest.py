from __future__ import annotations

from typing import Dict, List

import pandas as pd
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.models.schemas import CsvIngestionResponse, TelemetryPoint
from app.services.pipeline import DigitalTwinPipeline

REQUIRED_COLUMNS: List[str] = [
    "timestamp",
    "rpm",
    "cht",
    "egt",
    "oil_pressure",
    "oil_temp",
    "fuel_flow",
    "vibration",
    "battery_voltage",
    "alternator_health",
    "injection_timing",
    "throttle",
    "engine_load",
    "altitude",
    "ambient_temp",
]


RANGE_RULES: Dict[str, tuple[float, float]] = {
    "rpm": (0, 3500),
    "cht": (-30, 450),
    "egt": (0, 1300),
    "oil_pressure": (0, 150),
    "oil_temp": (-40, 260),
    "fuel_flow": (0, 180),
    "vibration": (0, 8),
    "battery_voltage": (0, 18),
    "alternator_health": (0, 1.2),
    "injection_timing": (0, 45),
    "throttle": (0, 1),
    "engine_load": (0, 1),
    "altitude": (0, 15000),
    "ambient_temp": (-60, 80),
}


def infer_mode(throttle: float, load: float) -> str:
    if throttle <= 0.03:
        return "shutdown"
    if throttle < 0.22:
        return "idle"
    if throttle > 0.90:
        return "takeoff"
    if throttle > 0.78 and load > 0.88:
        return "high_load"
    if throttle > 0.75:
        return "climb"
    if throttle > 0.58:
        return "cruise"
    if throttle > 0.40:
        return "loiter"
    return "descent"


def process_csv_upload(
    db: Session,
    pipeline: DigitalTwinPipeline,
    file: UploadFile,
    mission_name: str,
) -> CsvIngestionResponse:
    try:
        raw = file.file.read()
        df = pd.read_csv(pd.io.common.BytesIO(raw))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to read CSV: {exc}") from exc

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {', '.join(missing)}")

    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid timestamp column: {exc}") from exc

    # Numeric normalization and simple missing-value handling
    for col in RANGE_RULES:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if df[list(RANGE_RULES.keys())].isnull().any().any():
        df[list(RANGE_RULES.keys())] = (
            df[list(RANGE_RULES.keys())]
            .interpolate(limit_direction="both")
            .ffill()
            .bfill()
        )

    if df[list(RANGE_RULES.keys())].isnull().any().any():
        raise HTTPException(status_code=400, detail="CSV has non-recoverable missing numeric values in required telemetry columns")

    for col, (lo, hi) in RANGE_RULES.items():
        invalid = df[(df[col] < lo) | (df[col] > hi)]
        if not invalid.empty:
            raise HTTPException(
                status_code=400,
                detail=f"Column {col} has values outside range [{lo}, {hi}]",
            )

    df = df.sort_values("timestamp")

    mission_id = pipeline.start_mission(
        db,
        name=mission_name,
        source="csv",
        preset=None,
        metadata={"filename": file.filename, "rows": int(len(df))},
    )

    warnings = 0
    anomalies = 0

    for _, row in df.iterrows():
        mode = str(row["mode"]) if "mode" in df.columns else infer_mode(float(row["throttle"]), float(row["engine_load"]))
        efficiency = float(row["engine_efficiency"]) if "engine_efficiency" in df.columns else 0.95

        point = TelemetryPoint(
            timestamp=row["timestamp"].to_pydatetime(),
            mode=mode,
            rpm=float(row["rpm"]),
            cht=float(row["cht"]),
            egt=float(row["egt"]),
            oil_pressure=float(row["oil_pressure"]),
            oil_temp=float(row["oil_temp"]),
            fuel_flow=float(row["fuel_flow"]),
            vibration=float(row["vibration"]),
            battery_voltage=float(row["battery_voltage"]),
            alternator_health=float(row["alternator_health"]),
            injection_timing=float(row["injection_timing"]),
            throttle=float(row["throttle"]),
            engine_load=float(row["engine_load"]),
            altitude=float(row["altitude"]),
            ambient_temp=float(row["ambient_temp"]),
            engine_efficiency=float(efficiency),
            manifold_pressure=float(row["manifold_pressure"]) if "manifold_pressure" in df.columns else 0.0,
            air_mass_flow=float(row["air_mass_flow"]) if "air_mass_flow" in df.columns else 0.0,
            torque_nm=float(row["torque_nm"]) if "torque_nm" in df.columns else 0.0,
            power_kw=float(row["power_kw"]) if "power_kw" in df.columns else 0.0,
            propeller_load=float(row["propeller_load"]) if "propeller_load" in df.columns else float(row["engine_load"]),
            airspeed=float(row["airspeed"]) if "airspeed" in df.columns else 0.0,
            pressure_kpa=float(row["pressure_kpa"]) if "pressure_kpa" in df.columns else 0.0,
            density_ratio=float(row["density_ratio"]) if "density_ratio" in df.columns else 1.0,
        )

        frame = pipeline.process(db, point)
        if frame.anomaly.level in {"WARNING", "CRITICAL"}:
            warnings += 1
        if frame.anomaly.score >= 0.58:
            anomalies += 1

    pipeline.end_mission(db)

    return CsvIngestionResponse(
        mission_id=mission_id,
        rows_processed=int(len(df)),
        anomalies_detected=anomalies,
        warnings_or_critical=warnings,
    )
