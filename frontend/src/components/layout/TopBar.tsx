import { useEffect, useState } from 'react'
import { stopSimulation, startDemoScenario } from '../../api/client'

import type { ConnectionStatus } from '../../context/TelemetryContext'

interface TopBarProps {
  running: boolean
  connected: boolean
  connectionStatus?: ConnectionStatus
  missionProfile?: string
  onStarted?: () => void
  onStopped?: () => void
}

export function TopBar({ running, connected, connectionStatus = 'connected', missionProfile = 'Normal Endurance', onStarted, onStopped }: TopBarProps) {
  const [time, setTime] = useState(new Date())
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  const handleStart = async () => {
    setLoading(true)
    try {
      await startDemoScenario()
      onStarted?.()
    } catch {}
    setLoading(false)
  }

  const handleStop = async () => {
    setLoading(true)
    try {
      await stopSimulation()
      onStopped?.()
    } catch {}
    setLoading(false)
  }

  const dateStr = time.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
  const timeStr = time.toLocaleTimeString('en-GB', { hour12: false })

  return (
    <header className="topbar">
      {/* Logo */}
      <div className="topbar-logo">
        <div style={{
          width: 28, height: 28, borderRadius: 6,
          background: 'linear-gradient(135deg, #ea6a0a, #f97316)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0
        }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L4 7v10l8 5 8-5V7L12 2z" fill="white" opacity="0.9"/>
            <path d="M12 2l8 5-8 5-8-5 8-5z" fill="white"/>
          </svg>
        </div>
        <div className="topbar-brand">
          <div className="topbar-brand-name">SkySentrix</div>
          <div className="topbar-brand-sub">Aerospace Digital Twin</div>
        </div>
      </div>

      {/* Tagline */}
      <div className="topbar-tagline" style={{ flexShrink: 0 }}>
        Predict<span>•</span>Prevent<span>•</span>Keep You Flying
      </div>

      <div style={{ flex: 1 }} />

      {/* Live indicator */}
      {connected ? (
        running ? (
          <div className="live-indicator">
            <div className="live-dot" />
            LIVE
          </div>
        ) : (
          <div
            className="live-indicator"
            style={{
              background: 'rgba(56, 189, 248, 0.12)',
              color: 'var(--blue-400)',
              borderColor: 'rgba(56, 189, 248, 0.3)',
            }}
          >
            <div className="live-dot" style={{ background: 'var(--blue-400)', boxShadow: 'none' }} />
            STANDBY
          </div>
        )
      ) : connectionStatus === 'reconnecting' ? (
        <div className="disconnected-indicator" style={{ color: 'var(--amber-400)', borderColor: 'rgba(245, 158, 11, 0.3)' }}>
          <span className="live-dot" style={{ background: 'var(--amber-400)', width: 6, height: 6, borderRadius: '50%', display: 'inline-block' }} />
          RECONNECTING
        </div>
      ) : connectionStatus === 'connecting' ? (
        <div className="disconnected-indicator" style={{ color: 'var(--amber-400)', borderColor: 'rgba(245, 158, 11, 0.3)' }}>
          <span className="live-dot" style={{ background: 'var(--amber-400)', width: 6, height: 6, borderRadius: '50%', display: 'inline-block' }} />
          CONNECTING
        </div>
      ) : (
        <div className="disconnected-indicator">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
          OFFLINE
        </div>
      )}

      {/* Date/time */}
      <div className="topbar-datetime">
        <div className="topbar-date">{dateStr}</div>
        <div className="topbar-time">{timeStr}</div>
      </div>

      {/* Mission profile */}
      <div style={{
        display: 'flex', flexDirection: 'column', padding: '0 10px',
        borderLeft: '1px solid var(--border-subtle)', borderRight: '1px solid var(--border-subtle)'
      }}>
        <span style={{ fontSize: 9, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase' }}>Mission</span>
        <span style={{ fontSize: 11, color: 'var(--text-primary)', fontWeight: 600 }}>{missionProfile}</span>
      </div>

      {/* Controls */}
      {!running ? (
        <button className="topbar-btn topbar-btn-start" onClick={handleStart} disabled={loading}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
          {loading ? 'Starting...' : 'Start Demo'}
        </button>
      ) : (
        <>
          <button className="topbar-btn topbar-btn-pause">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="4" width="4" height="16"/>
              <rect x="14" y="4" width="4" height="16"/>
            </svg>
            Pause
          </button>
          <button className="topbar-btn topbar-btn-stop" onClick={handleStop} disabled={loading}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
            </svg>
            {loading ? 'Stopping...' : 'Stop'}
          </button>
        </>
      )}

      {/* User */}
      <div className="topbar-user">
        <div className="topbar-user-avatar">DU</div>
        <div className="topbar-user-info">
          <div className="topbar-user-name">Demo User</div>
          <div className="topbar-user-role">SkySentrix</div>
        </div>
      </div>
    </header>
  )
}
