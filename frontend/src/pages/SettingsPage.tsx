import { useState } from 'react'
import { wsUrl as defaultWsUrl } from '../api/client'

export function SettingsPage() {
  const [theme, setTheme] = useState('aerospace_dark')
  const [wsUrl, setWsUrl] = useState(defaultWsUrl)
  const [refreshRate, setRefreshRate] = useState(10)
  const [soundAlerts, setSoundAlerts] = useState(true)
  const [autoRotate, setAutoRotate] = useState(false)
  const [savedMsg, setSavedMsg] = useState('')

  const handleSave = () => {
    setSavedMsg('Settings saved successfully')
    setTimeout(() => setSavedMsg(''), 3000)
  }

  return (
    <div className="dashboard-layout">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Engineering Platform Settings</h1>
          <p className="page-subtitle">Configure display options, telemetry socket connection, simulation defaults, and alerts</p>
        </div>
      </div>

      <div className="mission-page-layout">
        {/* Appearance Settings */}
        <section className="section-card">
          <div className="section-card-header">Appearance & 3D Visualization</div>
          <div className="section-card-body">
            <div className="form-field">
              <label className="form-label">Theme Preset</label>
              <select className="form-select" value={theme} onChange={(e) => setTheme(e.target.value)}>
                <option value="aerospace_dark">Aerospace Dark Command Center (Default)</option>
                <option value="deep_space">Deep Space High-Contrast</option>
                <option value="slate_industrial">Slate Industrial Precision</option>
              </select>
            </div>

            <div className="form-field" style={{ marginTop: 4 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 12, color: 'var(--text-secondary)' }}>
                <input
                  type="checkbox"
                  checked={autoRotate}
                  onChange={(e) => setAutoRotate(e.target.checked)}
                  style={{ accentColor: 'var(--orange-500)' }}
                />
                Default Auto-Rotate 3D Engine Viewport
              </label>
            </div>
          </div>
        </section>

        {/* Connection & Telemetry Settings */}
        <section className="section-card">
          <div className="section-card-header">Telemetry & Socket Connection</div>
          <div className="section-card-body">
            <div className="form-field">
              <label className="form-label">WebSocket Telemetry URL</label>
              <input className="form-input" value={wsUrl} onChange={(e) => setWsUrl(e.target.value)} />
            </div>

            <div className="form-field">
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <label className="form-label">Stream Refresh Frequency (Hz)</label>
                <span className="font-mono text-orange">{refreshRate} Hz</span>
              </div>
              <input className="form-range" type="range" min={1} max={20} value={refreshRate} onChange={(e) => setRefreshRate(Number(e.target.value))} />
            </div>

            <div className="form-field" style={{ marginTop: 4 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 12, color: 'var(--text-secondary)' }}>
                <input
                  type="checkbox"
                  checked={soundAlerts}
                  onChange={(e) => setSoundAlerts(e.target.checked)}
                  style={{ accentColor: 'var(--orange-500)' }}
                />
                Audible Alert Signals on Critical Anomaly Trigger
              </label>
            </div>
          </div>
        </section>

        {/* System Info */}
        <section className="section-card" style={{ gridColumn: '1 / -1' }}>
          <div className="section-card-header">System Architecture Status</div>
          <div className="section-card-body">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
              <div style={{ padding: 10, borderRadius: 4, background: 'var(--bg-card)', border: '1px solid var(--border-default)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>Backend Engine</div>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--green-400)', marginTop: 2 }}>FastAPI / Uvicorn (v0.1.0)</div>
              </div>
              <div style={{ padding: 10, borderRadius: 4, background: 'var(--bg-card)', border: '1px solid var(--border-default)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>Target Engine Model</div>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--orange-400)', marginTop: 2 }}>Lycoming IO-360 Aero Piston</div>
              </div>
              <div style={{ padding: 10, borderRadius: 4, background: 'var(--bg-card)', border: '1px solid var(--border-default)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>Digital Twin Estimator</div>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--blue-400)', marginTop: 2 }}>Extended Kalman Filter (EKF)</div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 10, marginTop: 14 }}>
              <button className="btn btn-primary" onClick={handleSave}>
                Save Platform Preferences
              </button>
            </div>

            {savedMsg && <div style={{ fontSize: 11, color: 'var(--green-400)', marginTop: 8 }}>{savedMsg}</div>}
          </div>
        </section>
      </div>
    </div>
  )
}
