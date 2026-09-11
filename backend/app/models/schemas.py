from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


AnomalyLevel = Literal["NORMAL", "WARNING", "CRITICAL"]
MaintenanceLevel = Literal["NORMAL", "WARNING", "CRITICAL"]


class TelemetryPoint(BaseModel):
    timestamp: datetime
    mode: str
    rpm: float
    cht: float
    egt: float
    oil_pressure: float
    oil_temp: float
    fuel_flow: float
    vibration: float
    battery_voltage: float
    alternator_health: float
    injection_timing: float
    throttle: float
    engine_load: float
    altitude: float
    ambient_temp: float
    engine_efficiency: float

    # Extended coupled-model fields
    manifold_pressure: float = 0.0
    air_mass_flow: float = 0.0
    torque_nm: float = 0.0
    power_kw: float = 0.0
    propeller_load: float = 0.0
    airspeed: float = 0.0
    pressure_kpa: float = 0.0
    density_ratio: float = 1.0
    subsystem_health: Dict[str, float] = Field(default_factory=dict)
    true_state: Dict[str, float] = Field(default_factory=dict)


class EstimatedState(BaseModel):
    rpm: float
    egt: float
    cht: float
    oil_temp: float
    oil_pressure: float
    vibration: float
    fuel_flow: float
    battery_voltage: float
    manifold_pressure: float
    air_mass_flow: float
    torque_nm: float
    power_kw: float
    propeller_load: float
    engine_efficiency: float
    alternator_health: float


class ExpectedState(BaseModel):
    rpm: float
    cht: float
    egt: float
    oil_pressure: float
    oil_temp: float
    fuel_flow: float
    vibration: float
    battery_voltage: float
    manifold_pressure: float = 0.0
    air_mass_flow: float = 0.0
    torque_nm: float = 0.0
    power_kw: float = 0.0
    propeller_load: float = 0.0


class ResidualEntry(BaseModel):
    actual: float
    expected: float
    residual: float
    residual_pct: float


class AnomalyResult(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    level: AnomalyLevel
    timestamp: datetime
    contributing_parameters: List[str]


class DiagnosisResult(BaseModel):
    probable_fault: str
    confidence: float = Field(ge=0.0, le=1.0)
    contributing_parameters: List[str]
    affected_subsystems: List[str] = Field(default_factory=list)
    evidence: Dict[str, float]
    explanation: str


class HealthResult(BaseModel):
    health_index: float = Field(ge=0.0, le=100.0)
    degradation_index: float = Field(ge=0.0, le=100.0)
    degradation_rate_per_hour: float
    subsystem_health: Dict[str, float] = Field(default_factory=dict)
    state: str = "HEALTHY"


class RULResult(BaseModel):
    initial_rul_hours: float
    current_rul_hours: float
    degradation_rate_per_hour: float
    trend: str
    confidence_low_hours: float = 0.0
    confidence_high_hours: float = 0.0
    note: str


class MaintenanceAdvisory(BaseModel):
    level: MaintenanceLevel
    message: str


class PipelineFrame(BaseModel):
    mission_id: Optional[int]
    sequence: int
    telemetry: TelemetryPoint
    estimated: EstimatedState
    expected: ExpectedState
    residuals: Dict[str, ResidualEntry]
    anomaly: AnomalyResult
    diagnosis: DiagnosisResult
    health: HealthResult
    rul: RULResult
    maintenance: MaintenanceAdvisory


class FaultInjectionRequest(BaseModel):
    fault_type: str
    severity: float = Field(default=0.4, ge=0.0, le=1.0)
    progression_per_sec: float = Field(default=0.003, ge=0.0, le=0.05)
    sensor_name: Optional[str] = None


class ManualControlUpdateRequest(BaseModel):
    mode: Optional[str] = None
    throttle: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    engine_load: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    altitude: Optional[float] = Field(default=None, ge=0.0, le=12000.0)
    ambient_temp: Optional[float] = Field(default=None, ge=-50.0, le=70.0)


class StartSimulationRequest(BaseModel):
    mission_name: str = "SIH Demo Mission"
    preset: str = "normal_endurance"
    duration_sec: int = Field(default=600, ge=60, le=10800)
    demo_mode: bool = False


class MissionResponse(BaseModel):
    id: int
    name: str
    source: str
    status: str
    preset: Optional[str]
    engine_id: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime]


class CsvIngestionResponse(BaseModel):
    mission_id: int
    rows_processed: int
    anomalies_detected: int
    warnings_or_critical: int


class ValidationResult(BaseModel):
    precision: float
    recall: float
    false_alarm_rate: float
    detection_latency_sec: float
    f1: float = 0.0
    twin_rmse: Dict[str, float] = Field(default_factory=dict)
    confusion_matrix: Dict[str, int]
    rul_mae_hours: float
    rul_rmse_hours: float = 0.0
    notes: str
