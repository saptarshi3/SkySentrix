from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, String, Text, inspect, select, text
from sqlalchemy.orm import Session

from app.db.database import engine
from app.db.models import (
    AnomalyEvent,
    Base,
    EnginePassport,
    FaultEvent,
    HealthHistory,
    MaintenanceEvent,
    Mission,
    RULPrediction,
    TelemetryRecord,
)
from app.models.schemas import PipelineFrame


def _default_sql_for_column(col) -> str:
    if isinstance(col.type, (String, Text)):
        return "''"
    if isinstance(col.type, DateTime):
        return "'1970-01-01 00:00:00'"
    return "0"


def _apply_lightweight_schema_migrations() -> None:
    """
    Lightweight additive migration for SQLite prototype DB.
    - Creates missing columns with ALTER TABLE ... ADD COLUMN
    - Backfills non-null defaults for upgraded schema columns

    This avoids dropping user data while keeping migration simple for a demo prototype.
    """
    insp = inspect(engine)
    existing_tables = set(insp.get_table_names())
    dialect = engine.dialect

    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue

            existing_cols = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in existing_cols:
                    continue

                col_type_sql = col.type.compile(dialect=dialect)
                conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type_sql}"))

                if not col.nullable:
                    dflt = _default_sql_for_column(col)
                    conn.execute(text(f"UPDATE {table.name} SET {col.name} = {dflt} WHERE {col.name} IS NULL"))

        # Backfill known upgraded fields for compatibility with older rows.
        if "missions" in existing_tables:
            conn.execute(text("UPDATE missions SET engine_id = 'VIRTUAL-001' WHERE engine_id IS NULL OR engine_id = ''"))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _apply_lightweight_schema_migrations()


def _get_or_create_engine_passport(db: Session, engine_id: str) -> EnginePassport:
    stmt = select(EnginePassport).where(EnginePassport.engine_id == engine_id)
    passport = db.scalar(stmt)
    if passport is not None:
        return passport

    passport = EnginePassport(
        engine_id=engine_id,
        mission_count=0,
        total_engine_hours=0.0,
        cumulative_degradation=0.0,
        last_health_index=100.0,
        last_rul_hours=0.0,
        fault_event_count=0,
        updated_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.add(passport)
    db.flush()
    return passport


def create_mission(
    db: Session,
    *,
    name: str,
    source: str,
    preset: Optional[str],
    metadata: Optional[Dict[str, Any]] = None,
    engine_id: str = "VIRTUAL-001",
) -> Mission:
    mission = Mission(
        name=name,
        source=source,
        status="running",
        preset=preset,
        engine_id=engine_id,
        metadata_json=json.dumps(metadata or {}),
        started_at=datetime.utcnow(),
    )
    db.add(mission)

    passport = _get_or_create_engine_passport(db, engine_id)
    passport.mission_count += 1
    passport.updated_at = datetime.utcnow()
    db.add(passport)

    db.commit()
    db.refresh(mission)
    return mission


def complete_mission(db: Session, mission_id: int) -> None:
    mission = db.get(Mission, mission_id)
    if mission is None:
        return
    mission.status = "completed"
    mission.ended_at = datetime.utcnow()
    db.add(mission)
    db.commit()


def _to_utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _get_residual(frame: PipelineFrame, key: str, attr: str) -> float:
    entry = frame.residuals.get(key)
    if entry is None:
        return 0.0
    return float(getattr(entry, attr))


def save_pipeline_frame(db: Session, frame: PipelineFrame) -> None:
    if frame.mission_id is None:
        return

    t = frame.telemetry
    est = frame.estimated
    e = frame.expected

    ts = _to_utc_naive(t.timestamp)

    prev_stmt = (
        select(TelemetryRecord.timestamp)
        .where(TelemetryRecord.mission_id == frame.mission_id)
        .order_by(TelemetryRecord.sequence.desc())
        .limit(1)
    )
    prev_ts = db.scalar(prev_stmt)

    rec = TelemetryRecord(
        mission_id=frame.mission_id,
        sequence=frame.sequence,
        timestamp=ts,
        mode=t.mode,
        rpm=t.rpm,
        cht=t.cht,
        egt=t.egt,
        oil_pressure=t.oil_pressure,
        oil_temp=t.oil_temp,
        fuel_flow=t.fuel_flow,
        vibration=t.vibration,
        battery_voltage=t.battery_voltage,
        alternator_health=t.alternator_health,
        injection_timing=t.injection_timing,
        throttle=t.throttle,
        engine_load=t.engine_load,
        altitude=t.altitude,
        ambient_temp=t.ambient_temp,
        engine_efficiency=t.engine_efficiency,
        manifold_pressure=t.manifold_pressure,
        air_mass_flow=t.air_mass_flow,
        torque_nm=t.torque_nm,
        power_kw=t.power_kw,
        propeller_load=t.propeller_load,
        airspeed=t.airspeed,
        pressure_kpa=t.pressure_kpa,
        density_ratio=t.density_ratio,
        est_rpm=est.rpm,
        est_cht=est.cht,
        est_egt=est.egt,
        est_oil_pressure=est.oil_pressure,
        est_oil_temp=est.oil_temp,
        est_fuel_flow=est.fuel_flow,
        est_vibration=est.vibration,
        est_battery_voltage=est.battery_voltage,
        est_manifold_pressure=est.manifold_pressure,
        est_air_mass_flow=est.air_mass_flow,
        est_torque_nm=est.torque_nm,
        est_power_kw=est.power_kw,
        est_propeller_load=est.propeller_load,
        est_engine_efficiency=est.engine_efficiency,
        est_alternator_health=est.alternator_health,
        expected_rpm=e.rpm,
        expected_cht=e.cht,
        expected_egt=e.egt,
        expected_oil_pressure=e.oil_pressure,
        expected_oil_temp=e.oil_temp,
        expected_fuel_flow=e.fuel_flow,
        expected_vibration=e.vibration,
        expected_battery_voltage=e.battery_voltage,
        expected_manifold_pressure=e.manifold_pressure,
        expected_air_mass_flow=e.air_mass_flow,
        expected_torque_nm=e.torque_nm,
        expected_power_kw=e.power_kw,
        expected_propeller_load=e.propeller_load,
        residual_rpm=_get_residual(frame, "rpm", "residual"),
        residual_rpm_pct=_get_residual(frame, "rpm", "residual_pct"),
        residual_cht=_get_residual(frame, "cht", "residual"),
        residual_cht_pct=_get_residual(frame, "cht", "residual_pct"),
        residual_egt=_get_residual(frame, "egt", "residual"),
        residual_egt_pct=_get_residual(frame, "egt", "residual_pct"),
        residual_oil_pressure=_get_residual(frame, "oil_pressure", "residual"),
        residual_oil_pressure_pct=_get_residual(frame, "oil_pressure", "residual_pct"),
        residual_oil_temp=_get_residual(frame, "oil_temp", "residual"),
        residual_oil_temp_pct=_get_residual(frame, "oil_temp", "residual_pct"),
        residual_fuel_flow=_get_residual(frame, "fuel_flow", "residual"),
        residual_fuel_flow_pct=_get_residual(frame, "fuel_flow", "residual_pct"),
        residual_vibration=_get_residual(frame, "vibration", "residual"),
        residual_vibration_pct=_get_residual(frame, "vibration", "residual_pct"),
        residual_battery_voltage=_get_residual(frame, "battery_voltage", "residual"),
        residual_battery_voltage_pct=_get_residual(frame, "battery_voltage", "residual_pct"),
        residual_manifold_pressure=_get_residual(frame, "manifold_pressure", "residual"),
        residual_manifold_pressure_pct=_get_residual(frame, "manifold_pressure", "residual_pct"),
        residual_air_mass_flow=_get_residual(frame, "air_mass_flow", "residual"),
        residual_air_mass_flow_pct=_get_residual(frame, "air_mass_flow", "residual_pct"),
        residual_torque_nm=_get_residual(frame, "torque_nm", "residual"),
        residual_torque_nm_pct=_get_residual(frame, "torque_nm", "residual_pct"),
        residual_power_kw=_get_residual(frame, "power_kw", "residual"),
        residual_power_kw_pct=_get_residual(frame, "power_kw", "residual_pct"),
        residual_propeller_load=_get_residual(frame, "propeller_load", "residual"),
        residual_propeller_load_pct=_get_residual(frame, "propeller_load", "residual_pct"),
        anomaly_score=frame.anomaly.score,
        anomaly_level=frame.anomaly.level,
        diagnosis_fault=frame.diagnosis.probable_fault,
        diagnosis_confidence=frame.diagnosis.confidence,
        diagnosis_explanation=frame.diagnosis.explanation,
        diagnosis_evidence_json=json.dumps(frame.diagnosis.evidence),
        diagnosis_affected_subsystems_json=json.dumps(frame.diagnosis.affected_subsystems),
        health_index=frame.health.health_index,
        degradation_index=frame.health.degradation_index,
        degradation_rate_per_hour=frame.health.degradation_rate_per_hour,
        health_state=frame.health.state,
        subsystem_health_json=json.dumps(frame.health.subsystem_health),
        rul_hours=frame.rul.current_rul_hours,
        rul_trend=frame.rul.trend,
        rul_confidence_low=frame.rul.confidence_low_hours,
        rul_confidence_high=frame.rul.confidence_high_hours,
        rul_note=frame.rul.note,
        maintenance_level=frame.maintenance.level,
        maintenance_message=frame.maintenance.message,
    )
    db.add(rec)

    created_fault_event = False

    if frame.anomaly.level in {"WARNING", "CRITICAL"}:
        db.add(
            AnomalyEvent(
                mission_id=frame.mission_id,
                timestamp=ts,
                score=frame.anomaly.score,
                level=frame.anomaly.level,
                contributors_json=json.dumps(frame.anomaly.contributing_parameters),
            )
        )

    if frame.diagnosis.probable_fault != "normal" and frame.diagnosis.confidence >= 0.55:
        created_fault_event = True
        db.add(
            FaultEvent(
                mission_id=frame.mission_id,
                timestamp=ts,
                fault_type=frame.diagnosis.probable_fault,
                severity=frame.anomaly.score,
                confidence=frame.diagnosis.confidence,
                explanation=frame.diagnosis.explanation,
                contributors_json=json.dumps(frame.diagnosis.contributing_parameters),
            )
        )

    db.add(
        HealthHistory(
            mission_id=frame.mission_id,
            timestamp=ts,
            health_index=frame.health.health_index,
            degradation_index=frame.health.degradation_index,
            degradation_rate_per_hour=frame.health.degradation_rate_per_hour,
            state=frame.health.state,
            subsystem_health_json=json.dumps(frame.health.subsystem_health),
        )
    )

    db.add(
        RULPrediction(
            mission_id=frame.mission_id,
            timestamp=ts,
            initial_rul_hours=frame.rul.initial_rul_hours,
            current_rul_hours=frame.rul.current_rul_hours,
            degradation_rate_per_hour=frame.rul.degradation_rate_per_hour,
            trend=frame.rul.trend,
            confidence_low=frame.rul.confidence_low_hours,
            confidence_high=frame.rul.confidence_high_hours,
            note=frame.rul.note,
        )
    )

    db.add(
        MaintenanceEvent(
            mission_id=frame.mission_id,
            timestamp=ts,
            level=frame.maintenance.level,
            message=frame.maintenance.message,
        )
    )

    # Engine passport update
    mission = db.get(Mission, frame.mission_id)
    if mission is not None:
        passport = _get_or_create_engine_passport(db, mission.engine_id)

        if prev_ts is None:
            dt_sec = 1.0
        else:
            prev_ts_naive = _to_utc_naive(prev_ts)
            dt_sec = (ts - prev_ts_naive).total_seconds()
            dt_sec = max(0.2, min(5.0, dt_sec))

        dt_h = dt_sec / 3600.0
        passport.total_engine_hours += dt_h
        passport.cumulative_degradation += max(0.0, frame.health.degradation_rate_per_hour) * dt_h
        passport.last_health_index = frame.health.health_index
        passport.last_rul_hours = frame.rul.current_rul_hours
        if created_fault_event:
            passport.fault_event_count += 1
        passport.updated_at = datetime.utcnow()
        db.add(passport)

    db.commit()


def list_missions(db: Session) -> List[Mission]:
    stmt = select(Mission).order_by(Mission.started_at.desc())
    return list(db.scalars(stmt).all())


def get_mission(db: Session, mission_id: int) -> Optional[Mission]:
    return db.get(Mission, mission_id)


def get_mission_telemetry(db: Session, mission_id: int, limit: Optional[int] = None) -> List[TelemetryRecord]:
    stmt = select(TelemetryRecord).where(TelemetryRecord.mission_id == mission_id).order_by(TelemetryRecord.sequence.asc())
    if limit is not None and isinstance(limit, int):
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt).all())


def get_engine_passport(db: Session, engine_id: str) -> Optional[EnginePassport]:
    stmt = select(EnginePassport).where(EnginePassport.engine_id == engine_id)
    return db.scalar(stmt)
