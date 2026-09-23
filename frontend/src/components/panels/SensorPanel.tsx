import { useMemo } from 'react'
import type { PipelineFrame } from '../../types'

interface SensorPanelProps {
  frame: PipelineFrame | null
  history: PipelineFrame[]
}

function MiniSparkline({ values, color }: { values: number[]; color: string }) {
  if (values.length < 2) return <div className="sensor-trend" />
  const w = 52, h = 22
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w
    const y = h - ((v - min) / range) * (h - 4) - 2
    return `${x},${y}`
  }).join(' ')
  return (
    <svg width={w} height={h} className="sensor-trend">
      <polyline
        points={pts}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={0.7}
      />
    </svg>
  )
}

function DeviationBadge({ pct }: { pct: number | undefined }) {
  if (pct === undefined) return null
  const abs = Math.abs(pct)
  const sign = pct > 0 ? '+' : ''
  const color = abs <= 5 ? '#22c55e' : abs <= 15 ? '#f59e0b' : '#ef4444'
  const bg = abs <= 5 ? 'rgba(34,197,94,0.1)' : abs <= 15 ? 'rgba(245,158,11,0.1)' : 'rgba(239,68,68,0.12)'
  return (
    <span style={{
      fontSize: 9, fontFamily: 'var(--font-mono)', fontWeight: 700,
      color, background: bg, border: `1px solid ${color}40`,
      borderRadius: 3, padding: '1px 4px', marginLeft: 4, flexShrink: 0,
      letterSpacing: '0.02em',
    }}>
      {sign}{pct.toFixed(1)}%
    </span>
  )
}

function SensorRow({
  icon,
  name,
  value,
  unit,
  status,
  history,
  valueColor,
  devPct,
}: {
  icon: React.ReactNode
  name: string
  value: string
  unit: string
  status: 'green' | 'amber' | 'red' | 'orange' | 'neutral'
  history: number[]
  valueColor?: string
  devPct?: number
}) {
  const dotClass = status === 'green' ? 'dot-green'
    : status === 'amber' ? 'dot-amber'
    : status === 'red' ? 'dot-red'
    : 'dot-neutral'

  const sparkColor = status === 'red' ? '#ef4444'
    : status === 'amber' ? '#f59e0b'
    : '#f97316'

  return (
    <div className="sensor-row">
      <div className="sensor-icon">{icon}</div>
      <div className="sensor-info">
        <div className="sensor-name">{name}</div>
        <div className="sensor-reading" style={{ flexWrap: 'nowrap', alignItems: 'center' }}>
          <span className={`sensor-value sensor-value-${status}`} style={valueColor ? { color: valueColor } : undefined}>
            {value}
          </span>
          <span className="sensor-unit">{unit}</span>
          <DeviationBadge pct={devPct} />
        </div>
      </div>
      <MiniSparkline values={history} color={sparkColor} />
      <div className={`sensor-status-dot ${dotClass}`} />
    </div>
  )
}

// Simple SVG icons
const icons = {
  rpm: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="9"/>
      <path d="M12 7v5l3 3"/>
    </svg>
  ),
  manifold: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/>
      <line x1="4" y1="22" x2="4" y2="15"/>
    </svg>
  ),
  fuel: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M18 18v-8l-4-4H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2z"/>
      <path d="M14 6l4 4"/>
    </svg>
  ),
  flame: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M8.5 14.5A2.5 2.5 0 0011 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 01-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 002.5 2.5z"/>
    </svg>
  ),
  temp: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"/>
    </svg>
  ),
  oil: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M7 16.3c2.2 0 4-1.83 4-4.05 0-1.16-.57-2.26-1.71-3.19S7.29 6.75 7 5.3c-.29 1.45-1.14 2.84-2.29 3.76S3 11.1 3 12.25c0 2.22 1.8 4.05 4 4.05z"/>
      <path d="M12.56 6.6A10.97 10.97 0 0 0 14 3.02c.5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a6.98 6.98 0 0 1-11.91 4.97"/>
    </svg>
  ),
  pressure: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
  ),
  vibration: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
  ),
  battery: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="1" y="6" width="18" height="12" rx="2"/>
      <line x1="23" y1="13" x2="23" y2="11"/>
      <line x1="6" y1="10" x2="6" y2="14"/>
      <line x1="10" y1="10" x2="10" y2="14"/>
    </svg>
  ),
}

function getSensorStatus(name: string, value: number): 'green' | 'amber' | 'red' | 'orange' | 'neutral' {
  switch (name) {
    case 'rpm': return value > 2600 ? 'amber' : value > 2900 ? 'red' : 'orange'
    case 'egt': return value > 750 ? 'red' : value > 650 ? 'amber' : 'orange'
    case 'cht': return value > 220 ? 'red' : value > 180 ? 'amber' : 'green'
    case 'oil_pressure': return value < 20 ? 'red' : value < 35 ? 'amber' : 'green'
    case 'oil_temp': return value > 120 ? 'red' : value > 100 ? 'amber' : 'green'
    case 'vibration': return value > 2 ? 'red' : value > 1 ? 'amber' : 'green'
    case 'battery': return value < 11.5 ? 'red' : value < 12.5 ? 'amber' : 'green'
    default: return 'neutral'
  }
}


export function SensorPanel({ frame, history }: SensorPanelProps) {
  const t = frame?.telemetry
  const residuals = frame?.residuals

  const hist = useMemo(() => ({
    rpm: history.map(f => f.telemetry.rpm),
    manifold: history.map(f => f.telemetry.manifold_pressure ?? 0),
    fuel: history.map(f => f.telemetry.fuel_flow),
    egt: history.map(f => f.telemetry.egt),
    cht: history.map(f => f.telemetry.cht),
    oil_pressure: history.map(f => f.telemetry.oil_pressure),
    oil_temp: history.map(f => f.telemetry.oil_temp),
    vibration: history.map(f => f.telemetry.vibration),
    battery: history.map(f => f.telemetry.battery_voltage),
  }), [history])

  return (
    <div className="sensor-panel">
      <div className="sensor-panel-header">
        <div className="panel-title-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
          </svg>
          <span className="panel-title">Live Sensors</span>
        </div>
        <button className="view-all-link">
          All →
        </button>
      </div>

      <div className="sensor-list">
        <SensorRow
          icon={icons.rpm}
          name="RPM"
          value={t ? t.rpm.toFixed(0) : '---'}
          unit="RPM"
          status={t ? getSensorStatus('rpm', t.rpm) : 'neutral'}
          history={hist.rpm}
          devPct={residuals?.rpm?.residual_pct}
        />
        <SensorRow
          icon={icons.manifold}
          name="Manifold Pressure"
          value={t && t.manifold_pressure !== undefined ? t.manifold_pressure.toFixed(1) : '---'}
          unit="kPa"
          status={t ? 'orange' : 'neutral'}
          history={hist.manifold}
          devPct={residuals?.manifold_pressure?.residual_pct}
        />
        <SensorRow
          icon={icons.fuel}
          name="Fuel Flow"
          value={t ? t.fuel_flow.toFixed(1) : '---'}
          unit="L/h"
          status={t ? 'orange' : 'neutral'}
          history={hist.fuel}
          devPct={residuals?.fuel_flow?.residual_pct}
        />
        <SensorRow
          icon={icons.flame}
          name="EGT (Avg)"
          value={t ? t.egt.toFixed(0) : '---'}
          unit="°C"
          status={t ? getSensorStatus('egt', t.egt) : 'neutral'}
          history={hist.egt}
          devPct={residuals?.egt?.residual_pct}
        />
        <SensorRow
          icon={icons.temp}
          name="CHT (Avg)"
          value={t ? t.cht.toFixed(0) : '---'}
          unit="°C"
          status={t ? getSensorStatus('cht', t.cht) : 'neutral'}
          history={hist.cht}
          devPct={residuals?.cht?.residual_pct}
        />
        <SensorRow
          icon={icons.pressure}
          name="Oil Pressure"
          value={t ? t.oil_pressure.toFixed(1) : '---'}
          unit="PSI"
          status={t ? getSensorStatus('oil_pressure', t.oil_pressure) : 'neutral'}
          history={hist.oil_pressure}
          devPct={residuals?.oil_pressure?.residual_pct}
        />
        <SensorRow
          icon={icons.oil}
          name="Oil Temperature"
          value={t ? t.oil_temp.toFixed(0) : '---'}
          unit="°C"
          status={t ? getSensorStatus('oil_temp', t.oil_temp) : 'neutral'}
          history={hist.oil_temp}
          devPct={residuals?.oil_temp?.residual_pct}
        />
        <SensorRow
          icon={icons.vibration}
          name="Vibration"
          value={t ? t.vibration.toFixed(2) : '---'}
          unit="mm/s"
          status={t ? getSensorStatus('vibration', t.vibration) : 'neutral'}
          history={hist.vibration}
          devPct={residuals?.vibration?.residual_pct}
        />
        <SensorRow
          icon={icons.battery}
          name="Battery Voltage"
          value={t ? t.battery_voltage.toFixed(1) : '---'}
          unit="V"
          status={t ? getSensorStatus('battery', t.battery_voltage) : 'neutral'}
          history={hist.battery}
          devPct={residuals?.battery_voltage?.residual_pct}
        />

        {/* Mode & efficiency */}
        <div style={{ padding: '8px 12px', marginTop: 4, borderTop: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
            <span style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase' }}>Mode</span>
            <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--orange-400)', textTransform: 'capitalize' }}>{t?.mode ?? '---'}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase' }}>Efficiency</span>
            <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--green-400)', fontFamily: 'var(--font-mono)' }}>
              {t ? `${(t.engine_efficiency * 100).toFixed(1)}%` : '---'}
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 4 }}>
            <span style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase' }}>Altitude</span>
            <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
              {t ? `${t.altitude.toFixed(0)} m` : '---'}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

