export type AnomalyLevel = 'NORMAL' | 'WARNING' | 'CRITICAL'
export type MaintenanceLevel = 'NORMAL' | 'WARNING' | 'CRITICAL'

export interface TelemetryPoint {
  timestamp: string
  mode: string
  rpm: number
  cht: number
  egt: number
  oil_pressure: number
  oil_temp: number
  fuel_flow: number
  vibration: number
  battery_voltage: number
  alternator_health: number
  injection_timing: number
  throttle: number
  engine_load: number
  altitude: number
  ambient_temp: number
  engine_efficiency: number
  manifold_pressure?: number
  air_mass_flow?: number
  torque_nm?: number
  power_kw?: number
  propeller_load?: number
  airspeed?: number
  pressure_kpa?: number
  density_ratio?: number
  subsystem_health?: Record<string, number>
  true_state?: Record<string, number>
}

export interface ExpectedState {
  rpm: number
  cht: number
  egt: number
  oil_pressure: number
  oil_temp: number
  fuel_flow: number
  vibration: number
  battery_voltage: number
  manifold_pressure?: number
  air_mass_flow?: number
  torque_nm?: number
  power_kw?: number
  propeller_load?: number
}

export interface ResidualEntry {
  actual: number
  expected: number
  residual: number
  residual_pct: number
}

export interface AnomalyResult {
  score: number
  level: AnomalyLevel
  timestamp: string
  contributing_parameters: string[]
}

export interface DiagnosisResult {
  probable_fault: string
  confidence: number
  contributing_parameters: string[]
  affected_subsystems?: string[]
  evidence: Record<string, number>
  explanation: string
}

export interface HealthResult {
  health_index: number
  degradation_index: number
  degradation_rate_per_hour: number
  subsystem_health?: Record<string, number>
  state?: string
}

export interface RULResult {
  initial_rul_hours: number
  current_rul_hours: number
  degradation_rate_per_hour: number
  trend: string
  confidence_low_hours?: number
  confidence_high_hours?: number
  note: string
}

export interface MaintenanceAdvisory {
  level: MaintenanceLevel
  message: string
}

export interface EstimatedState {
  rpm: number
  egt: number
  cht: number
  oil_temp: number
  oil_pressure: number
  vibration: number
  fuel_flow: number
  battery_voltage: number
  manifold_pressure?: number
  air_mass_flow?: number
  torque_nm?: number
  power_kw?: number
  propeller_load?: number
  engine_efficiency?: number
  alternator_health?: number
}

export interface PipelineFrame {
  mission_id: number | null
  sequence: number
  telemetry: TelemetryPoint
  estimated?: EstimatedState
  expected: ExpectedState
  residuals: Record<string, ResidualEntry>
  anomaly: AnomalyResult
  diagnosis: DiagnosisResult
  health: HealthResult
  rul: RULResult
  maintenance: MaintenanceAdvisory
  active_faults?: Record<string, {
    target_severity: number
    current_severity: number
    progression_per_sec: number
    sensor_name?: string
  }>
  sim_time_sec?: number
  mission_elapsed_sec?: number
  mission_duration_sec?: number
}

export interface Mission {
  id: number
  name: string
  source: string
  status: string
  preset: string | null
  engine_id?: string | null
  started_at: string
  ended_at: string | null
}

export interface MissionTelemetryRow {
  sequence: number
  timestamp: string
  mode: string
  rpm: number
  cht: number
  egt: number
  oil_pressure: number
  oil_temp: number
  fuel_flow: number
  vibration: number
  battery_voltage: number
  alternator_health: number
  injection_timing: number
  throttle: number
  engine_load: number
  altitude: number
  ambient_temp: number
  engine_efficiency: number
  manifold_pressure?: number
  air_mass_flow?: number
  torque_nm?: number
  power_kw?: number
  propeller_load?: number
  airspeed?: number
  pressure_kpa?: number
  density_ratio?: number
  est_rpm?: number
  est_egt?: number
  est_cht?: number
  est_oil_pressure?: number
  est_oil_temp?: number
  est_fuel_flow?: number
  est_vibration?: number
  est_battery_voltage?: number
  expected_rpm: number
  expected_egt: number
  expected_cht: number
  expected_oil_pressure: number
  expected_oil_temp: number
  expected_fuel_flow: number
  expected_vibration: number
  expected_battery_voltage: number
  expected_manifold_pressure?: number
  expected_air_mass_flow?: number
  expected_torque_nm?: number
  expected_power_kw?: number
  expected_propeller_load?: number
  residual_rpm_pct: number
  residual_egt_pct: number
  residual_cht_pct: number
  residual_oil_pressure_pct: number
  residual_oil_temp_pct: number
  residual_fuel_flow_pct: number
  residual_vibration_pct: number
  residual_battery_voltage_pct: number
  residual_manifold_pressure_pct?: number
  residual_air_mass_flow_pct?: number
  residual_torque_nm_pct?: number
  residual_power_kw_pct?: number
  residual_propeller_load_pct?: number
  anomaly_score: number
  anomaly_level: AnomalyLevel
  diagnosis_fault: string
  diagnosis_confidence: number
  diagnosis_explanation: string
  diagnosis_affected_subsystems?: string[]
  health_index: number
  degradation_index: number
  degradation_rate_per_hour: number
  health_state?: string
  subsystem_health?: Record<string, number>
  rul_hours: number
  rul_trend?: string
  rul_confidence_low?: number
  rul_confidence_high?: number
  maintenance_level: MaintenanceLevel
  maintenance_message: string
}

export interface ValidationResult {
  precision: number
  recall: number
  false_alarm_rate: number
  detection_latency_sec: number
  f1?: number
  twin_rmse?: Record<string, number>
  confusion_matrix: {
    tp: number
    fp: number
    tn: number
    fn: number
  }
  rul_mae_hours: number
  rul_rmse_hours?: number
  notes: string
}
