from __future__ import annotations

import json
import math
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque, Dict, List, Optional

import numpy as np

try:
    import joblib
except Exception:  # pragma: no cover - joblib ships with scikit-learn
    joblib = None

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from app.models.schemas import AnomalyResult, ResidualEntry, TelemetryPoint

MODEL_DIR = Path(__file__).resolve().parents[2] / "models"
MODEL_VERSION = "anomaly_v2_calibrated"

FEATURE_NAMES: List[str] = [
    "residual_rpm_pct",
    "residual_cht_pct",
    "residual_egt_pct",
    "residual_oil_pressure_pct",
    "residual_oil_temp_pct",
    "residual_fuel_flow_pct",
    "residual_vibration_pct",
    "residual_battery_voltage_pct",
    "residual_manifold_pressure_pct",
    "residual_torque_nm_pct",
    "rpm_delta",
    "egt_delta",
    "vibration_delta",
    "rpm_rolling_std",
    "throttle",
    "engine_load",
    "altitude_norm",
    "ambient_temp_norm",
    "density_ratio",
    "engine_efficiency",
    "regime_code",
]

DEFAULT_WEIGHTS: Dict[str, float] = {
    "iforest": 0.10,
    "residual": 0.58,
    "ewma": 0.32,
    "bias": -0.36,
}

DEFAULT_THRESHOLDS: Dict[str, float] = {
    "warning": 0.42,
    "critical": 0.65,
}


@dataclass
class AnomalyModelArtifact:
    scaler: StandardScaler
    model: IsolationForest
    score_mean: float
    score_std: float
    contamination: float
    weights: Dict[str, float]
    thresholds: Dict[str, float]
    feature_names: List[str]
    version: str
    trained_at: str
    training_source: str
    training_samples: int
    metadata: Dict[str, object] = field(default_factory=dict)


class AnomalyEngine:
    """
    Hybrid anomaly scorer:
      score = w_if * IsolationForest_signal
            + w_res * normalized_residual_signal
            + w_ewma * EWMA(residual_signal)
            + bias

    Model persistence:
      - Looks for a calibrated artifact at backend/models/anomaly_model.joblib
      - If found, loads it (deterministic, no retraining at startup).
      - If not found, falls back to a synthetic training routine
        (`_train_on_synthetic_normal`) and immediately persists that
        fallback artifact so subsequent runs are stable.

    IMPORTANT (data provenance):
      The fallback synthetic trainer builds hand-crafted feature vectors and
      is intentionally narrow/unrealistic. It exists only so the service can
      start with *some* model before calibration has been run. The
      recommended artifact is produced by
      `backend/scripts/calibrate_anomaly.py`, which trains on residual
      features collected from actual simulator+twin+estimator trajectories
      across multiple mission presets, seeds and operating conditions.
    """

    def __init__(
        self,
        seed: int = 42,
        contamination: float = 0.04,
        weights: Optional[Dict[str, float]] = None,
        thresholds: Optional[Dict[str, float]] = None,
        model_dir: Optional[Path] = None,
        auto_load: bool = True,
    ) -> None:
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        self.contamination = contamination
        self.weights = dict(weights or DEFAULT_WEIGHTS)
        self.thresholds = dict(thresholds or DEFAULT_THRESHOLDS)
        self.model_dir = Path(model_dir) if model_dir else MODEL_DIR

        self.scaler = StandardScaler()
        self.model = IsolationForest(
            n_estimators=220,
            contamination=contamination,
            random_state=seed,
        )
        self.prev_points: Deque[TelemetryPoint] = deque(maxlen=20)
        self.residual_ewma = 0.0
        self.score_mean = 0.0
        self.score_std = 1.0
        self.training_source = "uninitialized"
        self.training_samples = 0

        loaded = False
        if auto_load:
            loaded = self._try_load()
        if not loaded:
            self._train_on_synthetic_normal()
            if auto_load:
                self.save()

    @staticmethod
    def _sigmoid(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))

    @staticmethod
    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))

    @staticmethod
    def _regime_code(mode: str) -> float:
        mapping = {
            "shutdown": 0.0,
            "idle": 0.15,
            "takeoff": 0.9,
            "climb": 0.75,
            "cruise": 0.60,
            "loiter": 0.45,
            "high_load": 0.85,
            "descent": 0.30,
        }
        return mapping.get(mode, 0.5)

    def reset_state(self) -> None:
        """Reset per-trajectory sequential state (EWMA, history). Does NOT retrain the model."""
        self.prev_points.clear()
        self.residual_ewma = 0.0

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _artifact_path(self) -> Path:
        return self.model_dir / "anomaly_model.joblib"

    def _metadata_path(self) -> Path:
        return self.model_dir / "anomaly_model.meta.json"

    def save(self) -> None:
        if joblib is None:
            return
        self.model_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "scaler": self.scaler,
            "model": self.model,
            "score_mean": self.score_mean,
            "score_std": self.score_std,
            "contamination": self.contamination,
            "weights": self.weights,
            "thresholds": self.thresholds,
            "feature_names": FEATURE_NAMES,
            "version": MODEL_VERSION,
            "seed": self.seed,
        }
        joblib.dump(payload, self._artifact_path())

        meta = {
            "version": MODEL_VERSION,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "training_source": self.training_source,
            "training_samples": self.training_samples,
            "contamination": self.contamination,
            "weights": self.weights,
            "thresholds": self.thresholds,
            "feature_names": FEATURE_NAMES,
            "n_estimators": self.model.n_estimators,
            "seed": self.seed,
        }
        self._metadata_path().write_text(json.dumps(meta, indent=2))

    def _try_load(self) -> bool:
        if joblib is None:
            return False
        path = self._artifact_path()
        if not path.exists():
            return False
        try:
            payload = joblib.load(path)
        except Exception:
            return False

        if payload.get("feature_names") != FEATURE_NAMES:
            # Stale artifact from an older feature schema; ignore it.
            return False

        self.scaler = payload["scaler"]
        self.model = payload["model"]
        self.score_mean = float(payload["score_mean"])
        self.score_std = float(payload["score_std"])
        self.contamination = float(payload.get("contamination", self.contamination))
        self.weights = dict(payload.get("weights", self.weights))
        self.thresholds = dict(payload.get("thresholds", self.thresholds))

        meta_path = self._metadata_path()
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
                self.training_source = meta.get("training_source", "loaded_artifact")
                self.training_samples = int(meta.get("training_samples", 0))
            except Exception:
                self.training_source = "loaded_artifact"
        else:
            self.training_source = "loaded_artifact"
        return True

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def fit_from_feature_matrix(self, feats: np.ndarray, source: str = "external_calibration") -> None:
        """Fit scaler + IsolationForest directly from a pre-built feature matrix.

        Used by backend/scripts/calibrate_anomaly.py, which builds features
        from actual simulator+twin+estimator trajectories rather than the
        hand-crafted synthetic fallback below.
        """
        scaled = self.scaler.fit_transform(feats)
        self.model.fit(scaled)
        train_scores = -self.model.score_samples(scaled)
        self.score_mean = float(np.mean(train_scores))
        self.score_std = float(np.std(train_scores) + 1e-6)
        self.training_source = source
        self.training_samples = int(feats.shape[0])

    def _train_on_synthetic_normal(self) -> None:
        """Fallback trainer: hand-crafted synthetic feature distribution.

        NOTE: This does not come from running the actual simulator. It is a
        narrow placeholder used only when no calibrated artifact exists yet.
        """
        n = 5000
        throttle = self.rng.uniform(0.1, 0.95, size=n)
        load = self.rng.uniform(0.15, 0.95, size=n)
        altitude = self.rng.uniform(0.0, 8000.0, size=n)
        ambient = self.rng.uniform(-10.0, 40.0, size=n)
        density = self.rng.uniform(0.55, 1.1, size=n)
        regime = self.rng.uniform(0.1, 0.95, size=n)

        residuals = self.rng.normal(0.0, 1.0, size=(n, 10))
        scales = np.array([2.2, 1.2, 1.4, 2.5, 1.7, 2.5, 4.0, 1.0, 2.4, 2.2], dtype=float)
        residuals *= scales

        rpm_delta = self.rng.normal(0.0, 28.0, size=n)
        egt_delta = self.rng.normal(0.0, 3.0, size=n)
        vib_delta = self.rng.normal(0.0, 0.02, size=n)
        eff = self.rng.uniform(0.86, 0.97, size=n)
        roll_std = self.rng.uniform(0.0, 4.0, size=n)

        feats = np.column_stack(
            [
                residuals,
                rpm_delta,
                egt_delta,
                vib_delta,
                roll_std,
                throttle,
                load,
                altitude / 10000.0,
                ambient / 50.0,
                density,
                eff,
                regime,
            ]
        )
        self.fit_from_feature_matrix(feats, source="synthetic_fallback_handcrafted")

    def _rolling_std(self, key: str) -> float:
        if len(self.prev_points) < 4:
            return 0.0
        arr = np.array([getattr(p, key) for p in self.prev_points], dtype=float)
        return float(np.std(arr))

    def build_feature_vector(self, telemetry: TelemetryPoint, residuals: Dict[str, ResidualEntry]) -> np.ndarray:
        if self.prev_points:
            prev = self.prev_points[-1]
            rpm_delta = telemetry.rpm - prev.rpm
            egt_delta = telemetry.egt - prev.egt
            vib_delta = telemetry.vibration - prev.vibration
        else:
            rpm_delta = 0.0
            egt_delta = 0.0
            vib_delta = 0.0

        roll_std = self._rolling_std("rpm")

        vec = np.array(
            [
                residuals["rpm"].residual_pct,
                residuals["cht"].residual_pct,
                residuals["egt"].residual_pct,
                residuals["oil_pressure"].residual_pct,
                residuals["oil_temp"].residual_pct,
                residuals["fuel_flow"].residual_pct,
                residuals["vibration"].residual_pct,
                residuals["battery_voltage"].residual_pct,
                residuals["manifold_pressure"].residual_pct,
                residuals["torque_nm"].residual_pct,
                rpm_delta,
                egt_delta,
                vib_delta,
                roll_std,
                telemetry.throttle,
                telemetry.engine_load,
                telemetry.altitude / 10000.0,
                telemetry.ambient_temp / 50.0,
                telemetry.density_ratio,
                telemetry.engine_efficiency,
                self._regime_code(telemetry.mode),
            ],
            dtype=float,
        )
        return vec

    # Backward-compatible alias (used by earlier experiment code).
    _build_feature_vector = build_feature_vector

    def score(self, telemetry: TelemetryPoint, residuals: Dict[str, ResidualEntry]) -> AnomalyResult:
        feat = self.build_feature_vector(telemetry, residuals)
        scaled = self.scaler.transform(feat.reshape(1, -1))

        raw_score = float(-self.model.score_samples(scaled)[0])
        z = (raw_score - self.score_mean) / self.score_std
        iforest_component = self._sigmoid(z)

        if telemetry.mode == "idle":
            mode_scale = 2.5
        elif telemetry.mode in {"takeoff", "high_load", "climb"}:
            mode_scale = 1.2
        else:
            mode_scale = 1.0
        threshold_pcts = {
            "rpm": 8.0 * mode_scale,
            "cht": 7.0 * mode_scale,
            "egt": 7.0 * mode_scale,
            "oil_pressure": 9.0 * mode_scale,
            "oil_temp": 8.0 * mode_scale,
            "fuel_flow": 12.0 * mode_scale,
            "vibration": 20.0 * mode_scale,
            "battery_voltage": 3.5,
            "manifold_pressure": 8.0 * mode_scale,
            "torque_nm": 14.0 * mode_scale,
        }

        normalized_mags: List[float] = []
        for key, thr in threshold_pcts.items():
            normalized_mags.append(abs(residuals[key].residual_pct) / max(thr, 1e-6))

        norms = np.array(normalized_mags, dtype=float)
        mean_norm = float(np.mean(norms))
        p85_norm = float(np.percentile(norms, 85))
        residual_component = self._clamp((0.60 * mean_norm + 0.40 * p85_norm) / 3.5, 0.0, 1.0)

        self.residual_ewma = 0.92 * self.residual_ewma + 0.08 * residual_component
        ewma_component = self._clamp((self.residual_ewma - 0.28) / 0.55, 0.0, 1.0)

        combined = (
            self.weights["iforest"] * iforest_component
            + self.weights["residual"] * residual_component
            + self.weights["ewma"] * ewma_component
            + self.weights["bias"]
        )
        combined = self._clamp(combined, 0.0, 1.0)

        if combined >= self.thresholds["critical"]:
            level = "CRITICAL"
        elif combined >= self.thresholds["warning"]:
            level = "WARNING"
        else:
            level = "NORMAL"

        ranked = sorted(
            residuals.items(),
            key=lambda kv: abs(kv[1].residual_pct),
            reverse=True,
        )
        contributors = [k for k, v in ranked[:5] if abs(v.residual_pct) >= 1.2]

        self.prev_points.append(telemetry)

        return AnomalyResult(
            score=combined,
            level=level,
            timestamp=telemetry.timestamp,
            contributing_parameters=contributors,
        )
