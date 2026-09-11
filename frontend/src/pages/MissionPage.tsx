import { useEffect, useMemo, useState } from 'react'
import { fetchFaultTypes, fetchPresets } from '../api/client'
import { useTelemetry } from '../context/TelemetryContext'

export function MissionPage() {
  const {
    running,
    current,
    startMission: startMissionAction,
    stopMission: stopMissionAction,
    applyControls,
    injectFaultAction,
    clearFaultAction,
    clearAllFaultsAction,
  } = useTelemetry()

  const [presets, setPresets] = useState<Record<string, { description: string }>>({})
  const [faultTypes, setFaultTypes] = useState<string[]>([])
  const [msg, setMsg] = useState('')

  const [missionName, setMissionName] = useState('Mission Simulator Run')
  const [preset, setPreset] = useState('normal_endurance')
  const [durationSec, setDurationSec] = useState(600)
  const [demoMode, setDemoMode] = useState(false)

  const [mode, setMode] = useState('cruise')
  const [throttle, setThrottle] = useState(0.66)
  const [engineLoad, setEngineLoad] = useState(0.58)
  const [altitude, setAltitude] = useState(3500)
  const [ambientTemp, setAmbientTemp] = useState(12)

  const [faultType, setFaultType] = useState('injector_degradation')
  const [faultSeverity, setFaultSeverity] = useState(0.5)
  const [faultProgression, setFaultProgression] = useState(0.005)
  const [sensorName, setSensorName] = useState('egt')

  const activeFaults = (running && current?.active_faults ? current.active_faults : {}) as Record<string, { current_severity: number; target_severity: number }>

  useEffect(() => {
    const load = async () => {
      const [p, faults] = await Promise.all([fetchPresets(), fetchFaultTypes()])
      setPresets(p)
      setFaultTypes(faults)
      if (faults.length > 0) {
        setFaultType(faults[0])
      }
    }
    void load()
  }, [])

  const presetOptions = useMemo(() => Object.keys(presets), [presets])

  const startMission = async () => {
    try {
      await startMissionAction({
        mission_name: missionName,
        preset,
        duration_sec: durationSec,
        demo_mode: demoMode,
      })
      setMsg('Mission started')
    } catch {
      setMsg('Failed to start mission')
    }
  }

  const stopMission = async () => {
    try {
      await stopMissionAction()
      setMsg('Mission stopped')
    } catch {
      setMsg('Failed to stop mission')
    }
  }

  const applyManualControls = async () => {
    try {
      await applyControls({
        mode,
        throttle,
        engine_load: engineLoad,
        altitude,
        ambient_temp: ambientTemp,
      })
      setMsg('Manual controls applied')
    } catch {
      setMsg('Failed to apply manual controls')
    }
  }

  const inject = async () => {
    try {
      await injectFaultAction({
        fault_type: faultType,
        severity: faultSeverity,
        progression_per_sec: faultProgression,
        sensor_name: sensorName,
      })
      setMsg(`Injected fault: ${faultType}`)
    } catch {
      setMsg('Failed to inject fault')
    }
  }

  return (
    <div className="dashboard-layout">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Mission Simulation & Fault Control</h1>
          <p className="page-subtitle">Configure flight profiles, manual inputs, and inject physical/sensor engine faults</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div className="live-indicator" style={{ background: running ? 'var(--green-900)' : 'var(--bg-card)', color: running ? 'var(--green-400)' : 'var(--text-muted)' }}>
            <span className="live-dot" style={{ background: running ? 'var(--green-400)' : 'var(--text-muted)' }} />
            {running ? 'MISSION RUNNING' : 'SYSTEM IDLE'}
          </div>
        </div>
      </div>

      <div className="mission-page-layout">
        {/* Card 1: Mission Configuration */}
        <section className="section-card">
          <div className="section-card-header">Mission Configuration</div>
          <div className="section-card-body">
            <div className="form-field">
              <label className="form-label">Mission Designation</label>
              <input className="form-input" value={missionName} onChange={(e) => setMissionName(e.target.value)} />
            </div>

            <div className="form-field">
              <label className="form-label">Flight Profile Preset</label>
              <select className="form-select" value={preset} onChange={(e) => setPreset(e.target.value)}>
                {presetOptions.map((k) => (
                  <option key={k} value={k}>
                    {k.replaceAll('_', ' ').toUpperCase()}
                  </option>
                ))}
              </select>
              {presets[preset]?.description && (
                <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{presets[preset].description}</p>
              )}
            </div>

            <div className="form-field">
              <label className="form-label">Duration (Seconds)</label>
              <input
                className="form-input"
                type="number"
                value={durationSec}
                onChange={(e) => setDurationSec(Number(e.target.value))}
                min={60}
                max={10800}
              />
            </div>

            <div className="form-field" style={{ marginTop: 4 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 12, color: 'var(--text-secondary)' }}>
                <input type="checkbox" checked={demoMode} onChange={(e) => setDemoMode(e.target.checked)} style={{ accentColor: 'var(--orange-500)' }} />
                Enable Demo Progression (Automatic Injector Degradation)
              </label>
            </div>

            <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
              <button className="btn btn-primary" onClick={startMission} style={{ flex: 1 }}>
                Start Mission
              </button>
              <button className="btn btn-danger" onClick={stopMission} style={{ flex: 1 }}>
                Stop Mission
              </button>
            </div>

            {msg && <div style={{ fontSize: 11, color: 'var(--orange-400)', marginTop: 4 }}>{msg}</div>}
          </div>
        </section>

        {/* Card 2: Manual Control Input */}
        <section className="section-card">
          <div className="section-card-header">Manual Engine Controls</div>
          <div className="section-card-body">
            <div className="form-field">
              <label className="form-label">Flight Mode</label>
              <select className="form-select" value={mode} onChange={(e) => setMode(e.target.value)}>
                {['idle', 'takeoff', 'climb', 'cruise', 'loiter', 'high_load', 'descent', 'shutdown'].map((m) => (
                  <option key={m} value={m}>
                    {m.toUpperCase()}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-field">
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <label className="form-label">Throttle Position</label>
                <span className="font-mono text-orange">{(throttle * 100).toFixed(0)}%</span>
              </div>
              <input className="form-range" type="range" min={0} max={1} step={0.01} value={throttle} onChange={(e) => setThrottle(Number(e.target.value))} />
            </div>

            <div className="form-field">
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <label className="form-label">Engine Load</label>
                <span className="font-mono text-orange">{(engineLoad * 100).toFixed(0)}%</span>
              </div>
              <input className="form-range" type="range" min={0} max={1} step={0.01} value={engineLoad} onChange={(e) => setEngineLoad(Number(e.target.value))} />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <div className="form-field">
                <label className="form-label">Altitude (m)</label>
                <input className="form-input" type="number" value={altitude} onChange={(e) => setAltitude(Number(e.target.value))} />
              </div>
              <div className="form-field">
                <label className="form-label">Ambient Temp (°C)</label>
                <input className="form-input" type="number" value={ambientTemp} onChange={(e) => setAmbientTemp(Number(e.target.value))} />
              </div>
            </div>

            <button className="btn" onClick={applyManualControls} style={{ marginTop: 8 }}>
              Apply Manual Parameters
            </button>
          </div>
        </section>

        {/* Card 3: Fault Injection Panel */}
        <section className="section-card" style={{ gridColumn: '1 / -1' }}>
          <div className="section-card-header">Fault Injection System</div>
          <div className="section-card-body">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
              <div className="form-field">
                <label className="form-label">Fault Signature</label>
                <select className="form-select" value={faultType} onChange={(e) => setFaultType(e.target.value)}>
                  {faultTypes.map((f) => (
                    <option key={f} value={f}>
                      {f.replaceAll('_', ' ').toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-field">
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <label className="form-label">Target Severity</label>
                  <span className="font-mono text-amber">{(faultSeverity * 100).toFixed(0)}%</span>
                </div>
                <input className="form-range" type="range" min={0} max={1} step={0.01} value={faultSeverity} onChange={(e) => setFaultSeverity(Number(e.target.value))} />
              </div>

              <div className="form-field">
                <label className="form-label">Progression Rate / Sec</label>
                <input
                  className="form-input"
                  type="number"
                  min={0}
                  max={0.05}
                  step={0.001}
                  value={faultProgression}
                  onChange={(e) => setFaultProgression(Number(e.target.value))}
                />
              </div>

              <div className="form-field">
                <label className="form-label">Target Sensor (Drift/Bias)</label>
                <input className="form-input" value={sensorName} onChange={(e) => setSensorName(e.target.value)} />
              </div>
            </div>

            <div style={{ display: 'flex', gap: 10, marginTop: 12, flexWrap: 'wrap' }}>
              <button className="btn btn-primary" onClick={inject}>
                Inject Fault Profile
              </button>
              <button
                className="btn"
                onClick={async () => {
                  try {
                    await clearFaultAction(faultType)
                    setMsg(`Cleared fault: ${faultType}`)
                  } catch {
                    setMsg('Failed to clear fault')
                  }
                }}
              >
                Clear Selected Fault
              </button>
              <button
                className="btn btn-danger"
                onClick={async () => {
                  try {
                    await clearAllFaultsAction()
                    setMsg('Cleared all faults')
                  } catch {
                    setMsg('Failed to clear all faults')
                  }
                }}
              >
                Clear All Active Faults
              </button>
            </div>

            <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid var(--border-subtle)' }}>
              <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Active System Faults
              </h3>
              {Object.keys(activeFaults).length === 0 ? (
                <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>No active fault profiles injected</p>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 8, marginTop: 8 }}>
                  {Object.entries(activeFaults).map(([key, value]) => (
                    <div key={key} style={{ padding: '8px 10px', borderRadius: 4, background: 'var(--bg-card)', border: '1px solid var(--border-default)' }}>
                      <div className="active-fault-chip">{key.replaceAll('_', ' ').toUpperCase()}</div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-muted)', marginTop: 6 }}>
                        <span>Current Severity:</span>
                        <span className="font-mono text-amber">{(value.current_severity * 100).toFixed(1)}%</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                        <span>Target Severity:</span>
                        <span className="font-mono text-secondary">{(value.target_severity * 100).toFixed(1)}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
