import type { PipelineFrame } from '../../types'

interface KpiStripProps {
  frame: PipelineFrame | null
  running: boolean
}

function KpiCard({
  iconClass,
  icon,
  label,
  value,
  valueClass,
  sub,
}: {
  iconClass: string
  icon: React.ReactNode
  label: string
  value: string
  valueClass: string
  sub: string
}) {
  return (
    <div className="kpi-card">
      <div className={`kpi-icon ${iconClass}`}>{icon}</div>
      <div className="kpi-content">
        <div className="kpi-label">{label}</div>
        <div className={`kpi-value ${valueClass}`}>{value}</div>
        <div className="kpi-sub">{sub}</div>
      </div>
    </div>
  )
}

export function KpiStrip({ frame, running }: KpiStripProps) {
  const health = frame?.health
  const rul = frame?.rul
  const anomaly = frame?.anomaly
  const diagnosis = frame?.diagnosis

  const hi = health?.health_index ?? 100
  const state = running ? (health?.state ?? 'HEALTHY') : 'STANDBY'

  const healthValueClass = !running ? 'kpi-value-normal'
    : state === 'HEALTHY' ? 'kpi-value-healthy'
    : state === 'DEGRADING' ? 'kpi-value-normal'
    : state === 'WARNING' ? 'kpi-value-warning'
    : 'kpi-value-critical'

  const anomalyClass = !running ? 'kpi-value-normal'
    : anomaly?.level === 'NORMAL' ? 'kpi-value-normal'
    : anomaly?.level === 'WARNING' ? 'kpi-value-warning' : 'kpi-value-critical'

  const faultName = running ? (diagnosis?.probable_fault ?? 'normal') : 'normal'
  const isAnomalous = running && faultName !== 'normal' && faultName !== ''
  const faultDisplay = isAnomalous ? faultName.replaceAll('_', ' ') : 'None'
  const maintScore = !running ? 100 : hi > 90 ? 96 : hi > 80 ? 88 : hi > 70 ? 76 : 62

  return (
    <div className="kpi-strip">
      <KpiCard
        iconClass={!running ? 'kpi-icon-neutral' : healthValueClass === 'kpi-value-healthy' ? 'kpi-icon-green' : healthValueClass === 'kpi-value-warning' ? 'kpi-icon-amber' : healthValueClass === 'kpi-value-critical' ? 'kpi-icon-red' : 'kpi-icon-neutral'}
        icon={
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
            <polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
        }
        label="Engine Health"
        value={frame ? `${hi.toFixed(1)}%` : '---'}
        valueClass={healthValueClass}
        sub={state}
      />
      <KpiCard
        iconClass={running ? 'kpi-icon-orange' : 'kpi-icon-neutral'}
        icon={
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M5 12h14"/>
            <path d="M12 5l7 7-7 7"/>
          </svg>
        }
        label="RUL Estimate"
        value={running && rul ? `${rul.current_rul_hours.toFixed(0)} h` : '---'}
        valueClass={running ? 'kpi-value-orange' : 'kpi-value-normal'}
        sub={running ? 'Remaining Useful Life' : 'Standby'}
      />
      <KpiCard
        iconClass={!running ? 'kpi-icon-neutral' : anomaly?.level === 'CRITICAL' ? 'kpi-icon-red' : anomaly?.level === 'WARNING' ? 'kpi-icon-amber' : 'kpi-icon-neutral'}
        icon={
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
          </svg>
        }
        label="Anomaly Score"
        value={running && anomaly ? anomaly.score.toFixed(3) : '0.000'}
        valueClass={anomalyClass}
        sub={running ? (anomaly?.level ?? 'Normal') : 'Normal'}
      />
      <KpiCard
        iconClass={isAnomalous ? 'kpi-icon-red' : 'kpi-icon-neutral'}
        icon={
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
        }
        label="Active Fault"
        value={faultDisplay}
        valueClass={isAnomalous ? 'kpi-value-warning' : 'kpi-value-normal'}
        sub={isAnomalous ? `${((diagnosis?.confidence ?? 0) * 100).toFixed(0)}% confidence` : 'No active fault'}
      />
      <KpiCard
        iconClass="kpi-icon-neutral"
        icon={
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/>
          </svg>
        }
        label="Maintenance Score"
        value={frame ? `${maintScore} / 100` : '---'}
        valueClass="kpi-value-normal"
        sub={running ? 'Excellent' : 'Standby'}
      />
      <KpiCard
        iconClass={running ? 'kpi-icon-green' : 'kpi-icon-neutral'}
        icon={
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
        }
        label="System Status"
        value={running ? 'Nominal' : 'Standby'}
        valueClass={running ? 'kpi-value-healthy' : 'kpi-value-normal'}
        sub={running ? 'All systems operational' : 'System ready • Engine idle'}
      />
    </div>
  )
}
