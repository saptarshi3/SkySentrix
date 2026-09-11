from __future__ import annotations

import logging
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple
import joblib
import numpy as np

from app.analytics.feature_extractor import DiagnosisFeatureExtractor, FEATURE_NAMES
from app.models.schemas import AnomalyResult, DiagnosisResult, ResidualEntry, TelemetryPoint

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
MODEL_PATH = MODELS_DIR / "diagnosis_classifier.joblib"

# Subsystems mapping for frontend / 3D engine hotspots
FAULT_TO_SUBSYSTEMS: Dict[str, List[str]] = {
    "injector_degradation": ["fuel", "combustion"],
    "misfire": ["combustion", "mechanical"],
    "lubrication_problem": ["lubrication", "mechanical"],
    "overheating": ["thermal", "combustion"],
    "excessive_vibration": ["mechanical"],
    "combustion_instability": ["combustion", "thermal"],
    "sensor_drift": ["sensor"],
    "sensor_failure": ["sensor"],
    "fuel_system_degradation": ["fuel", "combustion"],
    "alternator_problem": ["electrical"],
    "healthy": [],
    "normal": [],
}

# Global cached model bundle to prevent reloading per tick
_CACHED_MODEL_BUNDLE: Optional[Dict[str, Any]] = None
_MODEL_LOAD_ATTEMPTED = False


def _load_production_model() -> Optional[Dict[str, Any]]:
    """Safe lazy loader for the trained ML classifier bundle."""
    global _CACHED_MODEL_BUNDLE, _MODEL_LOAD_ATTEMPTED
    if _MODEL_LOAD_ATTEMPTED:
        return _CACHED_MODEL_BUNDLE

    _MODEL_LOAD_ATTEMPTED = True
    if not MODEL_PATH.exists():
        logger.error("Diagnosis model file not found at %s. ML classifier cannot be loaded.", MODEL_PATH)
        return None

    try:
        bundle = joblib.load(MODEL_PATH)
        # Validate bundle integrity
        assert "model" in bundle, "Missing 'model' in model bundle"
        assert "feature_names" in bundle, "Missing 'feature_names' in bundle"
        assert len(bundle["feature_names"]) == 39, f"Expected 39 features, found {len(bundle['feature_names'])}"
        assert bundle["feature_names"] == FEATURE_NAMES, "Feature names order mismatch with feature_extractor.py"
        _CACHED_MODEL_BUNDLE = bundle
        logger.info("Successfully loaded production DiagnosisClassifier (%s) from %s", bundle.get("model_type"), MODEL_PATH)
        return _CACHED_MODEL_BUNDLE
    except Exception as exc:
        logger.error("Failed to load or validate diagnosis model bundle from %s: %s", MODEL_PATH, exc, exc_info=True)
        _CACHED_MODEL_BUNDLE = None
        return None


class DiagnosisEngine:
    """
    Production Diagnosis Engine.
    
    Primary inference path:
      Telemetry + Residuals + Expected
      -> Shared DiagnosisFeatureExtractor (39 features)
      -> ExtraTreesClassifier (diagnosis_classifier.joblib)
      -> Class Probabilities (predict_proba)
      -> Temporal Stabilization (30-step rolling window majority vote)
      -> Production DiagnosisResult
    """

    def __init__(self, window_size: int = 30) -> None:
        self.feature_extractor = DiagnosisFeatureExtractor(window_size=window_size)
        self.prediction_history: Deque[str] = deque(maxlen=window_size)
        self.probability_history: Deque[float] = deque(maxlen=window_size)
        self.step_count = 0

        # Load production model bundle
        self.bundle = _load_production_model()

    @staticmethod
    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))

    def reset_state(self) -> None:
        """Reset internal rolling state on new mission start."""
        self.feature_extractor.reset()
        self.prediction_history.clear()
        self.probability_history.clear()
        self.step_count = 0

    def diagnose(
        self,
        telemetry: TelemetryPoint,
        residuals: Dict[str, ResidualEntry],
        anomaly: AnomalyResult,
        preset: str = "normal_endurance",
        expected: Optional[Any] = None,
    ) -> DiagnosisResult:
        self.step_count += 1

        # 1. Feature Extraction via shared DiagnosisFeatureExtractor
        feats = self.feature_extractor.extract_features(
            telemetry_or_frame=telemetry,
            residuals=residuals,
            expected=expected,
        )

        # 2. Strict feature count & order verification
        if len(FEATURE_NAMES) != 39:
            logger.error("Feature count assertion failed: expected 39, got %d", len(FEATURE_NAMES))
            return self._fallback_safe_result(anomaly, residuals, "Feature validation mismatch")

        # 3. ML Model Inference
        raw_pred = "healthy"
        raw_proba = 0.5
        all_probas: Dict[str, float] = {}

        if self.bundle is not None:
            try:
                clf = self.bundle["model"]
                feature_vector = np.array([[feats[name] for name in FEATURE_NAMES]], dtype=np.float32)
                
                # Model inference
                pred_label = str(clf.predict(feature_vector)[0])
                if hasattr(clf, "predict_proba"):
                    probas = clf.predict_proba(feature_vector)[0]
                    classes = list(clf.classes_)
                    all_probas = {c: float(p) for c, p in zip(classes, probas)}
                    pred_prob = float(all_probas.get(pred_label, max(probas)))
                else:
                    pred_prob = 0.75

                raw_pred = pred_label
                raw_proba = float(np.clip(pred_prob, 0.0, 1.0))
            except Exception as e:
                logger.error("ML model inference failed: %s", e, exc_info=True)
                return self._fallback_safe_result(anomaly, residuals, f"Inference failure: {e}")
        else:
            logger.warning("Production model bundle is unavailable; using nominal fallback.")
            return self._fallback_safe_result(anomaly, residuals, "Model bundle unavailable")

        # 4. Temporal Stabilization
        self.prediction_history.append(raw_pred)
        self.probability_history.append(raw_proba)

        # 4a. Warmup window (steps < 15): feature extractor rolling windows are unpopulated
        # Training dataset was strictly constructed on step >= 20.
        if self.step_count < 15:
            evidence = {
                "egt_deviation_pct": round(feats.get("egt_pos_res", 0.0), 2),
                "fuel_flow_deviation_pct": round(feats.get("fuel_pos_res", 0.0) - feats.get("fuel_neg_res", 0.0), 2),
                "rpm_instability_pct": round(feats.get("rpm_instability", 0.0), 2),
                "vibration_deviation_pct": round(feats.get("vib_pos_res", 0.0), 2),
            }
            return DiagnosisResult(
                probable_fault="normal",
                confidence=round(float(self._clamp(raw_proba * 0.85, 0.05, 0.95)), 4),
                contributing_parameters=[],
                affected_subsystems=[],
                evidence=evidence,
                explanation="Engine operating within nominal startup/warmup envelope.",
            )

        # 4b. Recent window consensus (last 8 ticks) for responsive fault onset tracking
        recent_len = min(8, len(self.prediction_history))
        recent_preds = list(self.prediction_history)[-recent_len:]
        recent_probs = list(self.probability_history)[-recent_len:]
        recent_votes = Counter(recent_preds)
        recent_top, recent_top_cnt = recent_votes.most_common(1)[0]
        recent_ratio = recent_top_cnt / recent_len

        # Window (30-step) consensus
        votes = Counter(self.prediction_history)
        window_top, window_cnt = votes.most_common(1)[0]
        window_ratio = window_cnt / len(self.prediction_history)

        # Promptly confirm fault when recent window establishes clear fault consensus
        if recent_top != "healthy" and recent_ratio >= 0.50:
            confirmed_pred = recent_top
            vote_ratio = recent_ratio
            class_probs = [p for pred, p in zip(recent_preds, recent_probs) if pred == recent_top]
            mean_confirmed_proba = float(np.mean(class_probs))
        else:
            confirmed_pred = window_top
            vote_ratio = window_ratio
            class_probs = [p for pred, p in zip(self.prediction_history, self.probability_history) if pred == confirmed_pred]
            mean_confirmed_proba = float(np.mean(class_probs)) if class_probs else raw_proba

        # Compute final exposed model probability [0, 1]
        stabilized_confidence = float(self._clamp(mean_confirmed_proba * (0.6 + 0.4 * vote_ratio), 0.05, 0.99))

        # 4c. Anomaly & Confidence Gating:
        # Under nominal operation (NORMAL anomaly level and low anomaly score < 0.35),
        # prevent arbitrary low-probability classifications (< 38%) from triggering false alarms.
        if confirmed_pred != "healthy":
            if anomaly.level == "NORMAL" and anomaly.score < 0.35 and stabilized_confidence < 0.38:
                confirmed_pred = "healthy"

        # 5. Output mapping: If confirmed diagnosis is "healthy", map probable_fault to "normal"
        # for frontend and advisory backward compatibility
        is_healthy = (confirmed_pred == "healthy")
        probable_fault = "normal" if is_healthy else confirmed_pred

        # 6. Directional evidence for frontend and inspector display
        evidence = {
            "egt_deviation_pct": round(feats.get("egt_pos_res", 0.0), 2),
            "fuel_flow_deviation_pct": round(feats.get("fuel_pos_res", 0.0) - feats.get("fuel_neg_res", 0.0), 2),
            "rpm_instability_pct": round(feats.get("rpm_instability", 0.0), 2),
            "vibration_deviation_pct": round(feats.get("vib_pos_res", 0.0), 2),
            "oil_pressure_drop_pct": round(feats.get("oil_p_neg_res", 0.0), 2),
            "oil_temp_deviation_pct": round(feats.get("oil_t_pos_res", 0.0), 2),
            "manifold_deviation_pct": round(feats.get("res_map_pct", 0.0), 2),
            "battery_voltage_drop_pct": round(feats.get("batt_neg_res", 0.0), 2),
        }

        # 7. Contributing parameters based on dominant observed residuals
        sorted_evidence = sorted(evidence.items(), key=lambda kv: abs(kv[1]), reverse=True)
        contributors: List[str] = [k for k, v in sorted_evidence[:4] if abs(v) > 0.1]
        if not contributors and not is_healthy:
            contributors = anomaly.contributing_parameters

        # 8. Explanation formatting
        if is_healthy:
            explanation = (
                f"Model prediction: healthy (probability: {raw_proba*100:.1f}%, temporal consensus: {vote_ratio*100:.0f}%). "
                "Operating state is nominal with no sustained fault pattern."
            )
            subsystems: List[str] = []
        else:
            readable = confirmed_pred.replace("_", " ")
            dominant_indicators = ", ".join(contributors) if contributors else "aggregate residual signature"
            explanation = (
                f"Model prediction: {readable} (probability: {raw_proba*100:.1f}%, temporal consensus: {vote_ratio*100:.0f}%). "
                f"Dominant observed indicators: {dominant_indicators}."
            )
            subsystems = FAULT_TO_SUBSYSTEMS.get(confirmed_pred, [])

        return DiagnosisResult(
            probable_fault=probable_fault,
            confidence=round(stabilized_confidence, 4),
            contributing_parameters=contributors,
            affected_subsystems=subsystems,
            evidence=evidence,
            explanation=explanation,
        )

    def _fallback_safe_result(
        self,
        anomaly: AnomalyResult,
        residuals: Dict[str, ResidualEntry],
        reason: str,
    ) -> DiagnosisResult:
        """Safe nominal fallback if ML model execution cannot proceed."""
        evidence = {
            "egt_deviation_pct": round(max(0.0, residuals.get("egt", ResidualEntry(0, 0, 0, 0)).residual_pct), 2),
            "rpm_instability_pct": 0.0,
            "vibration_deviation_pct": round(max(0.0, residuals.get("vibration", ResidualEntry(0, 0, 0, 0)).residual_pct), 2),
            "oil_pressure_drop_pct": round(max(0.0, -residuals.get("oil_pressure", ResidualEntry(0, 0, 0, 0)).residual_pct), 2),
        }
        return DiagnosisResult(
            probable_fault="normal",
            confidence=0.10,
            contributing_parameters=anomaly.contributing_parameters,
            affected_subsystems=[],
            evidence=evidence,
            explanation=f"Diagnosis fallback engaged ({reason}). Telemetry monitored in safe state.",
        )
