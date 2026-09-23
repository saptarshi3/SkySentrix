import type { PipelineFrame } from '../../types'

interface HealthPanelProps {
  frame: PipelineFrame | null
}

function HealthRing({ value }: { value: number }) {
  const r = 28
  const circumference = 2 * Math.PI * r
  const progress = (value / 100) * circumference
  const strokeColor = value >= 80 ? '#22c55e' : value >= 60 ? '#f59e0b' : '#ef4444'
  return (
    <div className="health-ring">
      <svg viewBox="0 0 72 72">
        {/* Background track */}
        <circle cx="36" cy="36" r={r} fill="none" stroke="var(--bg-card)" strokeWidth="5" />
        {/* Progress arc */}
        <circle
          cx="36" cy="36" r={r}
          fill="none"
          stroke={strokeColor}
          strokeWidth="5"
          strokeDasharray={`${progress} ${circumference}`}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 0.5s ease, stroke 0.3s ease', filter: `drop-shadow(0 0 4px ${strokeColor}60)` }}
        />
      </svg>
      <div className="health-ring-text">
        <div className="health-ring-value" style={{ color: strokeColor }}>
          {value.toFixed(1)}
        </div>
        <div className="health-ring-pct">%</div>
      </div>
    </div>
  )
}

function SubsystemBar({ name, value }: { name: string; value: number }) {
  const pct = Math.min(100, Math.max(0, value))
  const color = pct >= 80 ? '#22c55e' : pct >= 60 ? '#f59e0b' : '#ef4444'
  return (
    <div style={{ marginBottom: 5 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
        <span style={{ fontSize: 9.5, color: 'var(--text-muted)', fontWeight: 500, textTransform: 'capitalize' }}>{name}</span>
        <span style={{ fontSize: 9.5, fontWeight: 700, color, fontFamily: 'var(--font-mono)' }}>{pct.toFixed(0)}%</span>
      </div>
      <div style={{ height: 3, background: 'var(--bg-card)', borderRadius: 2, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 2, transition: 'width 0.4s ease' }} />
      </div>
    </div>
  )
}

/** Small chip for anomaly contributors / evidence items */
function SignalChip({ label, value, highlight }: { label: string; value?: string; highlight?: boolean }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '3px 7px', borderRadius: 4, marginBottom: 3,
      background: highlight ? 'rgba(239,68,68,0.08)' : 'rgba(255,255,255,0.04)',
      border: `1px solid ${highlight ? 'rgba(239,68,68,0.22)' : 'var(--border-subtle)'}`,
    }}>
      <span style={{
        fontSize: 9.5, color: highlight ? 'var(--red-400)' : 'var(--text-secondary)',
        fontWeight: 600, textTransform: 'capitalize',
      }}>{label.replaceAll('_', ' ')}</span>
      {value !== undefined && (
        <span style={{
          fontSize: 9, fontFamily: 'var(--font-mono)', fontWeight: 700,
          color: highlight ? 'var(--red-400)' : 'var(--text-muted)',
          marginLeft: 6, flexShrink: 0,
        }}>{value}</span>
      )}
    </div>
  )
}

export function HealthPanel({ frame }: HealthPanelProps) {
  const health = frame?.health
  const diagnosis = frame?.diagnosis
  const anomaly = frame?.anomaly
  const maintenance = frame?.maintenance
  const rul = frame?.rul

  const hi = health?.health_index ?? 100
  const state = health?.state ?? 'STANDBY'
  const stateColor = state === 'HEALTHY' ? 'var(--green-400)'
    : state === 'STANDBY' ? 'var(--blue-400)'
    : state === 'DEGRADING' ? 'var(--blue-400)'
    : state === 'WARNING' ? 'var(--amber-400)'
    : 'var(--red-400)'

  const faultName = diagnosis?.probable_fault ?? 'normal'
  const isAnomalous = faultName !== 'normal' && faultName !== ''
  const faultDisplay = faultName.replaceAll('_', ' ')

  const subsystems = health?.subsystem_health as Record<string, number> | undefined

  // Evidence entries sorted by magnitude descending
  const evidenceEntries = diagnosis?.evidence
    ? Object.entries(diagnosis.evidence)
        .sort(([, a], [, b]) => Math.abs(b) - Math.abs(a))
        .slice(0, 4)
    : []

  // Anomaly contributors
  const contributors = anomaly?.contributing_parameters?.slice(0, 4) ?? []

  // Maintenance tasks from backend-provided info + advisory level
  const tasks = [
    {
      name: 'Routine Inspection',
      due: 'Due in 48 h',
      severity: 'low',
    },
    {
      name: 'Oil System Check',
      due: 'Due in 120 h',
      severity: maintenance?.level === 'WARNING' || maintenance?.level === 'CRITICAL' ? 'medium' : 'low',
    },
    {
      name: 'Spark Plug Inspection',
      due: 'Due in 200 h',
      severity: isAnomalous ? 'medium' : 'low',
    },
  ]

  return (
    <div className="right-panel">
      <div className="right-panel-scroll">
        {/* ENGINE STATUS */}
        <div className="right-panel-section">
          <div className="panel-title-icon" style={{ marginBottom: 8 }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--orange-500)" strokeWidth="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
              <polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            <span className="panel-title">Engine Status</span>
          </div>
          <div className="health-ring-container">
            <HealthRing value={hi} />
            <div className="health-status-grid">
              <div style={{ marginBottom: 4 }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: stateColor, lineHeight: 1 }}>{state}</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>Health Index</div>
              </div>
              <div className="health-status-row">
                <span className="health-status-label">Condition</span>
                <span className={`health-status-value ${state.toLowerCase()}`}>{state}</span>
              </div>
              <div className="health-status-row">
                <span className="health-status-label">Anomaly</span>
                <span className={`health-status-value ${
                  anomaly?.level === 'NORMAL' ? 'normal'
                  : anomaly?.level === 'WARNING' ? 'warning' : 'critical'
                }`}>{anomaly?.level ?? 'NORMAL'}</span>
              </div>
              <div className="health-status-row">
                <span className="health-status-label">Fault</span>
                <span className={`health-status-value ${isAnomalous ? 'warning' : 'normal'}`}
                  style={{ textTransform: 'capitalize', fontSize: 9.5, maxWidth: 100, textAlign: 'right', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                >
                  {isAnomalous ? faultDisplay : 'None'}
                </span>
              </div>
              <div className="health-status-row">
                <span className="health-status-label">Confidence</span>
                <span className={`health-status-value ${isAnomalous ? 'warning' : 'normal'}`}>
                  {isAnomalous && diagnosis?.confidence ? `${(diagnosis.confidence * 100).toFixed(0)}%` : '—'}
                </span>
              </div>
              <div className="health-status-row">
                <span className="health-status-label">RUL</span>
                <span className="health-status-value normal" style={{ fontFamily: 'var(--font-mono)' }}>
                  {rul && state !== 'STANDBY' ? `${rul.current_rul_hours.toFixed(0)} h` : '---'}
                </span>
              </div>
            </div>
          </div>

          {/* Subsystem bars */}
          {subsystems && (
            <div style={{ marginTop: 8 }}>
              {Object.entries(subsystems).filter(([k]) => k !== 'overall').map(([k, v]) => (
                <SubsystemBar key={k} name={k} value={typeof v === 'number' ? v : 0} />
              ))}
            </div>
          )}

          {/* Change 3: Fault prediction — contributing evidence */}
          {isAnomalous && evidenceEntries.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <div style={{
                fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase',
                color: 'var(--red-400)', marginBottom: 5,
                display: 'flex', alignItems: 'center', gap: 5,
              }}>
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
                </svg>
                Contributing Evidence
              </div>
              {evidenceEntries.map(([key, val]) => (
                <SignalChip
                  key={key}
                  label={key}
                  value={typeof val === 'number' ? val.toFixed(3) : String(val)}
                  highlight={Math.abs(val as number) > 0.3}
                />
              ))}
            </div>
          )}
        </div>

        {/* AI INSIGHTS — Change 4: Expanded panel */}
        <div className="right-panel-section">
          <div className="panel-title-icon" style={{ marginBottom: 8 }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--orange-500)" strokeWidth="2">
              <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
              <circle cx="12" cy="12" r="10"/>
            </svg>
            <span className="panel-title">AI Predictive Insights</span>
          </div>

          {/* Assessment text */}
          <div style={{
            background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-subtle)',
            borderRadius: 6, padding: '8px 10px', marginBottom: 8,
          }}>
            <div style={{
              fontSize: 9, fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase',
              color: 'var(--text-muted)', marginBottom: 4,
            }}>Current Assessment</div>
            <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.55 }}>
              {diagnosis?.explanation
                ? diagnosis.explanation
                : 'Engine operating normally. All parameters within expected operating range.'}
            </div>
            {!isAnomalous && (
              <div className="ai-insight-ok" style={{ marginTop: 6 }}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                No immediate action required
              </div>
            )}
          </div>

          {/* Confidence bar (only when anomalous) */}
          {isAnomalous && diagnosis?.confidence !== undefined && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 3 }}>
                <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                  Diagnosis Confidence
                </span>
                <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--amber-400)' }}>
                  {(diagnosis.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <div style={{ height: 4, background: 'var(--bg-card)', borderRadius: 2, overflow: 'hidden' }}>
                <div style={{
                  width: `${diagnosis.confidence * 100}%`, height: '100%', borderRadius: 2, transition: 'width 0.4s ease',
                  background: diagnosis.confidence > 0.75 ? 'var(--red-500)'
                    : diagnosis.confidence > 0.5 ? 'var(--amber-500)' : 'var(--green-500)',
                }} />
              </div>
            </div>
          )}

          {/* Change 2: Anomaly Score + WHY THIS SCORE? */}
          {anomaly && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 3 }}>
                <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Anomaly Score</span>
                <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-secondary)' }}>
                  {(anomaly.score * 100).toFixed(1)}%
                </span>
              </div>
              <div style={{ height: 4, background: 'var(--bg-card)', borderRadius: 2, overflow: 'hidden', marginBottom: 6 }}>
                <div style={{
                  width: `${anomaly.score * 100}%`, height: '100%', borderRadius: 2, transition: 'width 0.4s ease',
                  background: anomaly.level === 'CRITICAL' ? 'var(--red-500)'
                    : anomaly.level === 'WARNING' ? 'var(--amber-500)' : 'var(--green-500)'
                }} />
              </div>

              {/* WHY THIS SCORE? */}
              {contributors.length > 0 && (
                <div>
                  <div style={{
                    fontSize: 9, fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase',
                    color: anomaly.level !== 'NORMAL' ? 'var(--amber-400)' : 'var(--text-muted)',
                    marginBottom: 4,
                  }}>
                    Why this score?
                  </div>
                  {contributors.map(p => (
                    <SignalChip
                      key={p}
                      label={p}
                      highlight={anomaly.level === 'CRITICAL'}
                    />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Subsystem key signals (from subsystem_health when running) */}
          {subsystems && state !== 'STANDBY' && (
            <div style={{ marginBottom: 8 }}>
              <div style={{
                fontSize: 9, fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase',
                color: 'var(--text-muted)', marginBottom: 4,
              }}>Key Subsystem Signals</div>
              {Object.entries(subsystems)
                .filter(([k]) => k !== 'overall')
                .map(([k, v]) => {
                  const pct = typeof v === 'number' ? v : 0
                  return (
                    <SignalChip
                      key={k}
                      label={k}
                      value={`${pct.toFixed(0)}%`}
                      highlight={pct < 60}
                    />
                  )
                })}
            </div>
          )}

          {/* Maintenance advisory */}
          {maintenance && maintenance.message && (
            <div style={{
              padding: '6px 8px', borderRadius: 5, marginBottom: 8,
              background: maintenance.level === 'CRITICAL' ? 'rgba(239,68,68,0.08)'
                : maintenance.level === 'WARNING' ? 'rgba(245,158,11,0.08)' : 'rgba(34,197,94,0.06)',
              border: `1px solid ${
                maintenance.level === 'CRITICAL' ? 'rgba(239,68,68,0.2)'
                : maintenance.level === 'WARNING' ? 'rgba(245,158,11,0.2)' : 'rgba(34,197,94,0.15)'}`,
            }}>
              <div style={{
                fontSize: 9, fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase',
                color: maintenance.level === 'CRITICAL' ? 'var(--red-400)'
                  : maintenance.level === 'WARNING' ? 'var(--amber-400)' : 'var(--green-400)',
                marginBottom: 3,
              }}>Recommended Action</div>
              <div style={{ fontSize: 10, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                {maintenance.message}
              </div>
            </div>
          )}

          {/* RUL context */}
          {rul && state !== 'STANDBY' && (
            <div style={{
              padding: '6px 8px', borderRadius: 5,
              background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-subtle)',
            }}>
              <div style={{
                fontSize: 9, fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase',
                color: 'var(--blue-400)', marginBottom: 4,
              }}>RUL Context</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                <span style={{ fontSize: 9.5, color: 'var(--text-muted)' }}>Remaining Useful Life</span>
                <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-secondary)' }}>
                  {rul.current_rul_hours.toFixed(0)} h
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                <span style={{ fontSize: 9.5, color: 'var(--text-muted)' }}>Trend</span>
                <span style={{ fontSize: 9.5, fontWeight: 600, textTransform: 'capitalize',
                  color: rul.trend === 'stable' ? 'var(--green-400)' : rul.trend === 'degrading' ? 'var(--red-400)' : 'var(--amber-400)',
                }}>
                  {rul.trend}
                </span>
              </div>
              {rul.note && (
                <div style={{ fontSize: 9, color: 'var(--text-muted)', marginTop: 3, lineHeight: 1.45 }}>{rul.note}</div>
              )}
            </div>
          )}
        </div>

        {/* MAINTENANCE TASKS */}
        <div className="right-panel-section">
          <div className="panel-title-icon" style={{ marginBottom: 8 }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--orange-500)" strokeWidth="2">
              <path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/>
            </svg>
            <span className="panel-title">Maintenance Tasks</span>
            <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--orange-500)', cursor: 'pointer' }}>View All →</span>
          </div>
          {tasks.map((task, i) => (
            <div key={i} className="maintenance-task">
              <div className="task-number">{i + 1}</div>
              <div className="task-info">
                <div className="task-name">{task.name}</div>
                <div className="task-due">{task.due}</div>
              </div>
              <div className={`task-badge badge-${task.severity}`}>
                {task.severity === 'low' ? 'Low' : task.severity === 'medium' ? 'Medium' : 'High'}
              </div>
            </div>
          ))}
        </div>

        {/* DIAGNOSTIC CHAIN - only show when fault active */}
        {isAnomalous && diagnosis && (
          <div className="right-panel-section">
            <div className="panel-title-icon" style={{ marginBottom: 8 }}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--red-400)" strokeWidth="2">
                <polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              <span className="panel-title" style={{ color: 'var(--red-400)' }}>Active Diagnosis</span>
            </div>
            <div className="diagnostic-chain">
              {diagnosis.contributing_parameters?.slice(0, 2).map((param, i) => (
                <div key={i} className="diag-step">
                  <div className="diag-step-line">
                    <div className="diag-dot" />
                    {i < 1 && <div className="diag-connector" />}
                  </div>
                  <div className="diag-content">
                    <div className="diag-step-label">Parameter</div>
                    <div className="diag-step-value" style={{ textTransform: 'capitalize' }}>{param.replaceAll('_', ' ')}</div>
                  </div>
                </div>
              ))}
              <div className="diag-step">
                <div className="diag-step-line">
                  <div className="diag-dot" />
                </div>
                <div className="diag-content">
                  <div className="diag-step-label">Diagnosis</div>
                  <div className="diag-step-value" style={{ textTransform: 'capitalize' }}>{faultDisplay}</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Safe Skies footer branding */}
        <div style={{ marginTop: 'auto', padding: '16px 12px 12px', borderTop: '1px solid var(--border-subtle)', textAlign: 'center' }}>
          <div style={{ fontSize: 8.5, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', lineHeight: 1.6 }}>
            SAFE SKIES<br/>SMARTER ENGINES
          </div>
          <div style={{ fontSize: 8, color: 'var(--text-disabled)', marginTop: 3 }}>BUILT FOR A MORE RELIABLE TOMORROW</div>
        </div>
      </div>
    </div>
  )
}
