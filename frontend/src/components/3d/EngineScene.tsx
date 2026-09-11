import { Suspense, useState, useEffect, useRef } from 'react'
import { Canvas, useThree } from '@react-three/fiber'
import { OrbitControls, Environment, ContactShadows } from '@react-three/drei'
import * as THREE from 'three'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import { PistonEngineModel } from './PistonEngineModel'
import type { PipelineFrame } from '../../types'

type ViewMode = 'normal' | 'xray' | 'component'
type CameraPreset = 'iso' | 'front' | 'top' | 'side'

interface HotspotData {
  id: string
  label: string
  value: string
  unit: string
  status: 'normal' | 'warning' | 'critical'
  screenPos: { left: string; top: string }
  leaderLineEnd: { x: number; y: number } // relative percentage offset for SVG leader line
}

function SceneLighting() {
  return (
    <>
      {/* Studio Key Light */}
      <directionalLight
        position={[6, 8, 6]}
        intensity={2.4}
        color="#ffffff"
        castShadow
        shadow-mapSize={[1024, 1024]}
        shadow-camera-far={20}
      />
      {/* Fill Light */}
      <directionalLight
        position={[-6, 5, 4]}
        intensity={1.4}
        color="#93c5fd"
      />
      {/* Orange Accent Rim Light */}
      <directionalLight
        position={[4, 4, -7]}
        intensity={2.0}
        color="#fb923c"
      />
      {/* Under-glow Light */}
      <directionalLight
        position={[0, -5, 2]}
        intensity={0.9}
        color="#38bdf8"
      />
      <ambientLight intensity={0.65} color="#e2e8f0" />
      <hemisphereLight
        color="#cbd5e1"
        groundColor="#1e293b"
        intensity={0.75}
      />
    </>
  )
}

function CameraController({ preset }: { preset: CameraPreset }) {
  const { camera } = useThree()

  useEffect(() => {
    if (preset === 'iso') {
      camera.position.set(2.2, 1.4, 2.8)
    } else if (preset === 'front') {
      camera.position.set(0, 0, 3.4)
    } else if (preset === 'top') {
      camera.position.set(0, 3.4, 0.01)
    } else if (preset === 'side') {
      camera.position.set(3.4, 0.1, 0)
    }
    camera.lookAt(0, 0, 0)
  }, [preset, camera])

  return null
}

interface EngineSceneProps {
  frame: PipelineFrame | null
  isConnected: boolean
}

function getStatus(value: number, warnThreshold: number, critThreshold: number, invert = false): 'normal' | 'warning' | 'critical' {
  if (invert) {
    if (value < critThreshold) return 'critical'
    if (value < warnThreshold) return 'warning'
    return 'normal'
  }
  if (value > critThreshold) return 'critical'
  if (value > warnThreshold) return 'warning'
  return 'normal'
}

export function EngineScene({ frame, isConnected }: EngineSceneProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('normal')
  const [autoRotate, setAutoRotate] = useState(false)
  const [cameraPreset, setCameraPreset] = useState<CameraPreset>('iso')
  const [selectedComponent, setSelectedComponent] = useState<string | null>(null)
  const [showSpecsPanel, setShowSpecsPanel] = useState(true)

  const controlsRef = useRef<OrbitControlsImpl>(null)
  const t = frame?.telemetry

  const handleResetCamera = () => {
    setCameraPreset('iso')
    if (controlsRef.current) {
      controlsRef.current.reset()
    }
  }

  const hotspots: HotspotData[] = [
    {
      id: 'rpm',
      label: 'Propeller / RPM',
      value: t ? t.rpm.toFixed(0) : '---',
      unit: 'RPM',
      status: t ? getStatus(t.rpm, 2400, 2800) : 'normal',
      screenPos: { left: '16%', top: '22%' },
      leaderLineEnd: { x: 38, y: 38 },
    },
    {
      id: 'egt',
      label: 'Exhaust / EGT',
      value: t ? t.egt.toFixed(0) : '---',
      unit: '°C',
      status: t ? getStatus(t.egt, 700, 850) : 'normal',
      screenPos: { left: '12%', top: '56%' },
      leaderLineEnd: { x: 30, y: 55 },
    },
    {
      id: 'cht',
      label: 'Cylinder Head',
      value: t ? t.cht.toFixed(0) : '---',
      unit: '°C',
      status: t ? getStatus(t.cht, 200, 250) : 'normal',
      screenPos: { left: '72%', top: '20%' },
      leaderLineEnd: { x: 58, y: 35 },
    },
    {
      id: 'oil',
      label: 'Oil System',
      value: t ? `${t.oil_pressure.toFixed(1)} PSI` : '---',
      unit: `${t ? t.oil_temp.toFixed(1) : '--'}°C`,
      status: t ? getStatus(t.oil_pressure, 0, 20, true) : 'normal',
      screenPos: { left: '70%', top: '65%' },
      leaderLineEnd: { x: 52, y: 62 },
    },
    {
      id: 'fuel',
      label: 'Fuel System',
      value: t ? t.fuel_flow.toFixed(1) : '---',
      unit: 'L/h',
      status: 'normal',
      screenPos: { left: '44%', top: '12%' },
      leaderLineEnd: { x: 48, y: 26 },
    },
    {
      id: 'alt',
      label: 'Alternator',
      value: t ? t.battery_voltage.toFixed(1) : '---',
      unit: 'V',
      status: t ? getStatus(t.battery_voltage, 0, 11.5, true) : 'normal',
      screenPos: { left: '18%', top: '78%' },
      leaderLineEnd: { x: 26, y: 64 },
    },
    {
      id: 'manifold',
      label: 'Intake Manifold',
      value: t && t.manifold_pressure !== undefined ? t.manifold_pressure.toFixed(1) : '---',
      unit: 'kPa',
      status: 'normal',
      screenPos: { left: '76%', top: '44%' },
      leaderLineEnd: { x: 54, y: 42 },
    },
  ]

  const componentsList = [
    { id: 'propeller', name: '1. Propeller / Crankshaft' },
    { id: 'alternator', name: '2. Alternator' },
    { id: 'manifold', name: '3. Intake Manifold' },
    { id: 'fuel', name: '4. Fuel System / Injectors' },
    { id: 'cylinders', name: '5. Cylinders ×4' },
    { id: 'oil', name: '6. Oil System / Cooler' },
    { id: 'ignition', name: '7. Dual Ignition Magnetos' },
    { id: 'mounts', name: '8. Engine Mounts' },
  ]

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', display: 'flex', overflow: 'hidden' }}>
      {/* Left/Center: Main 3D Engine Viewport */}
      <div style={{ flex: 1, position: 'relative', height: '100%' }}>
        <div className="engine-viewport-grid" />

        {/* Three.js Canvas */}
        <Canvas
          style={{ width: '100%', height: '100%' }}
          gl={{ antialias: true, alpha: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.25 }}
          shadows
          camera={{ fov: 45, near: 0.1, far: 100 }}
        >
          <CameraController preset={cameraPreset} />
          <SceneLighting />
          <Environment preset="city" />
          <ContactShadows
            position={[0, -0.70, 0]}
            opacity={0.35}
            scale={3.5}
            blur={2.5}
            color="#000020"
          />
          <Suspense fallback={null}>
            <PistonEngineModel
              rpm={t?.rpm ?? 0}
              faultType={frame?.diagnosis?.probable_fault}
              anomalyLevel={frame?.anomaly?.level}
              viewMode={viewMode}
              selectedComponent={selectedComponent}
              affectedSubsystems={frame?.diagnosis?.affected_subsystems}
            />
          </Suspense>
          <OrbitControls
            ref={controlsRef}
            enableDamping
            dampingFactor={0.08}
            minDistance={1.2}
            maxDistance={6}
            maxPolarAngle={Math.PI * 0.72}
            autoRotate={autoRotate}
            autoRotateSpeed={0.6}
            enablePan={true}
          />
          <gridHelper args={[8, 16, '#1e2d44', '#0f172a']} position={[0, -0.71, 0]} />
        </Canvas>

        {/* Floating Telemetry Callout Cards with Leader Lines */}
        {hotspots.map(h => (
          <div key={h.id}>
            {/* Leader line overlay SVG */}
            <svg
              style={{
                position: 'absolute',
                inset: 0,
                width: '100%',
                height: '100%',
                pointerEvents: 'none',
                zIndex: 4,
              }}
            >
              <line
                x1={h.screenPos.left}
                y1={h.screenPos.top}
                x2={`${h.leaderLineEnd.x}%`}
                y2={`${h.leaderLineEnd.y}%`}
                stroke="var(--orange-500)"
                strokeWidth="1.2"
                strokeDasharray="3 3"
                opacity="0.7"
              />
              <circle
                cx={`${h.leaderLineEnd.x}%`}
                cy={`${h.leaderLineEnd.y}%`}
                r="3"
                fill="var(--orange-500)"
              />
            </svg>

            {/* Hotspot label card */}
            <HotspotCallout data={h} />
          </div>
        ))}

        {/* View Mode Controls Toolbar Overlay */}
        <div className="engine-controls-bar">
          <button
            className={`engine-ctrl-btn${viewMode === 'normal' ? ' active' : ''}`}
            onClick={() => setViewMode('normal')}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
            </svg>
            3D View
          </button>
          <button
            className={`engine-ctrl-btn${viewMode === 'xray' ? ' active' : ''}`}
            onClick={() => setViewMode('xray')}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8"/>
              <line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            X-Ray
          </button>
          <button
            className={`engine-ctrl-btn${viewMode === 'component' ? ' active' : ''}`}
            onClick={() => setViewMode('component')}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
            Component
          </button>

          <div style={{ width: 1, height: 18, background: 'var(--border-subtle)', margin: '0 4px' }} />

          <button
            className={`engine-ctrl-btn${autoRotate ? ' active' : ''}`}
            onClick={() => setAutoRotate(r => !r)}
            title="Toggle auto rotation"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="23 4 23 10 17 10"/>
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
            </svg>
            Rotate
          </button>

          <button className="engine-ctrl-btn" onClick={handleResetCamera} title="Reset view">
            Reset
          </button>

          <button
            className="engine-ctrl-btn"
            onClick={() => setShowSpecsPanel(s => !s)}
            title="Toggle Engine Specifications Panel"
          >
            Specs Panel
          </button>
        </div>

        {/* Multi-View Angle Preset Selector (Bottom Left Overlay) */}
        <div
          style={{
            position: 'absolute',
            bottom: 12,
            left: 12,
            display: 'flex',
            gap: 4,
            background: 'rgba(8, 12, 20, 0.85)',
            border: '1px solid var(--border-default)',
            borderRadius: 6,
            padding: 3,
            backdropFilter: 'blur(8px)',
            zIndex: 10,
          }}
        >
          <button
            className={`engine-ctrl-btn${cameraPreset === 'iso' ? ' active' : ''}`}
            onClick={() => setCameraPreset('iso')}
            style={{ padding: '4px 8px', fontSize: 10 }}
          >
            ISO 3D
          </button>
          <button
            className={`engine-ctrl-btn${cameraPreset === 'front' ? ' active' : ''}`}
            onClick={() => setCameraPreset('front')}
            style={{ padding: '4px 8px', fontSize: 10 }}
          >
            FRONT
          </button>
          <button
            className={`engine-ctrl-btn${cameraPreset === 'top' ? ' active' : ''}`}
            onClick={() => setCameraPreset('top')}
            style={{ padding: '4px 8px', fontSize: 10 }}
          >
            TOP
          </button>
          <button
            className={`engine-ctrl-btn${cameraPreset === 'side' ? ' active' : ''}`}
            onClick={() => setCameraPreset('side')}
            style={{ padding: '4px 8px', fontSize: 10 }}
          >
            SIDE
          </button>
        </div>

        {/* Offline warning overlay */}
        {!isConnected && (
          <div
            style={{
              position: 'absolute',
              top: 12,
              right: 12,
              padding: '6px 12px',
              borderRadius: 4,
              background: 'rgba(26,5,5,0.92)',
              border: '1px solid rgba(239,68,68,0.5)',
              fontSize: 10,
              fontWeight: 700,
              color: 'var(--red-400)',
              letterSpacing: '0.06em',
              zIndex: 20,
            }}
          >
            BACKEND CONNECTION LOST
          </div>
        )}

        {/* Critical anomaly badge */}
        {frame?.anomaly?.level === 'CRITICAL' && (
          <div
            style={{
              position: 'absolute',
              top: 12,
              left: '50%',
              transform: 'translateX(-50%)',
              padding: '6px 16px',
              borderRadius: 4,
              background: 'rgba(26,5,5,0.92)',
              border: '1px solid rgba(239,68,68,0.6)',
              fontSize: 11,
              fontWeight: 700,
              color: 'var(--red-400)',
              letterSpacing: '0.08em',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              zIndex: 20,
              animation: 'pulse-live 1.5s ease-in-out infinite',
            }}
          >
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--red-500)' }} />
            CRITICAL ENGINE ANOMALY DETECTED
          </div>
        )}
      </div>

      {/* Right Side: Engine Reference & Component Selection Panel */}
      {showSpecsPanel && (
        <div
          style={{
            width: 220,
            background: 'var(--bg-panel)',
            borderLeft: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            overflowY: 'auto',
            padding: 10,
            gap: 12,
            zIndex: 10,
            flexShrink: 0,
          }}
        >
          {/* Engine Specs */}
          <div>
            <div className="panel-title" style={{ marginBottom: 6 }}>ENGINE SPECIFICATIONS</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: 2 }}>
                <span style={{ color: 'var(--text-muted)' }}>Model</span>
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Lycoming IO-360</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: 2 }}>
                <span style={{ color: 'var(--text-muted)' }}>Config</span>
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>4-Cyl Opposed</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: 2 }}>
                <span style={{ color: 'var(--text-muted)' }}>Displacement</span>
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>361 cu in (5.9L)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: 2 }}>
                <span style={{ color: 'var(--text-muted)' }}>Aspiration</span>
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Naturally Aspirated</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: 2 }}>
                <span style={{ color: 'var(--text-muted)' }}>Cooling</span>
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Air Cooled</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Power</span>
                <span style={{ fontWeight: 600, color: 'var(--orange-400)' }}>180 HP Ref</span>
              </div>
            </div>
          </div>

          {/* Key Components Highlight List */}
          <div>
            <div className="panel-title" style={{ marginBottom: 6 }}>KEY COMPONENTS</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {componentsList.map(c => (
                <button
                  key={c.id}
                  onClick={() => setSelectedComponent(selectedComponent === c.id ? null : c.id)}
                  style={{
                    textAlign: 'left',
                    padding: '4px 6px',
                    borderRadius: 3,
                    background: selectedComponent === c.id ? 'var(--orange-glow)' : 'var(--bg-card)',
                    border: `1px solid ${selectedComponent === c.id ? 'var(--orange-500)' : 'var(--border-subtle)'}`,
                    color: selectedComponent === c.id ? 'var(--orange-400)' : 'var(--text-secondary)',
                    fontSize: 10,
                    cursor: 'pointer',
                    transition: 'all 120ms ease',
                  }}
                >
                  {c.name}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function HotspotCallout({ data }: { data: HotspotData }) {
  const statusClass = `status-${data.status}`
  return (
    <div
      style={{
        position: 'absolute',
        left: data.screenPos.left,
        top: data.screenPos.top,
        pointerEvents: 'none',
        zIndex: 5,
      }}
    >
      <div className={`hotspot-label ${statusClass}`}>
        <div className="hotspot-label-name">{data.label}</div>
        <div className="hotspot-label-value">
          {data.value}
          {data.unit && <span className="hotspot-label-unit" style={{ marginLeft: 3 }}>{data.unit}</span>}
        </div>
        {data.status !== 'normal' && (
          <div style={{ fontSize: 8.5, fontWeight: 600, letterSpacing: '0.06em', marginTop: 1 }}>
            {data.status.toUpperCase()}
          </div>
        )}
      </div>
    </div>
  )
}
