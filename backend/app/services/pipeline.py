from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.analytics.anomaly import AnomalyEngine
from app.analytics.diagnosis import DiagnosisEngine
from app.analytics.health import HealthEngine
from app.analytics.rul import RULEstimator
from app.db import crud
from app.engine.state_estimator import StateEstimator
from app.engine.twin import DigitalTwinModel, compute_residuals
from app.models.schemas import PipelineFrame, TelemetryPoint
from app.services.advisory import generate_maintenance_advisory


class DigitalTwinPipeline:
    def __init__(self, engine_id: str = "VIRTUAL-001") -> None:
        self.twin = DigitalTwinModel()
        self.estimator = StateEstimator()
        self.anomaly = AnomalyEngine()
        self.diagnosis = DiagnosisEngine()
        self.health = HealthEngine()
        self.rul = RULEstimator()

        self.engine_id = engine_id
        self.current_mission_id: Optional[int] = None
        self.current_preset = "normal_endurance"
        self.sequence = 0
        self.last_timestamp: Optional[datetime] = None

    def reset_state(self) -> None:
        self.twin = DigitalTwinModel()
        self.estimator.reset_state()
        self.anomaly.reset_state()
        self.diagnosis.reset_state()
        self.health.reset_state()
        self.rul.reset_state()
        self.current_mission_id = None
        self.current_preset = "normal_endurance"
        self.sequence = 0
        self.last_timestamp = None

    def start_mission(
        self,
        db: Session,
        *,
        name: str,
        source: str,
        preset: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        self.reset_state()
        self.current_preset = preset or "normal_endurance"
        mission = crud.create_mission(
            db,
            name=name,
            source=source,
            preset=preset,
            metadata=metadata or {},
            engine_id=self.engine_id,
        )
        self.current_mission_id = mission.id
        return mission.id

    def end_mission(self, db: Session) -> None:
        if self.current_mission_id is None:
            return
        crud.complete_mission(db, self.current_mission_id)
        self.current_mission_id = None

    def process(self, db: Session, telemetry: TelemetryPoint) -> PipelineFrame:
        dt_sec = 1.0
        if self.last_timestamp is not None:
            dt_sec = max(0.2, min(5.0, (telemetry.timestamp - self.last_timestamp).total_seconds()))
        self.last_timestamp = telemetry.timestamp

        estimated = self.estimator.update(telemetry, dt_sec=dt_sec)
        expected = self.twin.predict(telemetry, estimated, dt_sec=dt_sec)
        residuals = compute_residuals(estimated, expected)
        anomaly = self.anomaly.score(telemetry, residuals)
        diagnosis = self.diagnosis.diagnose(telemetry, residuals, anomaly, preset=self.current_preset, expected=expected)
        health = self.health.update(telemetry, residuals, anomaly, diagnosis, dt_sec=dt_sec)
        rul = self.rul.update(health, anomaly.score, diagnosis.confidence, dt_sec=dt_sec)
        maintenance = generate_maintenance_advisory(anomaly, diagnosis, health)

        frame = PipelineFrame(
            mission_id=self.current_mission_id,
            sequence=self.sequence,
            telemetry=telemetry,
            estimated=estimated,
            expected=expected,
            residuals=residuals,
            anomaly=anomaly,
            diagnosis=diagnosis,
            health=health,
            rul=rul,
            maintenance=maintenance,
        )
        self.sequence += 1

        crud.save_pipeline_frame(db, frame)
        return frame
