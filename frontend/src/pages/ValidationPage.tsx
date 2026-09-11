import { useState } from 'react'
import { runValidation } from '../api/client'
import type { ValidationResult } from '../types'

interface ClassMetric {
  className: string
  label: string
  precision: number
  recall: number
  f1: number
  support: number
}

const VERIFIED_CLASSES: ClassMetric[] = [
  { className: 'alternator_problem', label: 'Alternator Problem', precision: 0.9932, recall: 0.9700, f1: 0.9815, support: 300 },
  { className: 'combustion_instability', label: 'Combustion Instability', precision: 0.8598, recall: 0.9200, f1: 0.8889, support: 300 },
  { className: 'excessive_vibration', label: 'Excessive Vibration', precision: 0.9130, recall: 0.9100, f1: 0.9115, support: 300 },
  { className: 'fuel_system_degradation', label: 'Fuel System Degradation', precision: 0.8576, recall: 0.9033, f1: 0.8799, support: 300 },
  { className: 'healthy', label: 'Healthy Baseline', precision: 0.9292, recall: 0.6969, f1: 0.7964, support: 960 },
  { className: 'injector_degradation', label: 'Injector Degradation', precision: 0.9582, recall: 0.9167, f1: 0.9370, support: 300 },
  { className: 'lubrication_problem', label: 'Lubrication Problem', precision: 0.9552, recall: 0.9233, f1: 0.9390, support: 300 },
  { className: 'misfire', label: 'Cylinder Misfire', precision: 0.9656, recall: 0.8433, f1: 0.9004, support: 300 },
  { className: 'overheating', label: 'Thermal Overheating', precision: 0.9793, recall: 0.9467, f1: 0.9627, support: 300 },
  { className: 'sensor_drift', label: 'Sensor Drift', precision: 0.4170, recall: 0.9133, f1: 0.5726, support: 300 },
  { className: 'sensor_failure', label: 'Sensor Failure / Flatline', precision: 0.8933, recall: 0.6700, f1: 0.7657, support: 300 },
]

function pct(v: number) {
  return `${(v * 100).toFixed(2)}%`
}

export function ValidationPage() {
  const [result, setResult] = useState<ValidationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState('')

  const runLegacyStressTest = async () => {
    setLoading(true)
    setMsg('Executing legacy synthetic trajectory stress test...')
    try {
      const data = await runValidation()
      setResult(data)
      setMsg('Legacy synthetic stress test complete')
    } catch {
      setMsg('Legacy synthetic stress test failed to execute')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="dashboard-layout">
      {/* Header */}
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 className="page-title">Digital Twin Validation & Benchmarks</h1>
          <p className="page-subtitle">Production model verification, diagnostic accuracy, and analytical benchmark metrics</p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <span style={{
            fontSize: 11,
            fontWeight: 600,
            padding: '4px 10px',
            borderRadius: 4,
            background: 'rgba(34, 197, 94, 0.12)',
            border: '1px solid rgba(34, 197, 94, 0.3)',
            color: 'var(--green-400)',
            textTransform: 'uppercase',
            letterSpacing: '0.04em'
          }}>
            Leakage-Free Simulator Benchmark
          </span>
          <span style={{
            fontSize: 11,
            fontWeight: 600,
            padding: '4px 10px',
            borderRadius: 4,
            background: 'rgba(59, 130, 246, 0.12)',
            border: '1px solid rgba(59, 130, 246, 0.3)',
            color: 'var(--blue-400)',
            letterSpacing: '0.02em'
          }}>
            Simulation-based validation; not real-flight certification.
          </span>
        </div>
      </div>

      <div className="validation-layout">
        {/* Production ExtraTrees Model Benchmark Card */}
        <section className="section-card">
          <div className="section-card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Production Classifier — ExtraTrees Verified Benchmark</span>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 400 }}>
              GroupKFold Virgin Test Split (33 runs, 3,960 held-out samples)
            </span>
          </div>
          <div className="section-card-body" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              Model: <strong style={{ color: 'var(--text-primary)' }}>ExtraTreesClassifier (300 estimators, max_depth=18)</strong> with 39 engineered physics-informed features. Evaluated strictly on independent held-out simulation runs with zero data leakage.
            </div>

            {/* Primary Verified Metrics */}
            <div className="metric-grid">
              <div className="metric-tile" style={{ borderLeft: '3px solid var(--green-400)' }}>
                <div className="metric-tile-label">Sample Accuracy</div>
                <div className="metric-tile-value" style={{ color: 'var(--green-400)' }}>84.44%</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>Held-out frame classification</div>
              </div>

              <div className="metric-tile" style={{ borderLeft: '3px solid var(--green-400)' }}>
                <div className="metric-tile-label">Macro Precision</div>
                <div className="metric-tile-value" style={{ color: 'var(--green-400)' }}>0.8838</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>Unweighted class mean</div>
              </div>

              <div className="metric-tile" style={{ borderLeft: '3px solid var(--green-400)' }}>
                <div className="metric-tile-label">Macro Recall</div>
                <div className="metric-tile-value" style={{ color: 'var(--green-400)' }}>0.8740</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>Unweighted sensitivity</div>
              </div>

              <div className="metric-tile" style={{ borderLeft: '3px solid var(--green-400)' }}>
                <div className="metric-tile-label">Macro F1</div>
                <div className="metric-tile-value" style={{ color: 'var(--green-400)' }}>0.8669</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>Harmonic mean (macro)</div>
              </div>

              <div className="metric-tile" style={{ borderLeft: '3px solid var(--cyan-400)', minWidth: 240, gridColumn: 'span 2' }}>
                <div className="metric-tile-label">Run-Level Accuracy with 30-step majority vote</div>
                <div className="metric-tile-value" style={{ color: 'var(--cyan-400)' }}>90.91%</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>Temporal window aggregation (30 of 33 runs correct)</div>
              </div>
            </div>

            {/* Per-Class Metrics Table */}
            <div style={{ marginTop: 8 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8, letterSpacing: '0.04em' }}>
                Per-Class Performance on Virgin Test Set (N = 3,960)
              </div>
              <div style={{ overflowX: 'auto', border: '1px solid var(--border-default)', borderRadius: 4 }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, textAlign: 'left' }}>
                  <thead>
                    <tr style={{ background: 'var(--bg-card)', borderBottom: '1px solid var(--border-default)', color: 'var(--text-muted)', fontSize: 11 }}>
                      <th style={{ padding: '8px 12px' }}>Fault / Class</th>
                      <th style={{ padding: '8px 12px' }}>Precision</th>
                      <th style={{ padding: '8px 12px' }}>Recall</th>
                      <th style={{ padding: '8px 12px' }}>F1 Score</th>
                      <th style={{ padding: '8px 12px' }}>Test Samples</th>
                    </tr>
                  </thead>
                  <tbody>
                    {VERIFIED_CLASSES.map((c, idx) => (
                      <tr key={c.className} style={{
                        borderBottom: idx < VERIFIED_CLASSES.length - 1 ? '1px solid var(--border-subtle)' : 'none',
                        background: idx % 2 === 0 ? 'transparent' : 'rgba(255, 255, 255, 0.015)'
                      }}>
                        <td style={{ padding: '7px 12px', fontWeight: 500, color: 'var(--text-primary)' }}>{c.label}</td>
                        <td className="font-mono" style={{ padding: '7px 12px', color: c.precision >= 0.85 ? 'var(--green-400)' : c.precision >= 0.7 ? 'var(--amber-400)' : 'var(--orange-400)' }}>
                          {(c.precision * 100).toFixed(1)}%
                        </td>
                        <td className="font-mono" style={{ padding: '7px 12px', color: c.recall >= 0.85 ? 'var(--green-400)' : c.recall >= 0.7 ? 'var(--amber-400)' : 'var(--orange-400)' }}>
                          {(c.recall * 100).toFixed(1)}%
                        </td>
                        <td className="font-mono" style={{ padding: '7px 12px', fontWeight: 600, color: c.f1 >= 0.85 ? 'var(--green-400)' : c.f1 >= 0.7 ? 'var(--amber-400)' : 'var(--orange-400)' }}>
                          {c.f1.toFixed(3)}
                        </td>
                        <td className="font-mono" style={{ padding: '7px 12px', color: 'var(--text-muted)' }}>{c.support}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </section>

        {/* Legacy Synthetic Stress Test Controller */}
        <section className="section-card">
          <div className="section-card-header">Legacy Synthetic Stress Test Suite</div>
          <div className="section-card-body" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
            <div style={{ maxWidth: 640 }}>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                Executes on-demand analytical evaluation over transient synthetic ground-truth trajectories. This is a synthetic stress test, not production ML model validation.
              </p>
              {msg && <div style={{ fontSize: 11, color: 'var(--orange-400)', marginTop: 4 }}>{msg}</div>}
            </div>
            <button className="btn btn-secondary" onClick={runLegacyStressTest} disabled={loading}>
              {loading ? 'Running Benchmark...' : 'Legacy Synthetic Stress Test — Not Production Model Validation'}
            </button>
          </div>
        </section>

        {result && (
          <>
            {/* Metric Tiles */}
            <div className="metric-grid">
              <div className="metric-tile">
                <div className="metric-tile-label">Precision</div>
                <div className="metric-tile-value" style={{ color: 'var(--green-400)' }}>{pct(result.precision)}</div>
              </div>
              <div className="metric-tile">
                <div className="metric-tile-label">Recall</div>
                <div className="metric-tile-value" style={{ color: 'var(--green-400)' }}>{pct(result.recall)}</div>
              </div>
              <div className="metric-tile">
                <div className="metric-tile-label">False Alarm Rate</div>
                <div className="metric-tile-value" style={{ color: 'var(--amber-400)' }}>{pct(result.false_alarm_rate)}</div>
              </div>
              <div className="metric-tile">
                <div className="metric-tile-label">F1 Score</div>
                <div className="metric-tile-value" style={{ color: 'var(--orange-400)' }}>
                  {result.f1 !== undefined ? result.f1.toFixed(3) : 'N/A'}
                </div>
              </div>
              <div className="metric-tile">
                <div className="metric-tile-label">Detection Latency</div>
                <div className="metric-tile-value" style={{ fontSize: 18 }}>
                  {result.detection_latency_sec < 0 ? 'N/A' : `${result.detection_latency_sec.toFixed(1)} s`}
                </div>
              </div>
              <div className="metric-tile">
                <div className="metric-tile-label">RUL MAE</div>
                <div className="metric-tile-value" style={{ color: 'var(--blue-400)' }}>{result.rul_mae_hours.toFixed(2)} h</div>
              </div>
            </div>

            {/* Confusion Matrix */}
            <section className="section-card">
              <div className="section-card-header">Legacy Synthetic Confusion Matrix</div>
              <div className="section-card-body">
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  <div style={{ padding: 12, borderRadius: 4, background: 'var(--bg-card)', border: '1px solid var(--border-default)' }}>
                    <div style={{ fontSize: 10, color: 'var(--green-400)', fontWeight: 600 }}>TRUE POSITIVES (TP)</div>
                    <div className="font-mono" style={{ fontSize: 24, fontWeight: 700, marginTop: 4 }}>{result.confusion_matrix.tp}</div>
                  </div>
                  <div style={{ padding: 12, borderRadius: 4, background: 'var(--bg-card)', border: '1px solid var(--border-default)' }}>
                    <div style={{ fontSize: 10, color: 'var(--amber-400)', fontWeight: 600 }}>FALSE POSITIVES (FP)</div>
                    <div className="font-mono" style={{ fontSize: 24, fontWeight: 700, marginTop: 4 }}>{result.confusion_matrix.fp}</div>
                  </div>
                  <div style={{ padding: 12, borderRadius: 4, background: 'var(--bg-card)', border: '1px solid var(--border-default)' }}>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600 }}>TRUE NEGATIVES (TN)</div>
                    <div className="font-mono" style={{ fontSize: 24, fontWeight: 700, marginTop: 4 }}>{result.confusion_matrix.tn}</div>
                  </div>
                  <div style={{ padding: 12, borderRadius: 4, background: 'var(--bg-card)', border: '1px solid var(--border-default)' }}>
                    <div style={{ fontSize: 10, color: 'var(--red-400)', fontWeight: 600 }}>FALSE NEGATIVES (FN)</div>
                    <div className="font-mono" style={{ fontSize: 24, fontWeight: 700, marginTop: 4 }}>{result.confusion_matrix.fn}</div>
                  </div>
                </div>
              </div>
            </section>

            {/* Digital Twin RMSE per signal */}
            {result.twin_rmse && (
              <section className="section-card">
                <div className="section-card-header">Digital Twin State Estimation RMSE</div>
                <div className="section-card-body">
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 8 }}>
                    {Object.entries(result.twin_rmse).map(([signal, rmse]) => (
                      <div key={signal} style={{ padding: '8px 10px', borderRadius: 4, background: 'var(--bg-card)', border: '1px solid var(--border-subtle)' }}>
                        <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{signal}</div>
                        <div className="font-mono" style={{ fontSize: 15, fontWeight: 600, color: 'var(--orange-400)', marginTop: 2 }}>
                          {Number(rmse.toFixed(3))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </section>
            )}

            {result.notes && (
              <p style={{ fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic' }}>{result.notes}</p>
            )}
          </>
        )}
      </div>
    </div>
  )
}
