import { useState } from 'react'
import { uploadCsv } from '../api/client'

const requiredColumns = [
  'timestamp',
  'rpm',
  'cht',
  'egt',
  'oil_pressure',
  'oil_temp',
  'fuel_flow',
  'vibration',
  'battery_voltage',
  'alternator_health',
  'injection_timing',
  'throttle',
  'engine_load',
  'altitude',
  'ambient_temp',
]

export function CsvPage() {
  const [file, setFile] = useState<File | null>(null)
  const [missionName, setMissionName] = useState('CSV Imported Flight')
  const [msg, setMsg] = useState('')
  const [processing, setProcessing] = useState(false)

  const upload = async () => {
    if (!file) {
      setMsg('Please select a valid .csv file first')
      return
    }

    setProcessing(true)
    setMsg('Uploading and processing CSV telemetry through Digital Twin pipeline...')
    try {
      const result = await uploadCsv(file, missionName)
      setMsg(
        `SUCCESS: Processed Mission #${result.mission_id} | Rows: ${result.rows_processed} | Anomalies: ${result.anomalies_detected} | Critical Alerts: ${result.warnings_or_critical}`
      )
    } catch (error: unknown) {
      if (typeof error === 'object' && error !== null && 'response' in error) {
        const withResponse = error as { response?: { data?: { detail?: string } } }
        setMsg(`ERROR: ${withResponse.response?.data?.detail ?? 'CSV processing failed'}`)
      } else {
        setMsg('ERROR: CSV upload and processing failed')
      }
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div className="dashboard-layout">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">CSV Telemetry Ingestion</h1>
          <p className="page-subtitle">Import offline telemetry data files and execute full Digital Twin residual & diagnostic analysis</p>
        </div>
      </div>

      <div className="mission-page-layout">
        {/* Card 1: Upload Form */}
        <section className="section-card">
          <div className="section-card-header">Flight File Selection</div>
          <div className="section-card-body">
            <div className="form-field">
              <label className="form-label">Mission / Aircraft Tag</label>
              <input className="form-input" value={missionName} onChange={(e) => setMissionName(e.target.value)} />
            </div>

            <div className="form-field">
              <label className="form-label">Telemetry File (.CSV)</label>
              <input
                className="form-input"
                type="file"
                accept=".csv"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                style={{ padding: '6px 10px' }}
              />
            </div>

            <button className="btn btn-primary" onClick={upload} disabled={processing} style={{ marginTop: 8 }}>
              {processing ? 'Processing Telemetry...' : 'Upload & Run Analytics Pipeline'}
            </button>

            <div
              style={{
                marginTop: 12,
                padding: '10px 12px',
                borderRadius: 4,
                background: msg.startsWith('SUCCESS')
                  ? 'var(--green-900)'
                  : msg.startsWith('ERROR')
                  ? 'var(--red-900)'
                  : 'var(--bg-card)',
                border: '1px solid var(--border-default)',
                fontSize: 11,
                fontFamily: 'var(--font-mono)',
                color: msg.startsWith('SUCCESS')
                  ? 'var(--green-400)'
                  : msg.startsWith('ERROR')
                  ? 'var(--red-400)'
                  : 'var(--text-secondary)',
              }}
            >
              {msg || 'Awaiting file selection...'}
            </div>
          </div>
        </section>

        {/* Card 2: Required Telemetry Schema */}
        <section className="section-card">
          <div className="section-card-header">Required CSV Schema Specification</div>
          <div className="section-card-body">
            <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              The SkySentrix Digital Twin pipeline requires the following 15 telemetry parameters per row for state estimation & residual computation:
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 6, marginTop: 8 }}>
              {requiredColumns.map((col) => (
                <div
                  key={col}
                  style={{
                    padding: '4px 8px',
                    borderRadius: 3,
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border-subtle)',
                    fontSize: 10,
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--orange-400)',
                  }}
                >
                  {col}
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
