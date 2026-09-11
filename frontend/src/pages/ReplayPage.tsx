import { useEffect, useMemo, useState } from 'react'
import { getMissionTelemetry, listMissions } from '../api/client'
import { LineChart } from '../components/LineChart'
import { StatusBadge } from '../components/StatusBadge'
import type { Mission, MissionTelemetryRow } from '../types'

function fmt(v: number, d = 2) {
  return Number.isFinite(v) ? v.toFixed(d) : '--'
}

export function ReplayPage() {
  const [missions, setMissions] = useState<Mission[]>([])
  const [selectedMissionId, setSelectedMissionId] = useState<number | null>(null)
  const [rows, setRows] = useState<MissionTelemetryRow[]>([])
  const [index, setIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    const load = async () => {
      const missionList = await listMissions()
      setMissions(missionList)
      if (missionList.length > 0) {
        setSelectedMissionId(missionList[0].id)
      }
    }
    void load()
  }, [])

  useEffect(() => {
    if (selectedMissionId === null) {
      return
    }
    const loadRows = async () => {
      try {
        const out = await getMissionTelemetry(selectedMissionId)
        setRows(out.rows)
        setIndex(0)
        setMsg(`Loaded ${out.rows.length} telemetry frames`)
      } catch {
        setMsg('Failed to load mission telemetry')
      }
    }
    void loadRows()
  }, [selectedMissionId])

  useEffect(() => {
    if (!playing || rows.length === 0) {
      return
    }
    const timer = window.setInterval(() => {
      setIndex((prev) => {
        const next = prev + 1
        if (next >= rows.length) {
          setPlaying(false)
          return rows.length - 1
        }
        return next
      })
    }, Math.max(80, 900 / speed))

    return () => window.clearInterval(timer)
  }, [playing, rows.length, speed])

  const row = rows[index] ?? null

  const replayRows = useMemo(() => rows.slice(0, index + 1), [rows, index])
  const x = useMemo(() => replayRows.map((r) => new Date(r.timestamp).toLocaleTimeString()), [replayRows])

  return (
    <div className="dashboard-layout">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Mission Analytics & Flight Replay</h1>
          <p className="page-subtitle">Post-flight investigation tool — scrub historical missions, analyze state estimation & failure progression</p>
        </div>
      </div>

      <div className="replay-layout">
        {/* Mission controls bar */}
        <section className="section-card">
          <div className="section-card-header">Flight Investigation Controls</div>
          <div className="section-card-body">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
              <div className="form-field">
                <label className="form-label">Recorded Mission Profile</label>
                <select
                  className="form-select"
                  value={selectedMissionId ?? ''}
                  onChange={(e) => setSelectedMissionId(Number(e.target.value))}
                  disabled={missions.length === 0}
                >
                  {missions.map((m) => (
                    <option key={m.id} value={m.id}>
                      Mission #{m.id} — {m.name} ({m.source.toUpperCase()})
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-field">
                <label className="form-label">Playback Speed</label>
                <select className="form-select" value={speed} onChange={(e) => setSpeed(Number(e.target.value))}>
                  <option value={1}>1x (Realtime)</option>
                  <option value={2}>2x Speed</option>
                  <option value={4}>4x Speed</option>
                  <option value={8}>8x Fast Forward</option>
                </select>
              </div>

              <div className="form-field" style={{ justifyContent: 'flex-end' }}>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn btn-primary" onClick={() => setPlaying((p) => !p)} style={{ flex: 1 }}>
                    {playing ? 'Pause' : 'Play Replay'}
                  </button>
                  <button className="btn" onClick={() => setIndex(0)}>
                    Reset
                  </button>
                </div>
              </div>
            </div>

            {/* Scrubber slider */}
            <div style={{ marginTop: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-muted)', marginBottom: 4 }}>
                <span>Scrub Timeline</span>
                <span className="font-mono text-orange">
                  Frame {index + 1} of {Math.max(1, rows.length)} ({row ? new Date(row.timestamp).toLocaleTimeString() : '--'})
                </span>
              </div>
              <input
                className="form-range"
                type="range"
                min={0}
                max={Math.max(0, rows.length - 1)}
                value={index}
                onChange={(e) => setIndex(Number(e.target.value))}
              />
            </div>

            {msg && <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 6 }}>{msg}</div>}
          </div>
        </section>

        {row ? (
          <>
            {/* KPI Metric Grid */}
            <div className="metric-grid">
              <div className="metric-tile">
                <div className="metric-tile-label">Flight State</div>
                <div className="metric-tile-value" style={{ fontSize: 16, color: 'var(--orange-400)' }}>{row.mode.toUpperCase()}</div>
              </div>
              <div className="metric-tile">
                <div className="metric-tile-label">Health Index</div>
                <div className="metric-tile-value" style={{ color: row.health_index > 80 ? 'var(--green-400)' : 'var(--amber-400)' }}>
                  {fmt(row.health_index, 1)}%
                </div>
              </div>
              <div className="metric-tile">
                <div className="metric-tile-label">Degradation</div>
                <div className="metric-tile-value">{fmt(row.degradation_index, 1)}%</div>
              </div>
              <div className="metric-tile">
                <div className="metric-tile-label">Remaining Useful Life</div>
                <div className="metric-tile-value" style={{ color: 'var(--blue-400)' }}>{fmt(row.rul_hours, 1)} h</div>
              </div>
              <div className="metric-tile">
                <div className="metric-tile-label">Anomaly Score</div>
                <div className="metric-tile-value" style={{ color: row.anomaly_score > 0.5 ? 'var(--red-400)' : 'var(--text-primary)' }}>
                  {fmt(row.anomaly_score, 3)}
                </div>
              </div>
              <div className="metric-tile">
                <div className="metric-tile-label">Diagnosed Fault</div>
                <div className="metric-tile-value" style={{ fontSize: 14, textTransform: 'capitalize' }}>
                  {row.diagnosis_fault.replaceAll('_', ' ')}
                </div>
              </div>
            </div>

            {/* Diagnostic Snapshot Box */}
            <section className="section-card">
              <div className="section-card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Diagnostic Snapshot</span>
                <StatusBadge level={row.anomaly_level} />
              </div>
              <div className="section-card-body">
                <p style={{ fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.5 }}>{row.diagnosis_explanation}</p>
                <div style={{ display: 'flex', gap: 16, fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>
                  <span>Confidence: <strong className="text-orange">{fmt(row.diagnosis_confidence * 100, 1)}%</strong></span>
                  <span>Maintenance Action: <strong className="text-secondary">{row.maintenance_message}</strong></span>
                </div>
              </div>
            </section>

            {/* Charts Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: 12 }}>
              <section className="section-card">
                <div className="section-card-header">EGT: Actual vs Healthy Twin</div>
                <div className="section-card-body" style={{ height: 220, padding: 8 }}>
                  <LineChart
                    title=""
                    x={x}
                    yAxisName="°C"
                    series={[
                      { name: 'Actual EGT', data: replayRows.map((r) => r.egt), color: '#f97316' },
                      { name: 'Expected EGT', data: replayRows.map((r) => r.expected_egt), color: '#38bdf8' },
                    ]}
                  />
                </div>
              </section>

              <section className="section-card">
                <div className="section-card-header">RPM: Telemetry vs Expected</div>
                <div className="section-card-body" style={{ height: 220, padding: 8 }}>
                  <LineChart
                    title=""
                    x={x}
                    yAxisName="RPM"
                    series={[
                      { name: 'Actual RPM', data: replayRows.map((r) => r.rpm), color: '#4ade80' },
                      { name: 'Expected RPM', data: replayRows.map((r) => r.expected_rpm), color: '#a855f7' },
                    ]}
                  />
                </div>
              </section>

              <section className="section-card">
                <div className="section-card-header">Health & Degradation Trends</div>
                <div className="section-card-body" style={{ height: 220, padding: 8 }}>
                  <LineChart
                    title=""
                    x={x}
                    series={[
                      { name: 'Health Index', data: replayRows.map((r) => r.health_index), color: '#60a5fa' },
                      { name: 'Degradation %', data: replayRows.map((r) => r.degradation_index), color: '#f87171' },
                    ]}
                  />
                </div>
              </section>

              <section className="section-card">
                <div className="section-card-header">RUL & Anomaly Score Progression</div>
                <div className="section-card-body" style={{ height: 220, padding: 8 }}>
                  <LineChart
                    title=""
                    x={x}
                    series={[
                      { name: 'RUL (Hours)', data: replayRows.map((r) => r.rul_hours), color: '#34d399' },
                      { name: 'Anomaly Score', data: replayRows.map((r) => r.anomaly_score), color: '#fb923c' },
                    ]}
                  />
                </div>
              </section>
            </div>
          </>
        ) : (
          <div className="section-card">
            <div className="section-card-body" style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
              No mission telemetry loaded. Select a mission above to begin replay.
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
