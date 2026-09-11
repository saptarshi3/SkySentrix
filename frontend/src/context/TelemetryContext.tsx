import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { wsUrl, getSimulationState, startSimulation, stopSimulation, startDemoScenario, injectFault, clearFault, clearAllFaults, updateManualControl } from '../api/client'
import type { PipelineFrame } from '../types'

export interface NormalizedTelemetryState {
  // Raw and simulated measurements
  timestamp: string
  sim_time_sec: number
  mission_elapsed_sec: number
  mission_duration_sec: number
  mode: string
  rpm: number
  cht: number
  egt: number
  oil_pressure: number
  oil_temp: number
  fuel_flow: number
  vibration: number
  battery_voltage: number
  alternator_health: number
  injection_timing: number
  throttle: number
  engine_load: number
  altitude: number
  ambient_temp: number
  engine_efficiency: number
  manifold_pressure: number

  // Digital Twin Expected State
  expected_rpm: number
  expected_cht: number
  expected_egt: number
  expected_oil_pressure: number
  expected_oil_temp: number
  expected_fuel_flow: number
  expected_vibration: number
  expected_battery_voltage: number
  expected_manifold_pressure: number

  // Residuals (percentages)
  residual_rpm_pct: number
  residual_cht_pct: number
  residual_egt_pct: number
  residual_oil_pressure_pct: number
  residual_oil_temp_pct: number
  residual_fuel_flow_pct: number
  residual_vibration_pct: number
  residual_battery_voltage_pct: number
  residual_manifold_pressure_pct: number

  // AI Anomaly & Diagnosis
  anomaly_score: number
  anomaly_level: 'NORMAL' | 'WARNING' | 'CRITICAL'
  contributing_parameters: string[]
  diagnosis_fault: string
  diagnosis_confidence: number
  diagnosis_explanation: string
  diagnosis_affected_subsystems: string[]
  diagnosis_evidence: Record<string, number>

  // Health & Degradation
  health_index: number
  degradation_index: number
  degradation_rate_per_hour: number
  health_state: string
  subsystem_health: Record<string, number>

  // Prognostics & RUL
  rul_hours: number
  rul_trend: string
  rul_confidence_low: number
  rul_confidence_high: number
  rul_note: string

  // Maintenance Advisory
  maintenance_level: 'NORMAL' | 'WARNING' | 'CRITICAL'
  maintenance_message: string

  // Active faults map
  active_faults: Record<string, {
    target_severity: number
    current_severity: number
    progression_per_sec: number
    sensor_name?: string
  }>

  // Original underlying frame
  rawFrame: PipelineFrame | null
}

export type ConnectionStatus = 'connected' | 'connecting' | 'reconnecting' | 'offline'

export interface TelemetryContextType {
  connected: boolean
  connecting: boolean
  reconnecting: boolean
  connectionStatus: ConnectionStatus
  socketError: string | null
  running: boolean
  current: NormalizedTelemetryState | null
  rawFrame: PipelineFrame | null
  history: PipelineFrame[]
  latestServerState: Record<string, unknown> | null
  refreshSimulationState: () => Promise<void>
  startMission: (params: { mission_name: string; preset: string; duration_sec: number; demo_mode: boolean }) => Promise<any>
  stopMission: () => Promise<any>
  startDemo: () => Promise<any>
  injectFaultAction: (params: { fault_type: string; severity: number; progression_per_sec: number; sensor_name?: string }) => Promise<any>
  clearFaultAction: (fault_type: string) => Promise<any>
  clearAllFaultsAction: () => Promise<any>
  applyControls: (params: { mode?: string; throttle?: number; engine_load?: number; altitude?: number; ambient_temp?: number }) => Promise<any>
}

const TelemetryContext = createContext<TelemetryContextType | null>(null)

const MAX_HISTORY = 200

export function createNeutralPipelineFrame(): PipelineFrame {
  return {
    mission_id: null,
    sequence: 0,
    sim_time_sec: 0,
    mission_elapsed_sec: 0,
    mission_duration_sec: 0,
    active_faults: {},
    telemetry: {
      timestamp: new Date().toISOString(),
      mode: 'idle',
      rpm: 0,
      cht: 22,
      egt: 22,
      oil_pressure: 0,
      oil_temp: 22,
      fuel_flow: 0,
      vibration: 0,
      battery_voltage: 24.2,
      alternator_health: 1.0,
      injection_timing: 0,
      throttle: 0,
      engine_load: 0,
      altitude: 0,
      ambient_temp: 22,
      engine_efficiency: 1.0,
      manifold_pressure: 29.92,
      airspeed: 0,
      subsystem_health: {
        combustion: 100,
        thermal: 100,
        lubrication: 100,
        airflow: 100,
        electrical: 100,
        mechanical: 100,
      },
    },
    estimated: {
      rpm: 0,
      egt: 22,
      cht: 22,
      oil_temp: 22,
      oil_pressure: 0,
      vibration: 0,
      fuel_flow: 0,
      battery_voltage: 24.2,
      manifold_pressure: 29.92,
      engine_efficiency: 1.0,
      alternator_health: 1.0,
    },
    expected: {
      rpm: 0,
      cht: 22,
      egt: 22,
      oil_pressure: 0,
      oil_temp: 22,
      fuel_flow: 0,
      vibration: 0,
      battery_voltage: 24.2,
      manifold_pressure: 29.92,
    },
    residuals: {
      rpm: { actual: 0, expected: 0, residual: 0, residual_pct: 0 },
      cht: { actual: 22, expected: 22, residual: 0, residual_pct: 0 },
      egt: { actual: 22, expected: 22, residual: 0, residual_pct: 0 },
      oil_pressure: { actual: 0, expected: 0, residual: 0, residual_pct: 0 },
      oil_temp: { actual: 22, expected: 22, residual: 0, residual_pct: 0 },
      fuel_flow: { actual: 0, expected: 0, residual: 0, residual_pct: 0 },
      vibration: { actual: 0, expected: 0, residual: 0, residual_pct: 0 },
      battery_voltage: { actual: 24.2, expected: 24.2, residual: 0, residual_pct: 0 },
      manifold_pressure: { actual: 29.92, expected: 29.92, residual: 0, residual_pct: 0 },
    },
    anomaly: {
      score: 0,
      level: 'NORMAL',
      timestamp: new Date().toISOString(),
      contributing_parameters: [],
    },
    diagnosis: {
      probable_fault: 'normal',
      confidence: 0,
      contributing_parameters: [],
      affected_subsystems: [],
      evidence: {},
      explanation: 'Engine idle / standing by. All systems nominal.',
    },
    health: {
      health_index: 100,
      degradation_index: 0,
      degradation_rate_per_hour: 0,
      state: 'STANDBY',
      subsystem_health: {
        combustion: 100,
        thermal: 100,
        lubrication: 100,
        airflow: 100,
        electrical: 100,
        mechanical: 100,
      },
    },
    rul: {
      initial_rul_hours: 500,
      current_rul_hours: 500,
      degradation_rate_per_hour: 0,
      trend: 'STABLE',
      confidence_low_hours: 450,
      confidence_high_hours: 550,
      note: 'Engine standing by',
    },
    maintenance: {
      level: 'NORMAL',
      message: 'System ready. No maintenance actions required.',
    },
  }
}

export function createNeutralTelemetryState(): NormalizedTelemetryState {
  const neutralFrame = createNeutralPipelineFrame()
  return normalizePipelineFrame(neutralFrame)
}

export function normalizePipelineFrame(frame: PipelineFrame): NormalizedTelemetryState {
  const t = frame.telemetry || ({} as any)
  const exp = frame.expected || ({} as any)
  const res = frame.residuals || ({} as any)
  const anom = frame.anomaly || ({} as any)
  const diag = frame.diagnosis || ({} as any)
  const hlth = frame.health || ({} as any)
  const rul = frame.rul || ({} as any)
  const maint = frame.maintenance || ({} as any)

  return {
    timestamp: t.timestamp ? (typeof t.timestamp === 'string' ? t.timestamp : new Date(t.timestamp).toISOString()) : new Date().toISOString(),
    sim_time_sec: frame.sim_time_sec ?? 0,
    mission_elapsed_sec: frame.mission_elapsed_sec ?? 0,
    mission_duration_sec: frame.mission_duration_sec ?? 0,
    mode: t.mode ?? 'normal_endurance',
    rpm: t.rpm ?? 0,
    cht: t.cht ?? 0,
    egt: t.egt ?? 0,
    oil_pressure: t.oil_pressure ?? 0,
    oil_temp: t.oil_temp ?? 0,
    fuel_flow: t.fuel_flow ?? 0,
    vibration: t.vibration ?? 0,
    battery_voltage: t.battery_voltage ?? 0,
    alternator_health: t.alternator_health ?? 1.0,
    injection_timing: t.injection_timing ?? 0,
    throttle: t.throttle ?? 0,
    engine_load: t.engine_load ?? 0,
    altitude: t.altitude ?? 0,
    ambient_temp: t.ambient_temp ?? 15,
    engine_efficiency: t.engine_efficiency ?? 1.0,
    manifold_pressure: t.manifold_pressure ?? 0,

    expected_rpm: exp.rpm ?? 0,
    expected_cht: exp.cht ?? 0,
    expected_egt: exp.egt ?? 0,
    expected_oil_pressure: exp.oil_pressure ?? 0,
    expected_oil_temp: exp.oil_temp ?? 0,
    expected_fuel_flow: exp.fuel_flow ?? 0,
    expected_vibration: exp.vibration ?? 0,
    expected_battery_voltage: exp.battery_voltage ?? 0,
    expected_manifold_pressure: exp.manifold_pressure ?? 0,

    residual_rpm_pct: res.rpm?.residual_pct ?? 0,
    residual_cht_pct: res.cht?.residual_pct ?? 0,
    residual_egt_pct: res.egt?.residual_pct ?? 0,
    residual_oil_pressure_pct: res.oil_pressure?.residual_pct ?? 0,
    residual_oil_temp_pct: res.oil_temp?.residual_pct ?? 0,
    residual_fuel_flow_pct: res.fuel_flow?.residual_pct ?? 0,
    residual_vibration_pct: res.vibration?.residual_pct ?? 0,
    residual_battery_voltage_pct: res.battery_voltage?.residual_pct ?? 0,
    residual_manifold_pressure_pct: res.manifold_pressure?.residual_pct ?? 0,

    anomaly_score: anom.score ?? 0,
    anomaly_level: anom.level ?? 'NORMAL',
    contributing_parameters: anom.contributing_parameters ?? [],
    diagnosis_fault: diag.probable_fault ?? 'normal',
    diagnosis_confidence: diag.confidence ?? 0,
    diagnosis_explanation: diag.explanation ?? '',
    diagnosis_affected_subsystems: diag.affected_subsystems ?? [],
    diagnosis_evidence: diag.evidence ?? {},

    health_index: hlth.health_index ?? 100,
    degradation_index: hlth.degradation_index ?? 0,
    degradation_rate_per_hour: hlth.degradation_rate_per_hour ?? 0,
    health_state: hlth.state ?? 'HEALTHY',
    subsystem_health: hlth.subsystem_health ?? (t.subsystem_health || {}),

    rul_hours: rul.current_rul_hours ?? 480,
    rul_trend: rul.trend ?? 'STABLE',
    rul_confidence_low: rul.confidence_low_hours ?? 0,
    rul_confidence_high: rul.confidence_high_hours ?? 0,
    rul_note: rul.note ?? '',

    maintenance_level: maint.level ?? 'NORMAL',
    maintenance_message: maint.message ?? '',

    active_faults: frame.active_faults ?? {},
    rawFrame: frame,
  }
}

export const TelemetryProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [connected, setConnected] = useState(false)
  const [connecting, setConnecting] = useState(true)
  const [reconnecting, setReconnecting] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('connecting')
  const [socketError, setSocketError] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const [current, setCurrent] = useState<NormalizedTelemetryState | null>(() => createNeutralTelemetryState())
  const [rawFrame, setRawFrame] = useState<PipelineFrame | null>(() => createNeutralPipelineFrame())
  const [history, setHistory] = useState<PipelineFrame[]>([])
  const [latestServerState, setLatestServerState] = useState<Record<string, unknown> | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)
  const pingIntervalRef = useRef<number | null>(null)
  const reconnectAttemptsRef = useRef<number>(0)

  const refreshSimulationState = useCallback(async () => {
    try {
      const state = await getSimulationState()
      const isRunning = Boolean(state.running)
      setRunning(isRunning)
      setLatestServerState(state)

      if (!isRunning) {
        // Authoritative server state: stopped / idle
        setCurrent(createNeutralTelemetryState())
        setRawFrame(createNeutralPipelineFrame())
      } else if (state.latest) {
        const frame = state.latest as PipelineFrame
        setRawFrame(frame)
        setCurrent(normalizePipelineFrame(frame))
      }
    } catch {
      // ignore network errors when offline
    }
  }, [])

  // Single WebSocket connection instance with auto-reconnect
  useEffect(() => {
    let unmounted = false

    const connectWebSocket = () => {
      if (unmounted) return
      if (reconnectAttemptsRef.current === 0) {
        setConnecting(true)
        setReconnecting(false)
        setConnectionStatus('connecting')
      } else {
        setConnecting(false)
        setReconnecting(true)
        setConnectionStatus('reconnecting')
      }

      try {
        const ws = new WebSocket(wsUrl)
        wsRef.current = ws

        ws.onopen = () => {
          if (unmounted) return
          reconnectAttemptsRef.current = 0
          setConnected(true)
          setConnecting(false)
          setReconnecting(false)
          setConnectionStatus('connected')
          setSocketError(null)

          if (pingIntervalRef.current) clearInterval(pingIntervalRef.current)
          pingIntervalRef.current = window.setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send('ping')
            }
          }, 2000)
        }

        ws.onmessage = (event) => {
          if (unmounted) return
          try {
            const payload = JSON.parse(event.data)
            if (payload.type === 'state') {
              setLatestServerState(payload)
              if (payload.running !== undefined) {
                const isRunning = Boolean(payload.running)
                setRunning(isRunning)
                if (!isRunning) {
                  // Authoritative server stopped state
                  setCurrent(createNeutralTelemetryState())
                  setRawFrame(createNeutralPipelineFrame())
                } else if (payload.latest) {
                  const frame = payload.latest as PipelineFrame
                  setRawFrame(frame)
                  setCurrent(normalizePipelineFrame(frame))
                }
              }
              return
            }

            // Received live telemetry frame
            const frame = payload as PipelineFrame
            setRunning(true)
            setRawFrame(frame)
            const normalized = normalizePipelineFrame(frame)
            setCurrent(normalized)

            setHistory((prev) => {
              const next = [...prev, frame]
              return next.length > MAX_HISTORY ? next.slice(-MAX_HISTORY) : next
            })
          } catch {
            setSocketError('Unable to parse telemetry payload')
          }
        }

        ws.onerror = () => {
          if (unmounted) return
          setSocketError('WebSocket connection error')
        }

        ws.onclose = () => {
          if (unmounted) return
          setConnected(false)
          setConnecting(false)
          reconnectAttemptsRef.current += 1

          if (reconnectAttemptsRef.current > 4) {
            setReconnecting(false)
            setConnectionStatus('offline')
          } else {
            setReconnecting(true)
            setConnectionStatus('reconnecting')
          }

          if (pingIntervalRef.current) {
            clearInterval(pingIntervalRef.current)
            pingIntervalRef.current = null
          }
          // schedule reconnect after 2 seconds
          if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current)
          reconnectTimeoutRef.current = window.setTimeout(() => {
            connectWebSocket()
          }, 2000)
        }
      } catch (err) {
        if (!unmounted) {
          setConnected(false)
          setConnecting(false)
          setReconnecting(false)
          setConnectionStatus('offline')
          setSocketError('Failed to initialize WebSocket')
        }
      }
    }

    connectWebSocket()
    void refreshSimulationState()

    const pollInterval = window.setInterval(() => {
      void refreshSimulationState()
    }, 2500)

    return () => {
      unmounted = true
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current)
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current)
      clearInterval(pollInterval)
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [refreshSimulationState])

  const startMission = useCallback(async (params: { mission_name: string; preset: string; duration_sec: number; demo_mode: boolean }) => {
    setHistory([])
    const res = await startSimulation(params)
    setRunning(true)
    await refreshSimulationState()
    return res
  }, [refreshSimulationState])

  const stopMission = useCallback(async () => {
    try {
      const res = await stopSimulation()
      setRunning(false)
      setCurrent(createNeutralTelemetryState())
      setRawFrame(createNeutralPipelineFrame())
      setHistory([])
      await refreshSimulationState()
      return res
    } catch (err) {
      setRunning(false)
      setCurrent(createNeutralTelemetryState())
      setRawFrame(createNeutralPipelineFrame())
      setHistory([])
      throw err
    }
  }, [refreshSimulationState])

  const startDemo = useCallback(async () => {
    const res = await startDemoScenario()
    setRunning(true)
    await refreshSimulationState()
    return res
  }, [refreshSimulationState])

  const injectFaultAction = useCallback(async (params: { fault_type: string; severity: number; progression_per_sec: number; sensor_name?: string }) => {
    const res = await injectFault(params)
    await refreshSimulationState()
    return res
  }, [refreshSimulationState])

  const clearFaultAction = useCallback(async (fault_type: string) => {
    const res = await clearFault(fault_type)
    await refreshSimulationState()
    return res
  }, [refreshSimulationState])

  const clearAllFaultsAction = useCallback(async () => {
    const res = await clearAllFaults()
    await refreshSimulationState()
    return res
  }, [refreshSimulationState])

  const applyControls = useCallback(async (params: { mode?: string; throttle?: number; engine_load?: number; altitude?: number; ambient_temp?: number }) => {
    const res = await updateManualControl(params)
    await refreshSimulationState()
    return res
  }, [refreshSimulationState])

  return (
    <TelemetryContext.Provider
      value={{
        connected,
        connecting,
        reconnecting,
        connectionStatus,
        socketError,
        running,
        current,
        rawFrame,
        history,
        latestServerState,
        refreshSimulationState,
        startMission,
        stopMission,
        startDemo,
        injectFaultAction,
        clearFaultAction,
        clearAllFaultsAction,
        applyControls,
      }}
    >
      {children}
    </TelemetryContext.Provider>
  )
}

export function useTelemetry(): TelemetryContextType {
  const ctx = useContext(TelemetryContext)
  if (!ctx) {
    throw new Error('useTelemetry must be used within a TelemetryProvider')
  }
  return ctx
}
