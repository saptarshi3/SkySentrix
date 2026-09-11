"""
Feature Extractor for Aero Piston Engine Digital Twin Fault Diagnosis.
Extracts:
1. Raw & Residual Normalized Features
2. Temporal Instability & Trend Features
3. Operating Context Features
4. Physical Orthogonal Separation Ratios
5. Sensor Fault Detection Signatures
"""
from app.analytics.feature_extractor import (
    DiagnosisFeatureExtractor,
    FEATURE_NAMES,
    EPSILON,
)

__all__ = ["DiagnosisFeatureExtractor", "FEATURE_NAMES", "EPSILON"]
