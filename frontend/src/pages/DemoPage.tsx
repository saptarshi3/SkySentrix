import { useEffect, useMemo, useState } from 'react'
import { useTelemetry } from '../context/TelemetryContext'
import { EngineScene } from '../components/3d/EngineScene'
import { fetchFaultTypes } from '../api/client'

interface SignalComparisonRow {
  key: string
  label: string
  unit: string
  actual: number
  expected: number
  residualPct: number
  status: 'NORMAL' | 'WARNING' | 'CRITICAL'
}

export function DemoPage() {
  const {
    connected,
    connectionStatus,
    running,
    current,
    rawFrame,
    startDemo,
    startMission,
    stopMission,
    injectFaultAction,
    clearAllFaultsAction,
    applyControls,
  } = useTelemetry()

  const [faultTypes, setFaultTypes] = useState<string[]>([])

  // Operator interactive controls
  const [selectedFault, setSelectedFault] = useState('injector_degradation')
  const [severityPct, setSeverityPct] = useState(65)
  const [progressionRate, setProgressionRate] = useState(0.005)
  const [throttleVal, setThrottleVal] = useState(0.70)
  const [altitudeVal, setAltitudeVal] = useState(2500)
  const [ambientTempVal, setAmbientTempVal] = useState(15)
  const [statusFeedback, setStatusFeedback] = useState<string | null>(null)
  const [isInjecting, setIsInjecting] = useState(false)

  useEffect(() => {
    async function loadConfig() {
      try {
        const types = await fetchFaultTypes()
        setFaultTypes(types)
        if (types.length > 0) {
          setSelectedFault(types[0])
        }
      } catch {
        // network error
      }
    }
    void loadConfig()
  }, [])

  // Show status notification
  const notify = (msg: string) => {
    setStatusFeedback(msg)
    window.setTimeout(() => setStatusFeedback(null), 3500)
  }

  // One-Click SIH Judge Demo
  const handleStartSihDemo = async () => {
    try {
      notify('Starting SIH 2026 Autonomous Demonstration Scenario...')
      await startDemo()
      notify('SIH Demo scenario active: Engine initialized with auto-progression')
    } catch {
      notify('Failed to trigger demo scenario')
    }
  }

  // Operator Actions
  const handleStartManual = async () => {
    try {
      await startMission({
        mission_name: 'Judge Flight Evaluation',
        preset: 'normal_endurance',
        duration_sec: 600,
        demo_mode: false,
      })
      notify('Engine running in flight test mode')
    } catch {
      notify('Failed to start engine')
    }
  }

  const handleStopManual = async () => {
    try {
      await stopMission()
      notify('Engine shutdown complete')
    } catch {
      notify('Failed to stop engine')
    }
  }

  const handleInjectFault = async () => {
    try {
      setIsInjecting(true)
      await injectFaultAction({
        fault_type: selectedFault,
        severity: severityPct / 100,
        progression_per_sec: progressionRate,
      })
      notify(`Injected fault: ${selectedFault.replace(/_/g, ' ').toUpperCase()} (${severityPct}%)`)
    } catch {
      notify('Fault injection failed')
    } finally {
      setIsInjecting(false)
    }
  }

  const handleClearFaults = async () => {
    try {
      await clearAllFaultsAction()
      notify('All simulated faults cleared. Engine returned to baseline.')
    } catch {
      notify('Failed to clear faults')
    }
  }

  const handleUpdateControls = async () => {
    try {
      await applyControls({
        throttle: throttleVal,
        altitude: altitudeVal,
        ambient_temp: ambientTempVal,
      })
      notify('Operating conditions updated')
    } catch {
      notify('Failed to apply controls')
    }
  }

  // Determine stage progress on the Judge Timeline
  const timelineStages = useMemo(() => {
    const isDegraded = Boolean(running && current && (current.health_index < 95 || current.degradation_index > 5))
    const isAnomaly = Boolean(running && current && (current.anomaly_level === 'WARNING' || current.anomaly_level === 'CRITICAL'))
    const isFault = Boolean(running && current && (current.diagnosis_fault !== 'normal' && current.diagnosis_fault !== 'NO_FAULT'))
    const isHealthDrop = Boolean(running && current && current.health_index < 75)
    const isRulDrop = Boolean(running && current && current.rul_hours < 400)
    const isMaint = Boolean(running && current && current.maintenance_level !== 'NORMAL')

    return [
      {
        step: '01',
        title: 'HEALTHY BASELINE',
        desc: 'Engine operating nominal. Residuals near 0%.',
        active: Boolean(running && !isAnomaly && !isDegraded && !isFault),
        completed: Boolean(running && (isDegraded || isAnomaly || isFault)),
      },
      {
        step: '02',
        title: 'DEGRADATION ONSET',
        desc: isDegraded && current ? `Degradation index ${(current.degradation_index).toFixed(1)}%` : 'Physics drift emerging',
        active: Boolean(running && isDegraded && !isAnomaly && !isFault),
        completed: Boolean(running && (isAnomaly || isFault)),
      },
      {
        step: '03',
        title: 'ANOMALY DETECTED',
        desc: isAnomaly && current ? `Ensemble score ${(current.anomaly_score * 100).toFixed(1)}% [${current.anomaly_level}]` : 'Awaiting threshold cross',
        active: Boolean(running && isAnomaly && !isFault),
        completed: Boolean(running && isFault),
      },
      {
        step: '04',
        title: 'FAULT IDENTIFIED',
        desc: isFault && current ? `${current.diagnosis_fault.replace(/_/g, ' ').toUpperCase()} (${(current.diagnosis_confidence * 100).toFixed(0)}%)` : 'Pattern matching signature',
        active: Boolean(running && isFault && !isHealthDrop && !isRulDrop),
        completed: Boolean(running && (isHealthDrop || isRulDrop)),
      },
      {
        step: '05',
        title: 'HEALTH & RUL IMPACT',
        desc: (isHealthDrop || isRulDrop) && current ? `Health: ${current.health_index.toFixed(1)}% | RUL: ${current.rul_hours.toFixed(0)}h` : 'Extrapolating time-to-limit',
        active: Boolean(running && (isHealthDrop || isRulDrop) && !isMaint),
        completed: Boolean(running && isMaint),
      },
      {
        step: '06',
        title: 'MAINTENANCE ADVISORY',
        desc: isMaint && current ? current.maintenance_message : 'Awaiting maintenance advisory',
        active: Boolean(running && isMaint),
        completed: Boolean(running && isMaint),
      },
    ]
  }, [current, running])

  // Real-time Signal Comparison (Digital Twin vs Actual)
  const comparisonRows: SignalComparisonRow[] = useMemo(() => {
    if (!current) return []
    const evaluateStatus = (resPct: number, warnThresh: number, critThresh: number): 'NORMAL' | 'WARNING' | 'CRITICAL' => {
      const abs = Math.abs(resPct)
      if (abs >= critThresh) return 'CRITICAL'
      if (abs >= warnThresh) return 'WARNING'
      return 'NORMAL'
    }

    return [
      {
        key: 'rpm',
        label: 'RPM',
        unit: 'RPM',
        actual: current.rpm,
        expected: current.expected_rpm,
        residualPct: current.residual_rpm_pct,
        status: evaluateStatus(current.residual_rpm_pct, 4, 10),
      },
      {
        key: 'egt',
        label: 'EGT',
        unit: '°C',
        actual: current.egt,
        expected: current.expected_egt,
        residualPct: current.residual_egt_pct,
        status: evaluateStatus(current.residual_egt_pct, 5, 12),
      },
      {
        key: 'cht',
        label: 'CHT',
        unit: '°C',
        actual: current.cht,
        expected: current.expected_cht,
        residualPct: current.residual_cht_pct,
        status: evaluateStatus(current.residual_cht_pct, 4, 10),
      },
      {
        key: 'oil_pressure',
        label: 'Oil Pressure',
        unit: 'PSI',
        actual: current.oil_pressure,
        expected: current.expected_oil_pressure,
        residualPct: current.residual_oil_pressure_pct,
        status: evaluateStatus(current.residual_oil_pressure_pct, 8, 18),
      },
      {
        key: 'oil_temp',
        label: 'Oil Temp',
        unit: '°C',
        actual: current.oil_temp,
        expected: current.expected_oil_temp,
        residualPct: current.residual_oil_temp_pct,
        status: evaluateStatus(current.residual_oil_temp_pct, 6, 15),
      },
      {
        key: 'fuel_flow',
        label: 'Fuel Flow',
        unit: 'L/h',
        actual: current.fuel_flow,
        expected: current.expected_fuel_flow,
        residualPct: current.residual_fuel_flow_pct,
        status: evaluateStatus(current.residual_fuel_flow_pct, 10, 25),
      },
      {
        key: 'vibration',
        label: 'Vibration',
        unit: 'g',
        actual: current.vibration,
        expected: current.expected_vibration,
        residualPct: current.residual_vibration_pct,
        status: evaluateStatus(current.residual_vibration_pct, 15, 35),
      },
      {
        key: 'battery_voltage',
        label: 'Battery',
        unit: 'V',
        actual: current.battery_voltage,
        expected: current.expected_battery_voltage,
        residualPct: current.residual_battery_voltage_pct,
        status: evaluateStatus(current.residual_battery_voltage_pct, 5, 12),
      },
      {
        key: 'manifold_pressure',
        label: 'Manifold Pres.',
        unit: 'kPa',
        actual: current.manifold_pressure,
        expected: current.expected_manifold_pressure,
        residualPct: current.residual_manifold_pressure_pct,
        status: evaluateStatus(current.residual_manifold_pressure_pct, 6, 15),
      },
    ]
  }, [current])

  const activeFaultList = running ? Object.entries(current?.active_faults || {}) : []

  // Parse diagnosis explanation components for dedicated presentation
  const diagnosisDetails = useMemo(() => {
    const rawExp = current?.diagnosis_explanation || ''
    // Patterns from backend diagnosis.py:
    // "Model prediction: <readable/healthy> (probability: XX.X%, temporal consensus: XX%). Dominant observed indicators: ... / Operating state is nominal..."
    const probMatch = rawExp.match(/probability:\s*([0-9.]+%?)/i)
    const consensusMatch = rawExp.match(/temporal consensus:\s*([0-9.]+%?)/i)
    const indicatorsMatch = rawExp.match(/Dominant observed indicators:\s*([^.]+)/i)

    const probability = probMatch ? probMatch[1] : (current?.diagnosis_confidence ? `${(current.diagnosis_confidence * 100).toFixed(1)}%` : null)
    const consensus = consensusMatch ? consensusMatch[1] : null
    
    // Parse list of dominant indicators
    let indicators: { label: string; key: string }[] = []
    if (indicatorsMatch && indicatorsMatch[1]) {
      indicators = indicatorsMatch[1]
        .split(',')
        .map(s => s.trim())
        .filter(s => Boolean(s) && !s.includes('aggregate residual signature'))
        .map(s => ({
          key: s,
          label: s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
        }))
    } else if (current?.contributing_parameters && current.contributing_parameters.length > 0) {
      indicators = current.contributing_parameters.map(s => ({
        key: s,
        label: s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
      }))
    }

    return {
      probability,
      consensus,
      indicators,
      rawExplanation: rawExp,
    }
  }, [current?.diagnosis_explanation, current?.diagnosis_confidence, current?.contributing_parameters])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg-base)', overflow: 'hidden' }}>
      {/* 1. Aerospace Mission Control Header */}
      <header
        style={{
          height: 48,
          background: 'var(--bg-panel)',
          borderBottom: '1px solid var(--border-default)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 16px',
          flexShrink: 0,
          zIndex: 30,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div
              style={{
                width: 24,
                height: 24,
                borderRadius: 4,
                background: 'linear-gradient(135deg, var(--orange-600), var(--orange-500))',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="white">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
              </svg>
            </div>
            <div>
              <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', color: 'var(--text-primary)' }}>
                SKYSENTRIX
              </span>
              <span style={{ fontSize: 10, color: 'var(--orange-400)', fontWeight: 600, marginLeft: 6 }}>
                MISSION CONTROL • LIVE DEMO
              </span>
            </div>
          </div>

          <div style={{ width: 1, height: 20, background: 'var(--border-subtle)' }} />

          {/* Engine Status Badge */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
            <span style={{ color: 'var(--text-muted)' }}>TARGET:</span>
            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>LYCOMING IO-360 DIGITAL TWIN</span>
            <span
              style={{
                padding: '2px 8px',
                borderRadius: 10,
                fontSize: 10,
                fontWeight: 700,
                background: !running
                  ? 'rgba(100,116,139,0.15)'
                  : current?.anomaly_level === 'CRITICAL'
                  ? 'rgba(239,68,68,0.2)'
                  : current?.anomaly_level === 'WARNING'
                  ? 'rgba(245,158,11,0.2)'
                  : 'rgba(34,197,94,0.15)',
                color: !running
                  ? 'var(--text-muted)'
                  : current?.anomaly_level === 'CRITICAL'
                  ? 'var(--red-400)'
                  : current?.anomaly_level === 'WARNING'
                  ? 'var(--amber-400)'
                  : 'var(--green-400)',
                border: `1px solid ${
                  !running
                    ? 'var(--border-subtle)'
                    : current?.anomaly_level === 'CRITICAL'
                    ? 'rgba(239,68,68,0.4)'
                    : current?.anomaly_level === 'WARNING'
                    ? 'rgba(245,158,11,0.4)'
                    : 'rgba(34,197,94,0.4)'
                }`,
              }}
            >
              {!running ? 'STANDBY' : current?.anomaly_level ?? 'NOMINAL'}
            </span>
          </div>
        </div>

        {/* Header Right Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {statusFeedback && (
            <div
              style={{
                fontSize: 11,
                color: 'var(--orange-400)',
                background: 'var(--orange-glow)',
                border: '1px solid var(--orange-500)',
                padding: '3px 10px',
                borderRadius: 4,
              }}
            >
              {statusFeedback}
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
            <span style={{ color: 'var(--text-muted)' }}>MISSION TIME:</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-primary)' }}>
              {current ? `${Math.floor(current.mission_elapsed_sec / 60)}m ${Math.floor(current.mission_elapsed_sec % 60)}s` : '00:00'}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: connected && running
                  ? 'var(--green-400)'
                  : connected
                  ? 'var(--blue-400)'
                  : connectionStatus === 'reconnecting' || connectionStatus === 'connecting'
                  ? 'var(--amber-400)'
                  : 'var(--red-500)',
                boxShadow: connected && running
                  ? '0 0 8px var(--green-400)'
                  : connected
                  ? '0 0 8px var(--blue-400)'
                  : 'none',
              }}
            />
            <span
              style={{
                fontSize: 10,
                fontWeight: 700,
                letterSpacing: '0.05em',
                color: connected && running
                  ? 'var(--green-400)'
                  : connected
                  ? 'var(--blue-400)'
                  : 'var(--text-muted)',
              }}
            >
              {connected && running
                ? 'LIVE TELEMETRY'
                : connected
                ? 'SYSTEM STANDBY'
                : connectionStatus === 'reconnecting'
                ? 'RECONNECTING...'
                : connectionStatus === 'connecting'
                ? 'CONNECTING...'
                : 'OFFLINE'}
            </span>
          </div>
        </div>
      </header>

      {/* 2. Main Content Grid (Split 55% 3D Engine / 45% Command Telemetry) */}
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1.2fr 1fr', minHeight: 0, overflow: 'hidden' }}>
        {/* Left Side: Visual Digital Twin & What Is Happening Timeline */}
        <div style={{ display: 'flex', flexDirection: 'column', borderRight: '1px solid var(--border-default)', minHeight: 0 }}>
          {/* Top Half: 3D Engine Viewport */}
          <div style={{ flex: 1, position: 'relative', background: 'radial-gradient(ellipse at center, #0f1a2c 0%, #080c14 100%)', minHeight: 280 }}>
            <EngineScene frame={rawFrame} isConnected={connected} />

            {/* Subsystem Glow Tag overlay */}
            {running && current && current.diagnosis_affected_subsystems.length > 0 && current.anomaly_level !== 'NORMAL' && (
              <div
                style={{
                  position: 'absolute',
                  top: 12,
                  left: 12,
                  background: 'rgba(8, 12, 20, 0.90)',
                  border: '1px solid var(--orange-500)',
                  padding: '6px 12px',
                  borderRadius: 6,
                  backdropFilter: 'blur(8px)',
                  zIndex: 10,
                }}
              >
                <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  ACTIVE SUBSYSTEM FAULT HOTSPOT
                </div>
                <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                  {current.diagnosis_affected_subsystems.map((sub) => (
                    <span
                      key={sub}
                      style={{
                        fontSize: 10,
                        fontWeight: 700,
                        color: 'var(--orange-400)',
                        background: 'rgba(249, 115, 22, 0.15)',
                        padding: '2px 8px',
                        borderRadius: 4,
                        border: '1px solid rgba(249, 115, 22, 0.3)',
                      }}
                    >
                      {sub.toUpperCase()}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Bottom Half: "WHAT IS HAPPENING?" Diagnostic Progression Timeline */}
          <div
            style={{
              height: 195,
              background: 'var(--bg-panel)',
              borderTop: '1px solid var(--border-default)',
              display: 'flex',
              flexDirection: 'column',
              padding: '10px 16px 12px',
              flexShrink: 0,
            }}
          >
            {/* Header with Pipeline Context */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10, flexShrink: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.07em', color: 'var(--text-primary)' }}>
                  SYSTEM STATE TIMELINE • WHAT IS HAPPENING?
                </span>
                <span
                  style={{
                    fontSize: 9.5,
                    fontFamily: 'var(--font-mono)',
                    padding: '1px 6px',
                    borderRadius: 3,
                    background: running ? 'rgba(34, 197, 94, 0.12)' : 'rgba(148, 163, 184, 0.12)',
                    color: running ? 'var(--green-400)' : 'var(--text-muted)',
                    border: `1px solid ${running ? 'rgba(34, 197, 94, 0.25)' : 'var(--border-subtle)'}`,
                  }}
                >
                  {running ? 'DIAGNOSTIC PIPELINE ACTIVE' : 'ENGINE STANDBY'}
                </span>
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                SEQUENTIAL AUTONOMOUS RESPONSE CHAIN
              </div>
            </div>

            {/* Stages Grid with Visual Progression */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(6, 1fr)',
                gap: 8,
                flex: 1,
                alignItems: 'stretch',
                minHeight: 0,
              }}
            >
              {timelineStages.map((stage) => {
                const isCurrent = stage.active
                const isPassed = stage.completed && !isCurrent
                const isPending = !isCurrent && !isPassed

                const borderCol = isCurrent
                  ? 'var(--orange-500)'
                  : isPassed
                  ? 'rgba(59, 130, 246, 0.45)'
                  : 'var(--border-subtle)'

                const bgCol = isCurrent
                  ? 'linear-gradient(180deg, rgba(249, 115, 22, 0.16) 0%, rgba(15, 23, 38, 0.95) 100%)'
                  : isPassed
                  ? 'rgba(15, 23, 42, 0.65)'
                  : 'rgba(12, 18, 32, 0.45)'

                const titleCol = isCurrent
                  ? 'var(--orange-400)'
                  : isPassed
                  ? 'var(--text-primary)'
                  : 'var(--text-muted)'

                const badgeBg = isCurrent
                  ? 'var(--orange-500)'
                  : isPassed
                  ? 'var(--blue-500)'
                  : 'var(--border-default)'

                const badgeText = isCurrent
                  ? '#ffffff'
                  : isPassed
                  ? '#ffffff'
                  : 'var(--text-muted)'

                return (
                  <div
                    key={stage.step}
                    style={{
                      border: `1px solid ${borderCol}`,
                      background: bgCol,
                      borderRadius: 6,
                      padding: '9px 10px',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      transition: 'all 200ms ease',
                      position: 'relative',
                      overflow: 'hidden',
                      boxShadow: isCurrent ? '0 0 14px rgba(249, 115, 22, 0.18)' : 'none',
                    }}
                  >
                    {/* Active State Accent Bar */}
                    {isCurrent && (
                      <div
                        style={{
                          position: 'absolute',
                          top: 0,
                          left: 0,
                          right: 0,
                          height: 3,
                          background: 'var(--orange-500)',
                          boxShadow: '0 0 8px var(--orange-500)',
                        }}
                      />
                    )}

                    {/* Step badge & state status */}
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                        <span
                          style={{
                            fontSize: 9,
                            fontWeight: 700,
                            fontFamily: 'var(--font-mono)',
                            padding: '1.5px 5px',
                            borderRadius: 3,
                            background: badgeBg,
                            color: badgeText,
                            letterSpacing: '0.04em',
                          }}
                        >
                          STAGE {stage.step}
                        </span>

                        {/* State Status Indicator / Icon */}
                        {isPassed && (
                          <span
                            style={{
                              fontSize: 9.5,
                              fontWeight: 700,
                              color: 'var(--blue-400)',
                              display: 'flex',
                              alignItems: 'center',
                              gap: 2,
                            }}
                          >
                            ✓ PASS
                          </span>
                        )}
                        {isCurrent && (
                          <span
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: 4,
                              fontSize: 9,
                              fontWeight: 800,
                              color: 'var(--orange-400)',
                              letterSpacing: '0.04em',
                            }}
                          >
                            <span
                              style={{
                                width: 6,
                                height: 6,
                                borderRadius: '50%',
                                background: 'var(--orange-500)',
                                boxShadow: '0 0 6px var(--orange-500)',
                              }}
                            />
                            ACTIVE
                          </span>
                        )}
                        {isPending && (
                          <span
                            style={{
                              fontSize: 8.5,
                              color: 'var(--text-disabled)',
                              fontFamily: 'var(--font-mono)',
                            }}
                          >
                            PENDING
                          </span>
                        )}
                      </div>

                      {/* Stage Title */}
                      <div
                        style={{
                          fontSize: 11,
                          fontWeight: 700,
                          color: titleCol,
                          lineHeight: 1.25,
                          marginTop: 3,
                          letterSpacing: '0.02em',
                        }}
                      >
                        {stage.title}
                      </div>
                    </div>

                    {/* Description & Diagnostic Output */}
                    <div
                      style={{
                        fontSize: 9.5,
                        color: isCurrent ? 'var(--text-secondary)' : isPassed ? 'var(--text-secondary)' : 'var(--text-disabled)',
                        lineHeight: 1.35,
                        marginTop: 6,
                        borderTop: `1px solid ${isCurrent ? 'rgba(249, 115, 22, 0.2)' : 'var(--border-subtle)'}`,
                        paddingTop: 4,
                      }}
                    >
                      {stage.desc}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* Right Side: Command Controls & Analytical Proof */}
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0, overflowY: 'auto' }}>
          {/* Section A: Live AI Diagnosis & Diagnostic Intelligence */}
          <div style={{ padding: '12px 16px', background: 'var(--bg-panel-alt)', borderBottom: '1px solid var(--border-default)' }}>
            {/* 4 Core Diagnostic KPI Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
              {/* 1. Anomaly Score */}
              <div style={{ padding: '9px 12px', background: 'var(--bg-card)', borderRadius: 6, border: '1px solid var(--border-subtle)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 9.5, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Anomaly Score
                  </span>
                  <span
                    style={{
                      fontSize: 8.5,
                      fontWeight: 700,
                      fontFamily: 'var(--font-mono)',
                      padding: '1px 5px',
                      borderRadius: 3,
                      background:
                        (current?.anomaly_score || 0) > 0.55
                          ? 'rgba(239, 68, 68, 0.2)'
                          : (current?.anomaly_score || 0) > 0.28
                          ? 'rgba(245, 158, 11, 0.2)'
                          : 'rgba(34, 197, 94, 0.15)',
                      color:
                        (current?.anomaly_score || 0) > 0.55
                          ? 'var(--red-400)'
                          : (current?.anomaly_score || 0) > 0.28
                          ? 'var(--amber-400)'
                          : 'var(--green-400)',
                    }}
                  >
                    {current?.anomaly_level ?? 'NOMINAL'}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginTop: 4 }}>
                  <span
                    style={{
                      fontSize: 20,
                      fontWeight: 700,
                      fontFamily: 'var(--font-mono)',
                      color:
                        (current?.anomaly_score || 0) > 0.55
                          ? 'var(--red-400)'
                          : (current?.anomaly_score || 0) > 0.28
                          ? 'var(--amber-400)'
                          : 'var(--green-400)',
                    }}
                  >
                    {current ? (current.anomaly_score * 100).toFixed(1) : '0.0'}%
                  </span>
                </div>
                <div style={{ fontSize: 9.5, color: 'var(--text-muted)', marginTop: 2 }}>
                  Ensemble deviation
                </div>
              </div>

              {/* 2. Diagnosed Fault / Primary Prediction */}
              <div style={{ padding: '9px 12px', background: 'var(--bg-card)', borderRadius: 6, border: '1px solid var(--border-subtle)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 9.5, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Model Prediction
                  </span>
                  {diagnosisDetails.probability && (
                    <span style={{ fontSize: 9, fontFamily: 'var(--font-mono)', color: 'var(--orange-400)' }}>
                      p={diagnosisDetails.probability}
                    </span>
                  )}
                </div>
                <div
                  style={{
                    fontSize: 14,
                    fontWeight: 700,
                    color: current?.diagnosis_fault && current.diagnosis_fault !== 'normal' ? 'var(--orange-400)' : 'var(--green-400)',
                    marginTop: 4,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    letterSpacing: '0.02em',
                  }}
                >
                  {current?.diagnosis_fault && current.diagnosis_fault !== 'normal'
                    ? current.diagnosis_fault.replace(/_/g, ' ').toUpperCase()
                    : 'NO ACTIVE FAULT'}
                </div>
                <div style={{ fontSize: 9.5, color: 'var(--text-muted)', marginTop: 2, fontFamily: 'var(--font-mono)' }}>
                  Conf: {current ? (current.diagnosis_confidence * 100).toFixed(0) : '0'}%
                </div>
              </div>

              {/* 3. Engine Health & Degradation */}
              <div style={{ padding: '9px 12px', background: 'var(--bg-card)', borderRadius: 6, border: '1px solid var(--border-subtle)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 9.5, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Engine Health
                  </span>
                  <span style={{ fontSize: 9, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    Deg: {current ? current.degradation_index.toFixed(1) : '0.0'}%
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, marginTop: 4 }}>
                  <span
                    style={{
                      fontSize: 20,
                      fontWeight: 700,
                      fontFamily: 'var(--font-mono)',
                      color:
                        (current?.health_index || 100) < 60
                          ? 'var(--red-400)'
                          : (current?.health_index || 100) < 80
                          ? 'var(--amber-400)'
                          : 'var(--green-400)',
                    }}
                  >
                    {current ? current.health_index.toFixed(1) : '100.0'}%
                  </span>
                </div>
                <div style={{ fontSize: 9.5, color: 'var(--text-muted)', marginTop: 2 }}>
                  Operating integrity
                </div>
              </div>

              {/* 4. Estimated RUL */}
              <div style={{ padding: '9px 12px', background: 'var(--bg-card)', borderRadius: 6, border: '1px solid var(--border-subtle)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 9.5, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Estimated RUL
                  </span>
                  <span
                    style={{
                      fontSize: 8.5,
                      fontWeight: 700,
                      fontFamily: 'var(--font-mono)',
                      padding: '1px 5px',
                      borderRadius: 3,
                      background: 'rgba(96, 165, 250, 0.15)',
                      color: 'var(--blue-400)',
                    }}
                  >
                    {current?.rul_trend ?? 'STABLE'}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, marginTop: 4 }}>
                  <span style={{ fontSize: 20, fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--blue-400)' }}>
                    {current ? current.rul_hours.toFixed(0) : '480'}h
                  </span>
                </div>
                <div style={{ fontSize: 9.5, color: 'var(--text-muted)', marginTop: 2 }}>
                  Time-to-limit margin
                </div>
              </div>
            </div>

            {/* Diagnostic Reasoning & Why This Prediction Panel */}
            {current?.diagnosis_explanation && (
              <div
                style={{
                  marginTop: 10,
                  padding: '10px 14px',
                  background: 'rgba(11, 18, 32, 0.85)',
                  borderRadius: 6,
                  border: '1px solid var(--border-default)',
                  borderLeft: '3px solid var(--orange-500)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 10.5, fontWeight: 800, color: 'var(--orange-400)', letterSpacing: '0.06em' }}>
                      WHY THIS PREDICTION?
                    </span>
                    <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                      Diagnostic Evidence & Pattern Consensus
                    </span>
                  </div>

                  {/* Quantitative Consensus Indicators */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    {diagnosisDetails.probability && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                        <span style={{ fontSize: 9.5, color: 'var(--text-muted)', textTransform: 'uppercase' }}>PROBABILITY:</span>
                        <span style={{ fontSize: 11, fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--orange-400)' }}>
                          {diagnosisDetails.probability}
                        </span>
                      </div>
                    )}
                    {diagnosisDetails.consensus && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                        <span style={{ fontSize: 9.5, color: 'var(--text-muted)', textTransform: 'uppercase' }}>TEMPORAL CONSENSUS:</span>
                        <span style={{ fontSize: 11, fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--blue-400)' }}>
                          {diagnosisDetails.consensus}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Dominant Observed Indicators Chips */}
                {diagnosisDetails.indicators.length > 0 && (
                  <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                    <span style={{ fontSize: 9.5, fontWeight: 700, color: 'var(--text-muted)' }}>
                      DOMINANT OBSERVED INDICATORS:
                    </span>
                    {diagnosisDetails.indicators.map((ind) => (
                      <span
                        key={ind.key}
                        style={{
                          fontSize: 10,
                          fontWeight: 600,
                          padding: '2px 8px',
                          borderRadius: 4,
                          background: 'rgba(249, 115, 22, 0.12)',
                          color: 'var(--orange-300)',
                          border: '1px solid rgba(249, 115, 22, 0.3)',
                          fontFamily: 'var(--font-mono)',
                        }}
                      >
                        {ind.label}
                      </span>
                    ))}
                  </div>
                )}

                {/* Full Explanation Text */}
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 6, lineHeight: 1.4 }}>
                  {current.diagnosis_explanation}
                </div>
              </div>
            )}
          </div>

          {/* Section B: Operator Control Center */}
          <div style={{ padding: '12px 14px', borderBottom: '1px solid var(--border-default)', background: 'var(--bg-panel)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.06em', color: 'var(--text-secondary)' }}>
                OPERATOR SIMULATION CONSOLE
              </span>
              <div style={{ display: 'flex', gap: 6 }}>
                <button
                  onClick={handleStartSihDemo}
                  style={{
                    background: 'linear-gradient(135deg, var(--orange-600), var(--orange-500))',
                    color: 'white',
                    border: 'none',
                    padding: '4px 12px',
                    borderRadius: 4,
                    fontSize: 10.5,
                    fontWeight: 700,
                    cursor: 'pointer',
                    boxShadow: '0 2px 8px var(--orange-glow)',
                  }}
                >
                  ⚡ START SIH 2026 DEMO
                </button>
                <button
                  onClick={running ? handleStopManual : handleStartManual}
                  style={{
                    background: running ? 'rgba(239, 68, 68, 0.2)' : 'rgba(34, 197, 94, 0.2)',
                    color: running ? 'var(--red-400)' : 'var(--green-400)',
                    border: `1px solid ${running ? 'rgba(239, 68, 68, 0.4)' : 'rgba(34, 197, 94, 0.4)'}`,
                    padding: '4px 10px',
                    borderRadius: 4,
                    fontSize: 10.5,
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  {running ? 'STOP ENGINE' : 'START ENGINE'}
                </button>
                <button
                  onClick={handleClearFaults}
                  style={{
                    background: 'var(--bg-card)',
                    color: 'var(--text-secondary)',
                    border: '1px solid var(--border-subtle)',
                    padding: '4px 10px',
                    borderRadius: 4,
                    fontSize: 10.5,
                    cursor: 'pointer',
                  }}
                >
                  RESET FAULTS
                </button>
              </div>
            </div>

            {/* Interactive Fault Injection Form */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1.4fr 1fr 1fr auto',
                gap: 8,
                alignItems: 'end',
                background: 'var(--bg-card)',
                padding: 10,
                borderRadius: 6,
                border: '1px solid var(--border-subtle)',
              }}
            >
              <div>
                <label style={{ fontSize: 9.5, color: 'var(--text-muted)', display: 'block', marginBottom: 2 }}>
                  Fault Profile
                </label>
                <select
                  value={selectedFault}
                  onChange={(e) => setSelectedFault(e.target.value)}
                  style={{
                    width: '100%',
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border-default)',
                    color: 'var(--text-primary)',
                    padding: '4px 8px',
                    borderRadius: 4,
                    fontSize: 11,
                  }}
                >
                  {faultTypes.map((ft) => (
                    <option key={ft} value={ft}>
                      {ft.replace(/_/g, ' ').toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9.5, color: 'var(--text-muted)' }}>
                  <span>Severity</span>
                  <span style={{ color: 'var(--orange-400)', fontFamily: 'var(--font-mono)' }}>{severityPct}%</span>
                </div>
                <input
                  type="range"
                  min={10}
                  max={100}
                  step={5}
                  value={severityPct}
                  onChange={(e) => setSeverityPct(Number(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--orange-500)', marginTop: 4 }}
                />
              </div>

              <div>
                <label style={{ fontSize: 9.5, color: 'var(--text-muted)', display: 'block', marginBottom: 2 }}>
                  Progression / Sec
                </label>
                <input
                  type="number"
                  step={0.002}
                  min={0}
                  max={0.05}
                  value={progressionRate}
                  onChange={(e) => setProgressionRate(Number(e.target.value))}
                  style={{
                    width: '100%',
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border-default)',
                    color: 'var(--text-primary)',
                    padding: '4px 6px',
                    borderRadius: 4,
                    fontSize: 11,
                  }}
                />
              </div>

              <button
                onClick={handleInjectFault}
                disabled={isInjecting}
                style={{
                  background: 'var(--orange-500)',
                  color: 'white',
                  border: 'none',
                  padding: '6px 12px',
                  borderRadius: 4,
                  fontSize: 11,
                  fontWeight: 600,
                  cursor: isInjecting ? 'not-allowed' : 'pointer',
                  height: 28,
                }}
              >
                INJECT FAULT
              </button>
            </div>

            {/* Operating Environmental Sliders */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr) auto', gap: 10, marginTop: 8, alignItems: 'end' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9.5, color: 'var(--text-muted)' }}>
                  <span>Throttle</span>
                  <span style={{ color: 'var(--orange-400)' }}>{(throttleVal * 100).toFixed(0)}%</span>
                </div>
                <input
                  type="range"
                  min={0.1}
                  max={1.0}
                  step={0.05}
                  value={throttleVal}
                  onChange={(e) => setThrottleVal(Number(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--orange-500)' }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9.5, color: 'var(--text-muted)' }}>
                  <span>Altitude</span>
                  <span style={{ color: 'var(--text-secondary)' }}>{altitudeVal} m</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={6000}
                  step={250}
                  value={altitudeVal}
                  onChange={(e) => setAltitudeVal(Number(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--blue-400)' }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9.5, color: 'var(--text-muted)' }}>
                  <span>Ambient Temp</span>
                  <span style={{ color: 'var(--text-secondary)' }}>{ambientTempVal}°C</span>
                </div>
                <input
                  type="range"
                  min={-20}
                  max={45}
                  step={1}
                  value={ambientTempVal}
                  onChange={(e) => setAmbientTempVal(Number(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--blue-400)' }}
                />
              </div>

              <button
                onClick={handleUpdateControls}
                style={{
                  background: 'var(--bg-card)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-default)',
                  padding: '4px 10px',
                  borderRadius: 4,
                  fontSize: 10,
                  cursor: 'pointer',
                  height: 26,
                }}
              >
                APPLY CONDITIONS
              </button>
            </div>

            {/* Active Fault Status Chips */}
            {activeFaultList.length > 0 && (
              <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 9, fontWeight: 700, color: 'var(--text-muted)' }}>ACTIVE FAULTS:</span>
                {activeFaultList.map(([key, val]) => (
                  <span
                    key={key}
                    style={{
                      fontSize: 9.5,
                      fontWeight: 600,
                      padding: '2px 6px',
                      borderRadius: 3,
                      background: 'rgba(239,68,68,0.15)',
                      color: 'var(--red-400)',
                      border: '1px solid rgba(239,68,68,0.3)',
                    }}
                  >
                    {key.replace(/_/g, ' ').toUpperCase()} ({(val.current_severity * 100).toFixed(0)}%)
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Section C: Live Digital Twin vs Actual Comparison — Redesigned Panel */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: 'var(--bg-surface)', overflowY: 'auto', minHeight: 0 }}>
            {/* Panel header */}
            <div
              style={{
                padding: '10px 16px 8px',
                borderBottom: '1px solid var(--border-default)',
                background: 'var(--bg-panel)',
                flexShrink: 0,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.07em', color: 'var(--text-primary)' }}>
                  ACTUAL SENSORS vs DIGITAL TWIN EXPECTATION
                </span>
                <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  RESIDUAL Δ MATRIX
                </span>
              </div>
              {/* Column headers */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '130px 1fr 1fr 100px 80px',
                  gap: 0,
                  marginTop: 8,
                  paddingBottom: 4,
                  borderBottom: '1px solid var(--border-subtle)',
                }}
              >
                {(['PARAMETER', 'ACTUAL', 'DIGITAL TWIN', 'DEVIATION', 'STATUS'] as const).map((col, i) => (
                  <div
                    key={col}
                    style={{
                      fontSize: 9.5,
                      fontWeight: 700,
                      letterSpacing: '0.08em',
                      color: 'var(--text-muted)',
                      textAlign: i >= 3 ? 'right' : 'left',
                      paddingRight: i === 4 ? 0 : 8,
                    }}
                  >
                    {col}
                  </div>
                ))}
              </div>
            </div>

            {/* Signal rows */}
            <div style={{ flex: 1, padding: '4px 0' }}>
              {comparisonRows.length === 0 ? (
                <div
                  style={{
                    padding: '24px 16px',
                    textAlign: 'center',
                    color: 'var(--text-muted)',
                    fontSize: 12,
                    fontStyle: 'italic',
                  }}
                >
                  Awaiting telemetry — start engine to populate sensor data
                </div>
              ) : (
                comparisonRows.map((row, idx) => {
                  const isWarn = row.status === 'WARNING'
                  const isCrit = row.status === 'CRITICAL'
                  const isNorm = row.status === 'NORMAL'

                  const statusColor = isCrit
                    ? 'var(--red-400)'
                    : isWarn
                    ? 'var(--amber-400)'
                    : 'var(--green-400)'

                  const statusBg = isCrit
                    ? 'rgba(239,68,68,0.14)'
                    : isWarn
                    ? 'rgba(245,158,11,0.14)'
                    : 'rgba(74,222,128,0.1)'

                  const statusBorder = isCrit
                    ? 'rgba(239,68,68,0.35)'
                    : isWarn
                    ? 'rgba(245,158,11,0.35)'
                    : 'rgba(74,222,128,0.25)'

                  const deviationColor = isCrit
                    ? 'var(--red-400)'
                    : isWarn
                    ? 'var(--amber-400)'
                    : row.residualPct > 0
                    ? 'var(--orange-400)'
                    : row.residualPct < 0
                    ? 'var(--blue-400)'
                    : 'var(--text-muted)'

                  // bar fill: clamp abs(residualPct) to 0–50%, scale to 0–100% width
                  const barFillPct = Math.min(Math.abs(row.residualPct) / 50, 1) * 100
                  const barColor = isCrit
                    ? 'var(--red-500)'
                    : isWarn
                    ? 'var(--amber-500)'
                    : 'var(--blue-500)'

                  const rowBg = isCrit
                    ? 'rgba(239,68,68,0.05)'
                    : isWarn
                    ? 'rgba(245,158,11,0.04)'
                    : 'transparent'

                  return (
                    <div
                      key={row.key}
                      style={{
                        display: 'grid',
                        gridTemplateColumns: '130px 1fr 1fr 100px 80px',
                        alignItems: 'center',
                        gap: 0,
                        padding: '9px 16px',
                        borderBottom: idx < comparisonRows.length - 1 ? '1px solid var(--border-subtle)' : 'none',
                        background: rowBg,
                        transition: 'background 200ms ease',
                        minHeight: 52,
                      }}
                    >
                      {/* PARAMETER */}
                      <div style={{ paddingRight: 8 }}>
                        <div
                          style={{
                            fontSize: 13,
                            fontWeight: 700,
                            color: isCrit ? 'var(--red-400)' : isWarn ? 'var(--amber-400)' : 'var(--text-primary)',
                            letterSpacing: '0.01em',
                            lineHeight: 1.2,
                          }}
                        >
                          {row.label}
                        </div>
                        <div
                          style={{
                            fontSize: 10,
                            color: 'var(--text-muted)',
                            marginTop: 1,
                            fontFamily: 'var(--font-mono)',
                          }}
                        >
                          {row.unit}
                        </div>
                      </div>

                      {/* ACTUAL */}
                      <div style={{ paddingRight: 8 }}>
                        <div
                          style={{
                            fontSize: 17,
                            fontWeight: 700,
                            fontFamily: 'var(--font-mono)',
                            color: 'var(--text-primary)',
                            lineHeight: 1,
                            transition: 'color 300ms ease',
                          }}
                        >
                          {row.actual.toFixed(1)}
                        </div>
                        <div
                          style={{
                            fontSize: 9.5,
                            color: 'var(--text-muted)',
                            marginTop: 2,
                          }}
                        >
                          sensor reading
                        </div>
                      </div>

                      {/* DIGITAL TWIN */}
                      <div style={{ paddingRight: 8 }}>
                        <div
                          style={{
                            fontSize: 17,
                            fontWeight: 600,
                            fontFamily: 'var(--font-mono)',
                            color: 'var(--text-secondary)',
                            lineHeight: 1,
                            transition: 'color 300ms ease',
                          }}
                        >
                          {row.expected.toFixed(1)}
                        </div>
                        <div
                          style={{
                            fontSize: 9.5,
                            color: 'var(--text-muted)',
                            marginTop: 2,
                          }}
                        >
                          twin model
                        </div>
                      </div>

                      {/* DEVIATION */}
                      <div style={{ textAlign: 'right', paddingRight: 12 }}>
                        <div
                          style={{
                            fontSize: 15,
                            fontWeight: 700,
                            fontFamily: 'var(--font-mono)',
                            color: deviationColor,
                            lineHeight: 1,
                            transition: 'color 300ms ease',
                          }}
                        >
                          {row.residualPct >= 0 ? '+' : ''}{row.residualPct.toFixed(1)}%
                        </div>
                        {/* Micro deviation bar */}
                        <div
                          style={{
                            marginTop: 4,
                            height: 3,
                            borderRadius: 2,
                            background: 'var(--border-subtle)',
                            overflow: 'hidden',
                            position: 'relative',
                          }}
                        >
                          <div
                            style={{
                              position: 'absolute',
                              top: 0,
                              left: row.residualPct >= 0 ? '50%' : `${50 - barFillPct / 2}%`,
                              width: `${barFillPct / 2}%`,
                              height: '100%',
                              background: barColor,
                              borderRadius: 2,
                              transition: 'width 400ms ease, left 400ms ease',
                            }}
                          />
                          {/* Center tick */}
                          <div
                            style={{
                              position: 'absolute',
                              top: 0,
                              left: '50%',
                              width: 1,
                              height: '100%',
                              background: 'var(--border-emphasis)',
                              transform: 'translateX(-50%)',
                            }}
                          />
                        </div>
                      </div>

                      {/* STATUS */}
                      <div style={{ textAlign: 'right' }}>
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 4,
                            padding: '3px 8px',
                            borderRadius: 4,
                            fontSize: 10,
                            fontWeight: 700,
                            letterSpacing: '0.04em',
                            background: statusBg,
                            color: statusColor,
                            border: `1px solid ${statusBorder}`,
                            transition: 'background 300ms ease, color 300ms ease, border-color 300ms ease',
                          }}
                        >
                          {isCrit && <span style={{ fontSize: 8 }}>●</span>}
                          {isWarn && <span style={{ fontSize: 8 }}>▲</span>}
                          {isNorm && <span style={{ fontSize: 8 }}>✓</span>}
                          {row.status}
                        </span>
                      </div>
                    </div>
                  )
                })
              )}
            </div>

            {/* Section D: Predictive Maintenance Advisory Card — Redesigned */}
            {(() => {
              const level = current?.maintenance_level ?? 'NORMAL'
              const message = current?.maintenance_message || (running ? 'Engine telemetry conforms to nominal aero-piston envelopes. No urgent service required.' : 'Simulation inactive. Awaiting mission start or telemetry stream.')
              const isCrit = level === 'CRITICAL'
              const isWarn = level === 'WARNING'

              const cardBg = isCrit
                ? 'linear-gradient(180deg, rgba(239, 68, 68, 0.12) 0%, rgba(19, 31, 48, 0.95) 100%)'
                : isWarn
                ? 'linear-gradient(180deg, rgba(245, 158, 11, 0.12) 0%, rgba(19, 31, 48, 0.95) 100%)'
                : 'rgba(15, 23, 38, 0.85)'

              const borderCol = isCrit
                ? 'rgba(239, 68, 68, 0.45)'
                : isWarn
                ? 'rgba(245, 158, 11, 0.45)'
                : 'var(--border-default)'

              const badgeBg = isCrit
                ? 'rgba(239, 68, 68, 0.2)'
                : isWarn
                ? 'rgba(245, 158, 11, 0.2)'
                : 'rgba(34, 197, 94, 0.15)'

              const badgeColor = isCrit
                ? 'var(--red-400)'
                : isWarn
                ? 'var(--amber-400)'
                : 'var(--green-400)'

              const badgeBorder = isCrit
                ? 'rgba(239, 68, 68, 0.4)'
                : isWarn
                ? 'rgba(245, 158, 11, 0.4)'
                : 'rgba(34, 197, 94, 0.3)'

              return (
                <div
                  style={{
                    margin: '8px 16px 14px',
                    padding: '12px 14px',
                    borderRadius: 6,
                    background: cardBg,
                    border: `1px solid ${borderCol}`,
                    flexShrink: 0,
                    boxShadow: isCrit ? '0 0 16px rgba(239, 68, 68, 0.15)' : isWarn ? '0 0 12px rgba(245, 158, 11, 0.12)' : 'none',
                    transition: 'all 250ms ease',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 11, fontWeight: 800, color: isCrit ? 'var(--red-400)' : isWarn ? 'var(--orange-400)' : 'var(--text-primary)', letterSpacing: '0.06em' }}>
                        PREDICTIVE MAINTENANCE ADVISORY
                      </span>
                      <span style={{ fontSize: 9.5, color: 'var(--text-muted)' }}>
                        Autonomous Action Directive
                      </span>
                    </div>

                    {/* Severity Level Pill */}
                    <span
                      style={{
                        fontSize: 10,
                        fontWeight: 800,
                        fontFamily: 'var(--font-mono)',
                        padding: '2px 8px',
                        borderRadius: 4,
                        background: badgeBg,
                        color: badgeColor,
                        border: `1px solid ${badgeBorder}`,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 5,
                      }}
                    >
                      <span style={{ width: 6, height: 6, borderRadius: '50%', background: badgeColor }} />
                      LEVEL: {level}
                    </span>
                  </div>

                  {/* Main Advisory Recommendation */}
                  <div
                    style={{
                      fontSize: 12,
                      fontWeight: 600,
                      color: isCrit ? 'var(--red-300)' : isWarn ? 'var(--amber-300)' : 'var(--text-primary)',
                      marginTop: 6,
                      lineHeight: 1.45,
                    }}
                  >
                    {message}
                  </div>

                  {/* Operational Context Subtext */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8, paddingTop: 6, borderTop: '1px solid var(--border-subtle)', fontSize: 9.5, color: 'var(--text-muted)' }}>
                    <span>
                      {isCrit ? 'Action urgency: Immediate ground inspection recommended' : isWarn ? 'Action urgency: Monitor trend and schedule inspection interval' : 'Condition: All thermal and kinematic thresholds within safe flight margin'}
                    </span>
                    {current?.rul_hours !== undefined && (
                      <span style={{ fontFamily: 'var(--font-mono)' }}>
                        RUL Window: {current.rul_hours.toFixed(0)}h
                      </span>
                    )}
                  </div>
                </div>
              )
            })()}
          </div>
        </div>
      </div>
    </div>
  )
}
