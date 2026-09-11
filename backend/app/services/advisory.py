from __future__ import annotations

from app.models.schemas import AnomalyResult, DiagnosisResult, MaintenanceAdvisory, HealthResult


def generate_maintenance_advisory(
    anomaly: AnomalyResult,
    diagnosis: DiagnosisResult,
    health: HealthResult,
) -> MaintenanceAdvisory:
    if anomaly.level == "CRITICAL" or health.health_index <= 55:
        if diagnosis.probable_fault != "normal":
            msg = (
                f"Severe abnormality detected ({diagnosis.probable_fault.replace('_', ' ')}). "
                "Further operation should be evaluated before continuation."
            )
        else:
            msg = "Severe abnormality detected. Further operation should be evaluated."
        return MaintenanceAdvisory(level="CRITICAL", message=msg)

    if anomaly.level == "WARNING" or health.health_index <= 82 or diagnosis.confidence >= 0.7:
        if diagnosis.probable_fault != "normal":
            msg = (
                f"Progressive {diagnosis.probable_fault.replace('_', ' ')} suspected. "
                "Inspection recommended during next maintenance window."
            )
        else:
            msg = "Parameter deviations observed. Schedule inspection and monitor trends."
        return MaintenanceAdvisory(level="WARNING", message=msg)

    return MaintenanceAdvisory(
        level="NORMAL",
        message="Engine operating within expected envelope.",
    )
