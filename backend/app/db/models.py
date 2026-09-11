from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Mission(Base):
    __tablename__ = "missions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="running")
    preset: Mapped[str | None] = mapped_column(String(80), nullable=True)
    engine_id: Mapped[str] = mapped_column(String(80), default="VIRTUAL-001", index=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    telemetry_entries: Mapped[list[TelemetryRecord]] = relationship(back_populates="mission")
    fault_events: Mapped[list[FaultEvent]] = relationship(back_populates="mission")
    anomaly_events: Mapped[list[AnomalyEvent]] = relationship(back_populates="mission")
    health_history: Mapped[list[HealthHistory]] = relationship(back_populates="mission")
    rul_predictions: Mapped[list[RULPrediction]] = relationship(back_populates="mission")
    maintenance_events: Mapped[list[MaintenanceEvent]] = relationship(back_populates="mission")


class TelemetryRecord(Base):
    __tablename__ = "telemetry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    mode: Mapped[str] = mapped_column(String(40), index=True)

    # Observed telemetry
    rpm: Mapped[float] = mapped_column(Float)
    cht: Mapped[float] = mapped_column(Float)
    egt: Mapped[float] = mapped_column(Float)
    oil_pressure: Mapped[float] = mapped_column(Float)
    oil_temp: Mapped[float] = mapped_column(Float)
    fuel_flow: Mapped[float] = mapped_column(Float)
    vibration: Mapped[float] = mapped_column(Float)
    battery_voltage: Mapped[float] = mapped_column(Float)
    alternator_health: Mapped[float] = mapped_column(Float)
    injection_timing: Mapped[float] = mapped_column(Float)
    throttle: Mapped[float] = mapped_column(Float)
    engine_load: Mapped[float] = mapped_column(Float)
    altitude: Mapped[float] = mapped_column(Float)
    ambient_temp: Mapped[float] = mapped_column(Float)
    engine_efficiency: Mapped[float] = mapped_column(Float)

    manifold_pressure: Mapped[float | None] = mapped_column(Float, nullable=True)
    air_mass_flow: Mapped[float | None] = mapped_column(Float, nullable=True)
    torque_nm: Mapped[float | None] = mapped_column(Float, nullable=True)
    power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    propeller_load: Mapped[float | None] = mapped_column(Float, nullable=True)
    airspeed: Mapped[float | None] = mapped_column(Float, nullable=True)
    pressure_kpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    density_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Estimated state
    est_rpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    est_cht: Mapped[float | None] = mapped_column(Float, nullable=True)
    est_egt: Mapped[float | None] = mapped_column(Float, nullable=True)
    est_oil_pressure: Mapped[float | None] = mapped_column(Float, nullable=True)
    est_oil_temp: Mapped[float | None] = mapped_column(Float, nullable=True)
    est_fuel_flow: Mapped[float | None] = mapped_column(Float, nullable=True)
    est_vibration: Mapped[float | None] = mapped_column(Float, nullable=True)
    est_battery_voltage: Mapped[float | None] = mapped_column(Float, nullable=True)
    est_manifold_pressure: Mapped[float | None] = mapped_column(Float, nullable=True)
    est_air_mass_flow: Mapped[float | None] = mapped_column(Float, nullable=True)
    est_torque_nm: Mapped[float | None] = mapped_column(Float, nullable=True)
    est_power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    est_propeller_load: Mapped[float | None] = mapped_column(Float, nullable=True)
    est_engine_efficiency: Mapped[float | None] = mapped_column(Float, nullable=True)
    est_alternator_health: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Healthy expected state
    expected_rpm: Mapped[float] = mapped_column(Float)
    expected_cht: Mapped[float] = mapped_column(Float)
    expected_egt: Mapped[float] = mapped_column(Float)
    expected_oil_pressure: Mapped[float] = mapped_column(Float)
    expected_oil_temp: Mapped[float] = mapped_column(Float)
    expected_fuel_flow: Mapped[float] = mapped_column(Float)
    expected_vibration: Mapped[float] = mapped_column(Float)
    expected_battery_voltage: Mapped[float] = mapped_column(Float)

    expected_manifold_pressure: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_air_mass_flow: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_torque_nm: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_propeller_load: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Residuals
    residual_rpm: Mapped[float] = mapped_column(Float)
    residual_rpm_pct: Mapped[float] = mapped_column(Float)
    residual_cht: Mapped[float] = mapped_column(Float)
    residual_cht_pct: Mapped[float] = mapped_column(Float)
    residual_egt: Mapped[float] = mapped_column(Float)
    residual_egt_pct: Mapped[float] = mapped_column(Float)
    residual_oil_pressure: Mapped[float] = mapped_column(Float)
    residual_oil_pressure_pct: Mapped[float] = mapped_column(Float)
    residual_oil_temp: Mapped[float] = mapped_column(Float)
    residual_oil_temp_pct: Mapped[float] = mapped_column(Float)
    residual_fuel_flow: Mapped[float] = mapped_column(Float)
    residual_fuel_flow_pct: Mapped[float] = mapped_column(Float)
    residual_vibration: Mapped[float] = mapped_column(Float)
    residual_vibration_pct: Mapped[float] = mapped_column(Float)
    residual_battery_voltage: Mapped[float] = mapped_column(Float)
    residual_battery_voltage_pct: Mapped[float] = mapped_column(Float)

    residual_manifold_pressure: Mapped[float | None] = mapped_column(Float, nullable=True)
    residual_manifold_pressure_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    residual_air_mass_flow: Mapped[float | None] = mapped_column(Float, nullable=True)
    residual_air_mass_flow_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    residual_torque_nm: Mapped[float | None] = mapped_column(Float, nullable=True)
    residual_torque_nm_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    residual_power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    residual_power_kw_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    residual_propeller_load: Mapped[float | None] = mapped_column(Float, nullable=True)
    residual_propeller_load_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    anomaly_score: Mapped[float] = mapped_column(Float)
    anomaly_level: Mapped[str] = mapped_column(String(20))
    diagnosis_fault: Mapped[str] = mapped_column(String(80))
    diagnosis_confidence: Mapped[float] = mapped_column(Float)
    diagnosis_explanation: Mapped[str] = mapped_column(Text)
    diagnosis_evidence_json: Mapped[str] = mapped_column(Text)
    diagnosis_affected_subsystems_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    health_index: Mapped[float] = mapped_column(Float)
    degradation_index: Mapped[float] = mapped_column(Float)
    degradation_rate_per_hour: Mapped[float] = mapped_column(Float)
    health_state: Mapped[str | None] = mapped_column(String(20), nullable=True)
    subsystem_health_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    rul_hours: Mapped[float] = mapped_column(Float)
    rul_trend: Mapped[str | None] = mapped_column(String(40), nullable=True)
    rul_confidence_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    rul_confidence_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    rul_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    maintenance_level: Mapped[str] = mapped_column(String(20))
    maintenance_message: Mapped[str] = mapped_column(Text)

    mission: Mapped[Mission] = relationship(back_populates="telemetry_entries")


class FaultEvent(Base):
    __tablename__ = "fault_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    fault_type: Mapped[str] = mapped_column(String(80))
    severity: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    explanation: Mapped[str] = mapped_column(Text)
    contributors_json: Mapped[str] = mapped_column(Text)

    mission: Mapped[Mission] = relationship(back_populates="fault_events")


class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    score: Mapped[float] = mapped_column(Float)
    level: Mapped[str] = mapped_column(String(20))
    contributors_json: Mapped[str] = mapped_column(Text)

    mission: Mapped[Mission] = relationship(back_populates="anomaly_events")


class HealthHistory(Base):
    __tablename__ = "health_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    health_index: Mapped[float] = mapped_column(Float)
    degradation_index: Mapped[float] = mapped_column(Float)
    degradation_rate_per_hour: Mapped[float] = mapped_column(Float)
    state: Mapped[str | None] = mapped_column(String(20), nullable=True)
    subsystem_health_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    mission: Mapped[Mission] = relationship(back_populates="health_history")


class RULPrediction(Base):
    __tablename__ = "rul_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    initial_rul_hours: Mapped[float] = mapped_column(Float)
    current_rul_hours: Mapped[float] = mapped_column(Float)
    degradation_rate_per_hour: Mapped[float] = mapped_column(Float)
    trend: Mapped[str | None] = mapped_column(String(40), nullable=True)
    confidence_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    mission: Mapped[Mission] = relationship(back_populates="rul_predictions")


class MaintenanceEvent(Base):
    __tablename__ = "maintenance_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    level: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)

    mission: Mapped[Mission] = relationship(back_populates="maintenance_events")


class EnginePassport(Base):
    __tablename__ = "engine_passports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    engine_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    mission_count: Mapped[int] = mapped_column(Integer, default=0)
    total_engine_hours: Mapped[float] = mapped_column(Float, default=0.0)
    cumulative_degradation: Mapped[float] = mapped_column(Float, default=0.0)
    last_health_index: Mapped[float] = mapped_column(Float, default=100.0)
    last_rul_hours: Mapped[float] = mapped_column(Float, default=0.0)
    fault_event_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
