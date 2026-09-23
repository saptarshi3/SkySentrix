import axios from 'axios'
import type { Mission, MissionTelemetryRow, ValidationResult } from '../types'

const rawApiBase = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').trim()
const API_BASE = rawApiBase.replace(/\/+$/, '')

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
})

const defaultWsUrl = `${API_BASE.replace(/^http:\/\//i, 'ws://').replace(/^https:\/\//i, 'wss://')}/ws/telemetry`
export const wsUrl = (import.meta.env.VITE_WS_URL ? String(import.meta.env.VITE_WS_URL).trim() : defaultWsUrl)

export async function fetchPresets() {
  const { data } = await api.get('/api/mission-presets')
  return data.presets as Record<string, {
    description: string
    segments: Array<{
      name: string
      duration_ratio: number
      throttle: number
      engine_load: number
      altitude: number
      ambient_temp: number
    }>
  }>
}

export async function fetchFaultTypes() {
  const { data } = await api.get('/api/fault-types')
  return data.fault_types as string[]
}

export async function startSimulation(payload: {
  mission_name: string
  preset: string
  duration_sec: number
  demo_mode: boolean
}) {
  const { data } = await api.post('/api/simulation/start', payload)
  return data
}

export async function stopSimulation() {
  const { data } = await api.post('/api/simulation/stop')
  return data
}

export async function resetSimulation() {
  const { data } = await api.post('/api/simulation/reset')
  return data
}

export async function startDemoScenario() {
  const { data } = await api.post('/api/simulation/demo')
  return data
}

export async function updateManualControl(payload: {
  mode?: string
  throttle?: number
  engine_load?: number
  altitude?: number
  ambient_temp?: number
}) {
  const { data } = await api.post('/api/simulation/control', payload)
  return data
}

export async function injectFault(payload: {
  fault_type: string
  severity: number
  progression_per_sec: number
  sensor_name?: string
}) {
  const { data } = await api.post('/api/simulation/faults/inject', payload)
  return data
}

export async function clearFault(faultType: string) {
  const { data } = await api.delete(`/api/simulation/faults/${faultType}`)
  return data
}

export async function clearAllFaults() {
  const { data } = await api.delete('/api/simulation/faults')
  return data
}

export async function getSimulationState() {
  const { data } = await api.get('/api/simulation/state')
  return data
}

export async function listMissions() {
  const { data } = await api.get<Mission[]>('/api/missions')
  return data
}

export async function getMissionTelemetry(missionId: number) {
  const { data } = await api.get<{ mission: Mission; rows: MissionTelemetryRow[] }>(`/api/missions/${missionId}/telemetry`)
  return data
}

export async function uploadCsv(file: File, missionName: string) {
  const form = new FormData()
  form.append('file', file)
  form.append('mission_name', missionName)
  const { data } = await api.post('/api/csv/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return data as {
    mission_id: number
    rows_processed: number
    anomalies_detected: number
    warnings_or_critical: number
  }
}

export async function runValidation() {
  const { data } = await api.post<ValidationResult>('/api/validation/run')
  return data
}

export async function getArchitecture() {
  const { data } = await api.get('/api/architecture')
  return data as { pipeline: string[]; note: string }
}
