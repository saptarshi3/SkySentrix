"""Debug diagnosis scoring for fuel_system_degradation"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pipeline import DigitalTwinPipeline
from scripts.trajectory_utils import run_fault_trajectory
from app.analytics.diagnosis import BASELINE_FEATURES

pipeline = DigitalTwinPipeline()
frames, sim = run_fault_trajectory(pipeline, 'normal_endurance', 706, 180, 'fuel_system_degradation', 0.75, 0.01, 60)

# Check step 170 (closer to end)
frame = frames[170]
print('=== Step 170 ===')

# Get the actual diagnosis scores
print(f'Actual diagnosis: {frame.diagnosis.probable_fault}')
print(f'Diagnosis scores: {frame.diagnosis.evidence}')

baselines = BASELINE_FEATURES['normal_endurance']
fuel_flow_signed_raw = frame.residuals['fuel_flow'].residual_pct
fuel_flow_signed_excess = fuel_flow_signed_raw - baselines['fuel_flow_signed']
fuel_flow_neg = max(0, -fuel_flow_signed_excess)
print(f'Fuel flow neg (after baseline): {fuel_flow_neg:.2f}')

rpm_abs_raw = abs(frame.residuals["rpm"].residual_pct)
print(f'rpm_abs raw: {rpm_abs_raw:.2f}')
vibration_raw = max(0, frame.residuals["vibration"].residual_pct)
print(f'vibration raw: {vibration_raw:.2f}')

# Get rpm_instability from history
rpm_history = [f.telemetry.rpm for f in frames[:171]]
mean_rpm = sum(rpm_history[-30:]) / min(30, len(rpm_history))
import statistics
std_rpm = statistics.pstdev(rpm_history[-30:]) if len(rpm_history) >= 6 else 0
rpm_instability_raw = 100 * std_rpm / mean_rpm if mean_rpm > 0 else 0
rpm_instability = max(0, rpm_instability_raw - baselines['rpm_instability'])
print(f'rpm_instability_raw: {rpm_instability_raw:.2f}')
print(f'rpm_instability (after baseline): {rpm_instability:.2f}')

vibration_pos = max(0, vibration_raw - baselines['vibration_pos'])
print(f'vibration_pos (after baseline): {vibration_pos:.2f}')

egt_pos_raw = max(0, frame.residuals['egt'].residual_pct)
egt_pos = max(0, egt_pos_raw - baselines['egt_pos'])
print(f'egt_pos (after baseline): {egt_pos:.2f}')

manifold_pos_raw = max(0, frame.residuals['manifold_pressure'].residual_pct)
manifold_pos = max(0, manifold_pos_raw - baselines['manifold_pos'])
print(f'manifold_pos (after baseline): {manifold_pos:.2f}')

egt_history = [f.telemetry.egt for f in frames[:171]]
egt_instability = statistics.pstdev(egt_history[-30:]) if len(egt_history) >= 6 else 0
print(f'egt_instability: {egt_instability:.2f}')

# Calculate scores
misfire_score = 3.0 * rpm_abs_raw + 2.0 * rpm_instability + 1.5 * vibration_pos + 0.05 * fuel_flow_neg
fuel_system_score = 4.0 * fuel_flow_neg + 1.5 * manifold_pos + 1.2 * egt_pos
combustion_score = 8.0 * egt_instability + 0.5 * rpm_abs_raw + 1.0 * vibration_pos + 1.0 * rpm_instability

print(f'Misfire score: {misfire_score:.2f}')
print(f'Fuel system score: {fuel_system_score:.2f}')
print(f'Combustion score: {combustion_score:.2f}')

# Check sensor drift
egt_residuals = [f.residuals['egt'].residual_pct for f in frames[150:171]]
cht_residuals = [f.residuals['cht'].residual_pct for f in frames[150:171]]
oil_temp_residuals = [f.residuals['oil_temp'].residual_pct for f in frames[150:171]]
fuel_flow_residuals = [f.residuals['fuel_flow'].residual_pct for f in frames[150:171]]
oil_pressure_residuals = [f.residuals['oil_pressure'].residual_pct for f in frames[150:171]]

def is_drift(residuals):
    abs_mean = abs(sum(residuals) / len(residuals))
    spread = max(residuals) - min(residuals)
    return abs_mean > 4.0 and spread < 5.0

print(f'EGT drift: {is_drift(egt_residuals)}')
print(f'CHT drift: {is_drift(cht_residuals)}')
print(f'Oil temp drift: {is_drift(oil_temp_residuals)}')
print(f'Fuel flow drift: {is_drift(fuel_flow_residuals)}')
print(f'Oil pressure drift: {is_drift(oil_pressure_residuals)}')

drifting_keys = [k for k, r in [('egt', egt_residuals), ('cht', cht_residuals), ('oil_temp', oil_temp_residuals), ('fuel_flow', fuel_flow_residuals), ('oil_pressure', oil_pressure_residuals)] if is_drift(r)]
print(f'Drifting keys: {drifting_keys}')
sensor_drift_score = 75.0 if drifting_keys else 0.0
print(f'Sensor drift score: {sensor_drift_score}')
