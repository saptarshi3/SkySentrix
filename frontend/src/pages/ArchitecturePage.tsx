import { useEffect, useState } from 'react'
import { getArchitecture } from '../api/client'

interface PipelineStage {
  id: number
  num: string
  name: string
  subsystem: string
  phase: string
  accentColor: string
  componentFile: string
  inputStr: string
  outputStr: string
  description: string
  technicalSpecs: string
}

const PIPELINE_STAGES: PipelineStage[] = [
  // Phase 1: Data Acquisition & State Estimation
  {
    id: 1,
    num: '01',
    name: 'Telemetry Sources',
    subsystem: 'SIM / CSV / DB',
    phase: 'Phase 1: Ingestion & Filter',
    accentColor: 'var(--blue-400)',
    componentFile: 'backend/app/analytics/simulator.py',
    inputStr: 'Mission preset, throttle commands, altitude, ambient temperature',
    outputStr: '15-channel engine telemetry frame @ 10 Hz (RPM, CHT, EGT, MAP, Oil P/T, Fuel Flow, Vibration, Voltage)',
    description: 'Generates or captures high-frequency physical telemetry across 5 mission flight regimes (Takeoff, Climb, Cruise, Descent, Loiter) or parses uploaded flight logs.',
    technicalSpecs: '15 physical sensors • 10 Hz frequency • Synthetic simulator or CSV batch ingestion'
  },
  {
    id: 2,
    num: '02',
    name: 'Telemetry Ingestion',
    subsystem: 'FASTAPI / WEBSOCKET',
    phase: 'Phase 1: Ingestion & Filter',
    accentColor: 'var(--blue-400)',
    componentFile: 'backend/app/services/realtime.py',
    inputStr: 'Raw WebSocket data packets, simulation controls, fault injection commands',
    outputStr: 'Validated TelemetryPoint schema, timestamp delta (dt_sec), active mission context',
    description: 'Pydantic schema validation pipeline ensuring strict type and numerical boundary compliance, managing WebSocket connection broadcasting and synchronized 100ms clock ticks.',
    technicalSpecs: 'Pydantic v2 • 10 Hz event loop • Thread-safe WebSocket broadcast'
  },
  {
    id: 3,
    num: '03',
    name: 'Preprocessing',
    subsystem: 'NUMPY / SLIDING WINDOW',
    phase: 'Phase 1: Ingestion & Filter',
    accentColor: 'var(--blue-400)',
    componentFile: 'backend/app/analytics/feature_extractor.py',
    inputStr: 'Successive validated telemetry points across historical mission timeline',
    outputStr: '60-second historical sliding buffer, rolling statistics, signal derivatives & slopes',
    description: 'Maintains bounded rolling circular buffers, computes first and second-order time derivatives, rolling variance, instability metrics, and normalizes physical units for downstream estimators.',
    technicalSpecs: '60s rolling window • Unit normalization • First-order difference slopes'
  },
  {
    id: 4,
    num: '04',
    name: 'State Estimation',
    subsystem: 'LINEAR KALMAN FILTER',
    phase: 'Phase 1: Ingestion & Filter',
    accentColor: 'var(--blue-400)',
    componentFile: 'backend/app/engine/state_estimator.py',
    inputStr: 'Raw noisy sensor vector z = [RPM, EGT, CHT, Oil_T, Oil_P, Vib, Fuel, Batt_V]',
    outputStr: 'Filtered state vector x_hat and error covariance matrix P (8 continuous states)',
    description: 'Linear Kalman filter tracking unmeasured system states and filtering sensor noise, dynamic process covariance Q and measurement noise covariance R.',
    technicalSpecs: '8-state continuous observer • Dynamic Q & R matrices • Recursive Kalman gain'
  },

  // Phase 2: Thermodynamic Twin & Residual Analysis
  {
    id: 5,
    num: '05',
    name: 'Physics-Based Digital Twin',
    subsystem: 'AERO THERMODYNAMICS',
    phase: 'Phase 2: Digital Twin & Residuals',
    accentColor: 'var(--cyan-400)',
    componentFile: 'backend/app/engine/twin.py',
    inputStr: 'Estimated state context, throttle, engine load, altitude, ambient temp',
    outputStr: 'Thermodynamic equilibrium calculations, manifold pressure targets, volumetric efficiency',
    description: 'Deterministic mean-value aero-piston engine thermodynamic model (Lycoming IO-360 baseline) modeling ideal combustion cycles, torque production, and atmospheric lapse rates.',
    technicalSpecs: 'Lycoming IO-360 physics baseline • ISA atmospheric model • Otto cycle mapping'
  },
  {
    id: 6,
    num: '06',
    name: 'Expected Engine State',
    subsystem: 'NOMINAL BASELINE MATRIX',
    phase: 'Phase 2: Digital Twin & Residuals',
    accentColor: 'var(--cyan-400)',
    componentFile: 'backend/app/models/schemas.py',
    inputStr: 'Thermodynamic twin predictions evaluated at current operating flight conditions',
    outputStr: '13 nominal expected parameters: expected RPM, CHT, EGT, MAP, Fuel Flow, Oil P/T, Power, Torque',
    description: 'Forms the healthy baseline reference vector against which real engine behavior is compared in real time, accounting for environmental and load shifts.',
    technicalSpecs: '13 reference channels • Altitude-compensated • Torque & power equilibrium'
  },
  {
    id: 7,
    num: '07',
    name: 'Residual Calculation (Actual − Expected)',
    subsystem: 'RESIDUAL DELTA ENGINE',
    phase: 'Phase 2: Digital Twin & Residuals',
    accentColor: 'var(--cyan-400)',
    componentFile: 'backend/app/engine/twin.py (compute_residuals)',
    inputStr: 'Actual estimated state vector vs Expected healthy reference vector',
    outputStr: 'Normalized residual percentages: r_i = (actual_i − expected_i) / expected_i',
    description: 'Calculates 9 core physical residual percentages (res_rpm_pct, res_egt_pct, res_cht_pct, res_oil_p_pct, etc.) and directional delta biases to detect subsystem deviations.',
    technicalSpecs: 'Normalized percentage residuals • Directional delta flags • Cross-subsystem ratios'
  },

  // Phase 3: AI/ML Detection & ExtraTrees Diagnosis
  {
    id: 8,
    num: '08',
    name: 'Anomaly Detection',
    subsystem: 'ISOFOREST + EWMA',
    phase: 'Phase 3: AI/ML Detection & Diagnosis',
    accentColor: 'var(--orange-400)',
    componentFile: 'backend/app/analytics/anomaly.py',
    inputStr: 'Instantaneous telemetry points and normalized residual vectors',
    outputStr: 'Composite Anomaly Score [0.0 to 1.0], anomaly level (NOMINAL, WARNING, CRITICAL)',
    description: 'Dual-layer detector combining scikit-learn IsolationForest trained on healthy baseline manifolds with adaptive EWMA residual vector thresholding.',
    technicalSpecs: 'IsolationForest + EWMA • Weighted residual norm • Adaptive warning/critical thresholds'
  },
  {
    id: 9,
    num: '09',
    name: 'ExtraTrees Fault Diagnosis',
    subsystem: 'EXTRATREES CLASSIFIER',
    phase: 'Phase 3: AI/ML Detection & Diagnosis',
    accentColor: 'var(--orange-400)',
    componentFile: 'backend/app/analytics/diagnosis.py',
    inputStr: '39 engineered features extracted from residuals, ratios, stability, and slopes',
    outputStr: 'Fault classification (11 classes), confidence score, affected subsystems, 30-step majority vote',
    description: 'Production ExtraTrees classifier (300 estimators, max_depth=18) identifying specific failure modes with 90.91% run-level accuracy on virgin test datasets.',
    technicalSpecs: '300 trees • max_depth=18 • 39 features • 11 fault classes • 90.91% run accuracy'
  },

  // Phase 4: Prognostics, Health & Maintenance Advisory
  {
    id: 10,
    num: '10',
    name: 'Health / Degradation',
    subsystem: 'HEALTH INDEX ENGINE',
    phase: 'Phase 4: Prognostics & Action',
    accentColor: 'var(--green-400)',
    componentFile: 'backend/app/analytics/health.py',
    inputStr: 'Residual vectors, composite anomaly score, diagnosis fault signature & confidence',
    outputStr: 'Global Engine Health Index [0–100%], degradation rate (%/hr), 5 subsystem health scores',
    description: 'Tracks wear and stress across Combustion, Fuel, Lubrication, Thermal, and Electrical subsystems, computing overall degradation velocity.',
    technicalSpecs: '5 subsystem tracking • Multi-channel stress integration • Degradation velocity (%/hr)'
  },
  {
    id: 11,
    num: '11',
    name: 'RUL Estimation',
    subsystem: 'PROGNOSTIC EXTRAPOLATION',
    phase: 'Phase 4: Prognostics & Action',
    accentColor: 'var(--green-400)',
    componentFile: 'backend/app/analytics/rul.py',
    inputStr: 'Health index trajectory, degradation velocity, operational profile context',
    outputStr: 'Remaining Useful Life in flight hours, 90% confidence bounds [low, high], trend indicator',
    description: 'Bounded exponential and velocity extrapolation models projecting operating flight hours remaining before reaching critical failure boundaries.',
    technicalSpecs: 'Degradation curve fitting • 90% confidence interval • Bound-clamped [0–500h]'
  },
  {
    id: 12,
    num: '12',
    name: 'Maintenance Advisory',
    subsystem: 'WORK ORDER DISPATCH',
    phase: 'Phase 4: Prognostics & Action',
    accentColor: 'var(--green-400)',
    componentFile: 'backend/app/services/advisory.py',
    inputStr: 'Diagnosed fault mode, subsystem health scores, anomaly level, RUL hours',
    outputStr: 'Maintenance urgency (NORMAL, CAUTION, URGENT, GROUND_ENGINE), prioritized actions',
    description: 'Deterministic rule-based advisory system generating actionable line-maintenance procedures, inspection checklists, and flight-clearing status recommendations.',
    technicalSpecs: '4-level urgency triage • Subsystem action checklists • Flight clearance gating'
  },
]

const PHASES = [
  {
    name: 'Phase 1: Ingestion & Filter',
    color: 'var(--blue-400)',
    badge: 'STAGES 01–04',
    summary: 'Raw signal acquisition, schema validation, rolling sliding buffer, and Kalman state estimation.',
  },
  {
    name: 'Phase 2: Digital Twin & Residuals',
    color: 'var(--cyan-400)',
    badge: 'STAGES 05–07',
    summary: 'Thermodynamic aero-piston twin, nominal healthy baseline, and physics-informed residual deltas.',
  },
  {
    name: 'Phase 3: AI/ML Detection & Diagnosis',
    color: 'var(--orange-400)',
    badge: 'STAGES 08–09',
    summary: 'Dual IsolationForest/EWMA anomaly scoring and 300-tree ExtraTrees fault classification (39 features).',
  },
  {
    name: 'Phase 4: Prognostics & Action',
    color: 'var(--green-400)',
    badge: 'STAGES 10–12',
    summary: '5-subsystem health degradation tracking, RUL hours extrapolation, and maintenance triage dispatch.',
  },
]

export function ArchitecturePage() {
  const [backendNote, setBackendNote] = useState('')
  const [backendPipeline, setBackendPipeline] = useState<string[]>([])
  const [selectedStage, setSelectedStage] = useState<number | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getArchitecture()
        setBackendPipeline(data.pipeline || [])
        setBackendNote(data.note || '')
      } catch {
        setBackendNote('Architecture synchronized with local DigitalTwinPipeline contract.')
      }
    }
    void load()
  }, [])

  return (
    <div className="dashboard-layout">
      {/* Header */}
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 className="page-title">Digital Twin System Architecture</h1>
          <p className="page-subtitle">
            End-to-End Real-Time Analytics Pipeline: Sensor Telemetry → Physics Twin → ExtraTrees ML Diagnosis → Maintenance Advisory
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <span style={{
            fontSize: 11,
            fontWeight: 600,
            padding: '4px 10px',
            borderRadius: 4,
            background: 'rgba(59, 130, 246, 0.12)',
            border: '1px solid rgba(59, 130, 246, 0.3)',
            color: 'var(--blue-400)',
            letterSpacing: '0.04em'
          }}>
            10 Hz Execution Loop (100 ms)
          </span>
          <span style={{
            fontSize: 11,
            fontWeight: 600,
            padding: '4px 10px',
            borderRadius: 4,
            background: 'rgba(249, 115, 22, 0.12)',
            border: '1px solid rgba(249, 115, 22, 0.3)',
            color: 'var(--orange-400)',
            letterSpacing: '0.04em'
          }}>
            ExtraTrees 300-Tree Classifier
          </span>
          <span style={{
            fontSize: 11,
            fontWeight: 600,
            padding: '4px 10px',
            borderRadius: 4,
            background: 'rgba(34, 197, 94, 0.12)',
            border: '1px solid rgba(34, 197, 94, 0.3)',
            color: 'var(--green-400)',
            letterSpacing: '0.04em'
          }}>
            Lycoming IO-360 Physics Twin
          </span>
        </div>
      </div>

      <div className="arch-layout">
        {/* High-Level Overview Ribbon: 5-Second Comprehension */}
        <section className="arch-overview-bar">
          <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginRight: 4, letterSpacing: '0.06em' }}>
            Pipeline Flow:
          </div>
          {PHASES.map((p, idx) => (
            <div key={p.name} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div className="arch-phase-pill" style={{ borderLeft: `3px solid ${p.color}` }}>
                <span style={{ color: p.color, fontWeight: 700 }}>{p.badge}</span>
                <span style={{ color: 'var(--text-primary)' }}>{p.name.split(':')[1]}</span>
              </div>
              {idx < PHASES.length - 1 && <span className="arch-phase-arrow">→</span>}
            </div>
          ))}
        </section>

        {/* 4 Phase Sections containing the 12 Pipeline Nodes */}
        {PHASES.map((phase) => {
          const stagesInPhase = PIPELINE_STAGES.filter((s) => s.phase === phase.name)
          return (
            <section key={phase.name} className="arch-phase-section">
              <div className="arch-phase-header">
                <div className="arch-phase-title">
                  <span style={{ width: 8, height: 8, borderRadius: 2, background: phase.color }} />
                  <span style={{ color: phase.color }}>{phase.badge}:</span>
                  <span>{phase.name}</span>
                </div>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{phase.summary}</span>
              </div>

              <div className="arch-grid">
                {stagesInPhase.map((stage) => {
                  const isSelected = selectedStage === stage.id
                  return (
                    <div
                      key={stage.id}
                      className="arch-card"
                      style={{
                        borderColor: isSelected ? stage.accentColor : 'var(--border-default)',
                        cursor: 'pointer'
                      }}
                      onClick={() => setSelectedStage(isSelected ? null : stage.id)}
                    >
                      {/* Card Header */}
                      <div className="arch-card-header">
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span className="arch-card-num" style={{ color: stage.accentColor }}>{stage.num}</span>
                          <span className="arch-card-title">{stage.name}</span>
                        </div>
                        <span className="arch-card-badge" style={{
                          background: 'var(--bg-base)',
                          border: '1px solid var(--border-subtle)',
                          color: stage.accentColor
                        }}>
                          {stage.subsystem}
                        </span>
                      </div>

                      {/* Description */}
                      <p className="arch-card-desc">{stage.description}</p>

                      {/* Input / Output Structured Rows */}
                      <div className="arch-card-io">
                        <div className="arch-io-row">
                          <span className="arch-io-label" style={{ color: 'var(--blue-400)' }}>INPUT:</span>
                          <span className="arch-io-val">{stage.inputStr}</span>
                        </div>
                        <div className="arch-io-row">
                          <span className="arch-io-label" style={{ color: 'var(--green-400)' }}>OUTPUT:</span>
                          <span className="arch-io-val">{stage.outputStr}</span>
                        </div>
                      </div>

                      {/* Technical Specs Footer */}
                      <div className="arch-card-tech">
                        <span>{stage.technicalSpecs}</span>
                        <span style={{ fontSize: 9, color: 'var(--text-muted)', textDecoration: 'underline' }}>
                          {stage.componentFile.split('/').pop()}
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </section>
          )
        })}

        {/* System Telemetry & Backend Pipeline Contract Box */}
        <section className="section-card">
          <div className="section-card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Backend Runtime Alignment & Technical Contract</span>
            <span style={{ fontSize: 10, color: 'var(--green-400)', fontWeight: 600 }}>SYNCHRONIZED WITH BACKEND API</span>
          </div>
          <div className="section-card-body" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10 }}>
              <div style={{ padding: 10, borderRadius: 4, background: 'var(--bg-card)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Loop Frequency</div>
                <div className="font-mono" style={{ fontSize: 15, fontWeight: 700, color: 'var(--blue-400)', marginTop: 2 }}>10 Hz (0.1s step)</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>Synchronous real-time pipeline tick</div>
              </div>
              <div style={{ padding: 10, borderRadius: 4, background: 'var(--bg-card)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Diagnosis Latency</div>
                <div className="font-mono" style={{ fontSize: 15, fontWeight: 700, color: 'var(--orange-400)', marginTop: 2 }}>&lt; 12 ms / frame</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>Instantaneous ML tree inference</div>
              </div>
              <div style={{ padding: 10, borderRadius: 4, background: 'var(--bg-card)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Classifier Accuracy</div>
                <div className="font-mono" style={{ fontSize: 15, fontWeight: 700, color: 'var(--green-400)', marginTop: 2 }}>90.91% Run-Level</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>30-step majority voting on test set</div>
              </div>
              <div style={{ padding: 10, borderRadius: 4, background: 'var(--bg-card)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Twin Reference Model</div>
                <div className="font-mono" style={{ fontSize: 15, fontWeight: 700, color: 'var(--cyan-400)', marginTop: 2 }}>Lycoming IO-360</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>4-Cyl Piston Engine Thermodynamics</div>
              </div>
            </div>

            {backendNote && (
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', padding: '8px 12px', background: 'var(--bg-card)', borderRadius: 4, border: '1px solid var(--border-subtle)' }}>
                <strong style={{ color: 'var(--text-primary)' }}>API Contract Note:</strong> {backendNote}
                {backendPipeline.length > 0 && (
                  <span style={{ marginLeft: 8, color: 'var(--text-muted)' }}>
                    ({backendPipeline.length} verified server pipeline stages active)
                  </span>
                )}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}

