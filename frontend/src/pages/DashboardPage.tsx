import { useTelemetry } from '../context/TelemetryContext'
import { EngineScene } from '../components/3d/EngineScene'
import { SensorPanel } from '../components/panels/SensorPanel'
import { HealthPanel } from '../components/panels/HealthPanel'
import { KpiStrip } from '../components/ui/KpiStrip'
import { TrendCharts } from '../components/ui/TrendCharts'
import { TopBar } from '../components/layout/TopBar'

export function DashboardPage() {
  const { connected, connectionStatus, running, rawFrame, history, startMission, stopMission } = useTelemetry()

  const current = rawFrame
  const missionProfile = current?.telemetry?.mode
    ? current.telemetry.mode.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    : 'Normal Endurance'

  return (
    <div className="dashboard-layout">
      <TopBar
        running={running}
        connected={connected}
        connectionStatus={connectionStatus}
        missionProfile={missionProfile}
        onStarted={() => {
          void startMission({
            mission_name: 'Engine Run',
            preset: 'normal_endurance',
            duration_sec: 600,
            demo_mode: false,
          })
        }}
        onStopped={() => {
          void stopMission()
        }}
      />

      {/* Page header with engine identity */}
      <div className="page-header">
        <div>
          <div className="page-title">Engine Digital Twin</div>
          <div className="page-subtitle">Real-time monitoring • Predictive maintenance • Aero piston engine</div>
        </div>

        <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginLeft: 'auto' }}>
          {/* Engine identity card */}
          <div className="engine-identity">
            <div className="engine-identity-icon">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                <path d="M2 17l10 5 10-5"/>
                <path d="M2 12l10 5 10-5"/>
              </svg>
            </div>
            <div>
              <div className="engine-identity-name">AERO PISTON ENGINE</div>
              <div className="engine-identity-detail">Lycoming IO-360 (Simulated)</div>
              <div className="engine-identity-specs">
                <span className="engine-spec-chip">4 Cylinders</span>
                <span className="engine-spec-chip">Naturally Aspirated</span>
                <span className="engine-spec-chip">Avionics Integrated</span>
              </div>
            </div>
          </div>

          {/* Ambient conditions */}
          <div className="ambient-conditions">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--blue-400)" strokeWidth="1.8">
              <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
            </svg>
            <div>
              <div className="ambient-label">Ambient</div>
              <div className="ambient-value">
                {current ? `${current.telemetry.ambient_temp.toFixed(0)}°C` : '22°C'}
              </div>
            </div>
            <div className="ambient-divider" />
            <div>
              <div className="ambient-label">Altitude</div>
              <div className="ambient-value">
                {current ? `${current.telemetry.altitude.toFixed(0)} m` : '---'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* KPI Strip */}
      <KpiStrip frame={current} running={running} />

      {/* Main body */}
      <div className="dashboard-body">
        {/* Left: Sensor Panel */}
        <SensorPanel frame={current} history={history} />

        {/* Center: Engine Viewport + Charts */}
        <div className="dashboard-center">
          <div className="engine-viewport">
            <EngineScene frame={current} isConnected={connected} />
          </div>
          <TrendCharts history={history} />
        </div>

        {/* Right: Health + Insights */}
        <HealthPanel frame={current} />
      </div>
    </div>
  )
}
