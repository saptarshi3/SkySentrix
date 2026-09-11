"""
Feature Extractor for Aero Piston Engine Digital Twin Fault Diagnosis.
Extracts:
1. Raw & Residual Normalized Features
2. Temporal Instability & Trend Features
3. Operating Context Features
4. Physical Orthogonal Separation Ratios
5. Sensor Fault Detection Signatures
"""
from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Optional
import numpy as np

EPSILON = 1e-6

FEATURE_NAMES = [
    "res_rpm_pct",
    "res_egt_pct",
    "res_cht_pct",
    "res_oil_p_pct",
    "res_oil_t_pct",
    "res_fuel_pct",
    "res_vib_pct",
    "res_batt_pct",
    "res_map_pct",
    "rpm_abs_res",
    "egt_pos_res",
    "cht_pos_res",
    "oil_p_neg_res",
    "oil_t_pos_res",
    "vib_pos_res",
    "batt_neg_res",
    "fuel_pos_res",
    "fuel_neg_res",
    "rpm_instability",
    "egt_instability",
    "vib_instability",
    "oil_p_instability",
    "egt_res_slope",
    "oil_p_res_slope",
    "cht_res_slope",
    "ratio_oil_p_drop_to_rpm_drop",
    "ratio_cht_to_egt",
    "ratio_vib_to_rpm_instab",
    "ratio_fuel_to_rpm_res",
    "air_fuel_ratio_dev",
    "ratio_egt_shift_to_var",
    "sensor_flatline_detected",
    "single_channel_dominance",
    "drift_persistence_votes",
    "throttle",
    "engine_load",
    "altitude",
    "ambient_temp",
    "engine_efficiency",
]

class DiagnosisFeatureExtractor:
    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self.reset()

    def reset(self):
        self.rpm_hist = deque(maxlen=self.window_size)
        self.egt_hist = deque(maxlen=self.window_size)
        self.cht_hist = deque(maxlen=self.window_size)
        self.oil_p_hist = deque(maxlen=self.window_size)
        self.oil_t_hist = deque(maxlen=self.window_size)
        self.fuel_hist = deque(maxlen=self.window_size)
        self.vib_hist = deque(maxlen=self.window_size)
        self.batt_hist = deque(maxlen=self.window_size)
        self.map_hist = deque(maxlen=self.window_size)
        
        # Residual histories
        self.res_rpm_hist = deque(maxlen=self.window_size)
        self.res_egt_hist = deque(maxlen=self.window_size)
        self.res_cht_hist = deque(maxlen=self.window_size)
        self.res_oil_p_hist = deque(maxlen=self.window_size)
        self.res_oil_t_hist = deque(maxlen=self.window_size)
        self.res_fuel_hist = deque(maxlen=self.window_size)
        self.res_vib_hist = deque(maxlen=self.window_size)
        self.res_batt_hist = deque(maxlen=self.window_size)
        self.res_map_hist = deque(maxlen=self.window_size)

    def extract_features(
        self,
        telemetry_or_frame: Any,
        residuals: Optional[Dict[str, Any]] = None,
        expected: Optional[Any] = None,
    ) -> Dict[str, float]:
        """Extract a full numerical feature vector from a single PipelineFrame or (telemetry, residuals, expected)."""
        if residuals is None and hasattr(telemetry_or_frame, "residuals"):
            t = telemetry_or_frame.telemetry
            exp = getattr(telemetry_or_frame, "expected", None)
            res = telemetry_or_frame.residuals
        else:
            t = telemetry_or_frame
            exp = expected
            res = residuals

        # 1. Update rolling histories
        self.rpm_hist.append(float(t.rpm))
        self.egt_hist.append(float(t.egt))
        self.cht_hist.append(float(t.cht))
        self.oil_p_hist.append(float(t.oil_pressure))
        self.oil_t_hist.append(float(t.oil_temp))
        self.fuel_hist.append(float(t.fuel_flow))
        self.vib_hist.append(float(t.vibration))
        self.batt_hist.append(float(t.battery_voltage))
        self.map_hist.append(float(t.manifold_pressure))

        def _get_res_pct(key: str) -> float:
            if not res or key not in res:
                return 0.0
            entry = res[key]
            return float(getattr(entry, "residual_pct", entry))

        r_rpm = _get_res_pct("rpm")
        r_egt = _get_res_pct("egt")
        r_cht = _get_res_pct("cht")
        r_oil_p = _get_res_pct("oil_pressure")
        r_oil_t = _get_res_pct("oil_temp")
        r_fuel = _get_res_pct("fuel_flow")
        r_vib = _get_res_pct("vibration")
        r_batt = _get_res_pct("battery_voltage")
        r_map = _get_res_pct("manifold_pressure")

        self.res_rpm_hist.append(r_rpm)
        self.res_egt_hist.append(r_egt)
        self.res_cht_hist.append(r_cht)
        self.res_oil_p_hist.append(r_oil_p)
        self.res_oil_t_hist.append(r_oil_t)
        self.res_fuel_hist.append(r_fuel)
        self.res_vib_hist.append(r_vib)
        self.res_batt_hist.append(r_batt)
        self.res_map_hist.append(r_map)

        # 2. Basic Residuals & Directional Features
        feats: Dict[str, float] = {
            "res_rpm_pct": r_rpm,
            "res_egt_pct": r_egt,
            "res_cht_pct": r_cht,
            "res_oil_p_pct": r_oil_p,
            "res_oil_t_pct": r_oil_t,
            "res_fuel_pct": r_fuel,
            "res_vib_pct": r_vib,
            "res_batt_pct": r_batt,
            "res_map_pct": r_map,

            "rpm_abs_res": abs(r_rpm),
            "egt_pos_res": max(0.0, r_egt),
            "cht_pos_res": max(0.0, r_cht),
            "oil_p_neg_res": max(0.0, -r_oil_p),
            "oil_t_pos_res": max(0.0, r_oil_t),
            "vib_pos_res": max(0.0, r_vib),
            "batt_neg_res": max(0.0, -r_batt),
            "fuel_pos_res": max(0.0, r_fuel),
            "fuel_neg_res": max(0.0, -r_fuel),
        }

        # 3. Temporal Features (rolling statistics)
        def std_or_zero(hist):
            return float(np.std(hist)) if len(hist) > 4 else 0.0

        def slope_or_zero(hist):
            if len(hist) < 6:
                return 0.0
            x = np.arange(len(hist))
            return float(np.polyfit(x, hist, 1)[0])

        rpm_mean = float(np.mean(self.rpm_hist)) if self.rpm_hist else 1.0
        rpm_instability = (std_or_zero(self.rpm_hist) / max(rpm_mean, 100.0)) * 100.0
        egt_instability = std_or_zero(self.egt_hist)
        vib_instability = std_or_zero(self.vib_hist)
        oil_p_instability = std_or_zero(self.oil_p_hist)

        feats["rpm_instability"] = rpm_instability
        feats["egt_instability"] = egt_instability
        feats["vib_instability"] = vib_instability
        feats["oil_p_instability"] = oil_p_instability

        feats["egt_res_slope"] = slope_or_zero(self.res_egt_hist)
        feats["oil_p_res_slope"] = slope_or_zero(self.res_oil_p_hist)
        feats["cht_res_slope"] = slope_or_zero(self.res_cht_hist)

        # 4. Physical Orthogonal Separation Ratios (Safely divided with EPSILON)
        # Ratio 1: Oil pressure drop vs RPM drop (Dominant in lubrication failure)
        feats["ratio_oil_p_drop_to_rpm_drop"] = (feats["oil_p_neg_res"] + EPSILON) / (feats["rpm_abs_res"] + EPSILON)

        # Ratio 2: CHT spike vs EGT spike (Dominant in cylinder head overheating vs pure combustion)
        feats["ratio_cht_to_egt"] = (feats["cht_pos_res"] + EPSILON) / (feats["egt_pos_res"] + EPSILON)

        # Ratio 3: Vibration residual vs RPM instability (Dominant in mechanical balance / prop failure)
        feats["ratio_vib_to_rpm_instab"] = (feats["vib_pos_res"] + EPSILON) / (feats["rpm_instability"] + EPSILON)

        # Ratio 4: Fuel flow residual vs RPM residual
        feats["ratio_fuel_to_rpm_res"] = (r_fuel + EPSILON) / (r_rpm + EPSILON)

        # Ratio 5: Air mass flow deviation vs Fuel flow deviation
        air_actual = getattr(t, 'air_mass_flow', 0.0) or 0.0
        air_exp = getattr(exp, 'air_mass_flow', 0.0) or (air_actual if air_actual > 0 else 0.1)
        air_res_pct = ((air_actual - air_exp) / max(air_exp, 1e-4)) * 100.0 if air_exp > 0 else 0.0
        feats["air_fuel_ratio_dev"] = air_res_pct - r_fuel

        # Ratio 6: EGT mean shift vs EGT variance (Combustion instability has high variance, low shift; Injector has high shift)
        feats["ratio_egt_shift_to_var"] = (feats["egt_pos_res"] + EPSILON) / (egt_instability + EPSILON)

        # 5. Sensor Fault Discrimination Features
        # Flatline detection: range of raw signal < 0.02
        flatline_cnt = 0
        for h in [self.rpm_hist, self.egt_hist, self.oil_p_hist, self.batt_hist]:
            if len(h) >= 8 and (max(h) - min(h)) < 0.02:
                flatline_cnt += 1
        feats["sensor_flatline_detected"] = 1.0 if flatline_cnt > 0 else 0.0

        # Single-channel residual dominance: Max residual divided by second max residual
        all_res_abs = sorted([abs(r_rpm), abs(r_egt), abs(r_cht), abs(r_oil_p), abs(r_oil_t), abs(r_fuel), abs(r_vib), abs(r_batt)], reverse=True)
        max_r = all_res_abs[0]
        second_max_r = all_res_abs[1] if len(all_res_abs) > 1 else 0.0
        feats["single_channel_dominance"] = (max_r + EPSILON) / (second_max_r + EPSILON)

        # Drift persistence: low variance in residual history with non-zero mean
        drift_votes = 0
        for h in [self.res_egt_hist, self.res_cht_hist, self.res_oil_p_hist, self.res_oil_t_hist]:
            if len(h) >= 10:
                abs_m = abs(float(np.mean(h)))
                spread = float(np.max(h) - np.min(h))
                if abs_m > 4.0 and spread < 5.0:
                    drift_votes += 1
        feats["drift_persistence_votes"] = float(drift_votes)

        # 6. Operating Context
        feats["throttle"] = float(t.throttle)
        feats["engine_load"] = float(t.engine_load)
        feats["altitude"] = float(t.altitude)
        feats["ambient_temp"] = float(t.ambient_temp)
        feats["engine_efficiency"] = float(t.engine_efficiency)

        return feats

    def extract_vector(
        self,
        telemetry_or_frame: Any,
        residuals: Optional[Dict[str, Any]] = None,
        expected: Optional[Any] = None,
    ) -> np.ndarray:
        feats = self.extract_features(telemetry_or_frame, residuals=residuals, expected=expected)
        return np.array([feats[k] for k in FEATURE_NAMES], dtype=np.float32)
