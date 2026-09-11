import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

interface PistonEngineModelProps {
  rpm: number
  faultType?: string | null
  anomalyLevel?: string
  viewMode?: 'normal' | 'xray' | 'component'
  selectedComponent?: string | null
  affectedSubsystems?: string[]
}

// Shared materials
const MAT_CRANKCASE = new THREE.MeshStandardMaterial({ color: '#7a818c', roughness: 0.5, metalness: 0.8 })
const MAT_CRANKCASE_HIGHLIGHT = new THREE.MeshStandardMaterial({ color: '#ea6a0a', roughness: 0.5, metalness: 0.8, emissive: '#f97316', emissiveIntensity: 0.3 })
const MAT_CYLINDER = new THREE.MeshStandardMaterial({ color: '#2a2f36', roughness: 0.6, metalness: 0.7 })
const MAT_CYL_HEAD = new THREE.MeshStandardMaterial({ color: '#687282', roughness: 0.4, metalness: 0.85 })
const MAT_EXHAUST = new THREE.MeshStandardMaterial({ color: '#574841', roughness: 0.8, metalness: 0.4 })
const MAT_EXHAUST_GLOW = new THREE.MeshStandardMaterial({ color: '#3a2016', roughness: 0.8, metalness: 0.4, emissive: '#ff4400', emissiveIntensity: 0.8 })
const MAT_INTAKE = new THREE.MeshStandardMaterial({ color: '#3a4454', roughness: 0.5, metalness: 0.8 })
const MAT_CHROME = new THREE.MeshStandardMaterial({ color: '#e2e8f0', roughness: 0.1, metalness: 0.95 })
const MAT_IGNITION = new THREE.MeshStandardMaterial({ color: '#f97316', roughness: 0.7, metalness: 0.1 })
const MAT_PROP_HUB = new THREE.MeshStandardMaterial({ color: '#b0b8c4', roughness: 0.3, metalness: 0.9 })
const MAT_PROP_BLADE = new THREE.MeshStandardMaterial({ color: '#1a1d24', roughness: 0.3, metalness: 0.3 })
const MAT_PROP_TIP = new THREE.MeshStandardMaterial({ color: '#f97316', roughness: 0.4, metalness: 0.2 })
const MAT_XRAY = new THREE.MeshStandardMaterial({ color: '#38bdf8', roughness: 0.2, metalness: 0.5, transparent: true, opacity: 0.2, side: THREE.DoubleSide })
const MAT_OIL = new THREE.MeshStandardMaterial({ color: '#171717', roughness: 0.7, metalness: 0.5 })
const MAT_MOUNT = new THREE.MeshStandardMaterial({ color: '#475569', roughness: 0.5, metalness: 0.9 })

function getMaterial(key: string, isHighlighted: boolean, isFaulted: boolean, viewMode: string, faultMat?: THREE.Material) {
  if (viewMode === 'xray') return MAT_XRAY
  if (isFaulted && faultMat) return faultMat
  if (isHighlighted) return MAT_CRANKCASE_HIGHLIGHT
  switch (key) {
    case 'crankcase': return MAT_CRANKCASE
    case 'cylinder': return MAT_CYLINDER
    case 'head': return MAT_CYL_HEAD
    case 'exhaust': return MAT_EXHAUST
    case 'intake': return MAT_INTAKE
    case 'chrome': return MAT_CHROME
    case 'ignition': return MAT_IGNITION
    case 'prophub': return MAT_PROP_HUB
    case 'propblade': return MAT_PROP_BLADE
    case 'proptip': return MAT_PROP_TIP
    case 'oil': return MAT_OIL
    case 'mount': return MAT_MOUNT
    default: return MAT_CRANKCASE
  }
}

// Utility for curved tubes
function Tube({ points, radius, material }: { points: number[][], radius: number, material: THREE.Material }) {
  const curve = useMemo(() => new THREE.CatmullRomCurve3(points.map(p => new THREE.Vector3(...p))), [points])
  return (
    <mesh castShadow receiveShadow material={material}>
      <tubeGeometry args={[curve, 32, radius, 12, false]} />
    </mesh>
  )
}

function EngineCrankcase({ selected, viewMode }: { selected: boolean, viewMode: string }) {
  const mat = getMaterial('crankcase', selected, false, viewMode)
  return (
    <group>
      {/* Main Block Halves */}
      <mesh position={[0.07, 0, 0]} castShadow receiveShadow material={mat}>
        <boxGeometry args={[0.14, 0.36, 0.65]} />
      </mesh>
      <mesh position={[-0.07, 0, 0]} castShadow receiveShadow material={mat}>
        <boxGeometry args={[0.14, 0.36, 0.65]} />
      </mesh>
      {/* Split Line Flange */}
      <mesh position={[0, 0, 0]} castShadow receiveShadow material={mat}>
        <boxGeometry args={[0.015, 0.38, 0.68]} />
      </mesh>
      
      {/* Top curved spine */}
      <mesh position={[0, 0.18, 0]} rotation={[Math.PI/2, 0, 0]} castShadow material={mat}>
        <cylinderGeometry args={[0.10, 0.10, 0.65, 24]} />
      </mesh>
      {/* Bottom curved belly */}
      <mesh position={[0, -0.18, 0]} rotation={[Math.PI/2, 0, 0]} castShadow material={mat}>
        <cylinderGeometry args={[0.10, 0.10, 0.65, 24]} />
      </mesh>
      
      {/* Structural Ribs */}
      {[-0.2, -0.05, 0.1, 0.25].map((z, i) => (
        <group key={i} position={[0, 0, z]}>
          <mesh castShadow material={mat}>
             <boxGeometry args={[0.3, 0.37, 0.02]} />
          </mesh>
        </group>
      ))}

      {/* Front Snout (Prop Shaft Housing) */}
      <mesh position={[0, 0, 0.38]} rotation={[Math.PI/2, 0, 0]} castShadow material={mat}>
        <cylinderGeometry args={[0.06, 0.10, 0.12, 32]} />
      </mesh>
    </group>
  )
}

function Cylinder({ position, isRight, selected, faulted, viewMode }: { position: [number, number, number], isRight: boolean, selected: boolean, faulted: boolean, viewMode: string }) {
  const rotZ = isRight ? -Math.PI / 2 : Math.PI / 2
  const dir = isRight ? 1 : -1

  const barrelMat = getMaterial('cylinder', selected, false, viewMode)
  const headMat = getMaterial('head', selected, faulted, viewMode, MAT_EXHAUST_GLOW)
  
  // Fins
  const fins = []
  for (let i = 0; i < 16; i++) {
    fins.push(
      <mesh key={`fin-${i}`} position={[0, 0.14 + i * 0.012, 0]} castShadow material={barrelMat}>
        <cylinderGeometry args={[0.12, 0.12, 0.003, 32]} />
      </mesh>
    )
  }

  // Exhaust port
  const exhaustPts = [
    [0, 0.38, -0.08],
    [0, 0.38, -0.15],
    [dir * -0.05, 0.30, -0.2],
    [dir * -0.1, 0.0, -0.25]
  ]

  // Intake port
  // const intakePts = [
  //   [0, 0.42, 0.05],
  //   [0, 0.50, 0.12],
  //   [dir * -0.05, 0.55, 0.15]
  // ]

  return (
    <group position={position}>
      {/* X-Ray Internal Piston */}
      {viewMode === 'xray' && (
        <mesh position={[dir * 0.25, 0, 0]} rotation={[0, 0, Math.PI/2]}>
          <cylinderGeometry args={[0.10, 0.10, 0.15, 24]} />
          <meshStandardMaterial color="#e2e8f0" roughness={0.2} metalness={0.95} />
        </mesh>
      )}

      <group rotation={[0, 0, rotZ]}>
        {/* Barrel Core */}
        <mesh position={[0, 0.22, 0]} castShadow material={barrelMat}>
          <cylinderGeometry args={[0.08, 0.08, 0.22, 24]} />
        </mesh>
        
        {/* Fins */}
        {viewMode !== 'xray' && fins}

        {/* Cylinder Head */}
        <mesh position={[0, 0.38, 0]} castShadow material={headMat}>
          <boxGeometry args={[0.22, 0.14, 0.22]} />
        </mesh>
        <mesh position={[0, 0.38, 0]} castShadow material={headMat}>
          <cylinderGeometry args={[0.14, 0.14, 0.14, 32]} />
        </mesh>

        {/* Rocker Cover */}
        <mesh position={[0, 0.48, 0]} castShadow material={getMaterial('chrome', selected, false, viewMode)}>
          <boxGeometry args={[0.16, 0.05, 0.12]} />
        </mesh>
        <mesh position={[0, 0.48, 0]} castShadow material={getMaterial('chrome', selected, false, viewMode)} rotation={[Math.PI/2, 0, 0]}>
          <cylinderGeometry args={[0.06, 0.06, 0.16, 16]} />
        </mesh>

        {/* Spark Plugs (Dual) */}
        <mesh position={[0.08, 0.42, 0.12]} rotation={[Math.PI/4, 0, 0]} castShadow material={getMaterial('chrome', false, false, viewMode)}>
          <cylinderGeometry args={[0.012, 0.012, 0.06, 8]} />
        </mesh>
        <mesh position={[-0.08, 0.42, 0.12]} rotation={[Math.PI/4, 0, 0]} castShadow material={getMaterial('chrome', false, false, viewMode)}>
          <cylinderGeometry args={[0.012, 0.012, 0.06, 8]} />
        </mesh>

        {/* Pushrod Tubes */}
        <mesh position={[0.05, 0.25, 0.09]} rotation={[0.05, 0, 0]} castShadow material={getMaterial('chrome', false, false, viewMode)}>
          <cylinderGeometry args={[0.008, 0.008, 0.35, 12]} />
        </mesh>
        <mesh position={[-0.05, 0.25, 0.09]} rotation={[0.05, 0, 0]} castShadow material={getMaterial('chrome', false, false, viewMode)}>
          <cylinderGeometry args={[0.008, 0.008, 0.35, 12]} />
        </mesh>

        {/* Local Exhaust Header stub */}
        {viewMode !== 'xray' && <Tube points={exhaustPts} radius={0.022} material={getMaterial('exhaust', false, faulted, viewMode, MAT_EXHAUST_GLOW)} />}
      </group>
    </group>
  )
}

function ExhaustSystem({ faulted, viewMode }: { faulted: boolean, viewMode: string }) {
  if (viewMode === 'xray') return null
  const mat = getMaterial('exhaust', false, faulted, viewMode, MAT_EXHAUST_GLOW)
  
  // Right side exhaust path merging
  const rPts1 = [[0.15, -0.2, 0.08], [0.25, -0.4, 0.08], [0.25, -0.5, 0.0], [0.2, -0.6, -0.1]]
  const rPts2 = [[0.15, -0.2, -0.24], [0.25, -0.4, -0.24], [0.25, -0.5, -0.1], [0.2, -0.6, -0.1]]
  const rPtsOut = [[0.2, -0.6, -0.1], [0.15, -0.8, -0.15], [0.15, -1.0, -0.15]]

  // Left side exhaust path merging
  const lPts1 = [[-0.15, -0.2, 0.08], [-0.25, -0.4, 0.08], [-0.25, -0.5, 0.0], [-0.2, -0.6, -0.1]]
  const lPts2 = [[-0.15, -0.2, -0.24], [-0.25, -0.4, -0.24], [-0.25, -0.5, -0.1], [-0.2, -0.6, -0.1]]
  const lPtsOut = [[-0.2, -0.6, -0.1], [-0.15, -0.8, -0.15], [-0.15, -1.0, -0.15]]

  return (
    <group>
      <Tube points={rPts1} radius={0.025} material={mat} />
      <Tube points={rPts2} radius={0.025} material={mat} />
      <Tube points={rPtsOut} radius={0.035} material={mat} />
      
      <Tube points={lPts1} radius={0.025} material={mat} />
      <Tube points={lPts2} radius={0.025} material={mat} />
      <Tube points={lPtsOut} radius={0.035} material={mat} />
    </group>
  )
}

function IntakeSystem({ selected, viewMode }: { selected: boolean, viewMode: string }) {
  if (viewMode === 'xray') return null
  const mat = getMaterial('intake', selected, false, viewMode)
  const filterMat = getMaterial('oil', selected, false, viewMode)

  return (
    <group position={[0, -0.3, 0]}>
      {/* Sump/Oil Pan area which houses intake plenum in some Lycomings */}
      <mesh castShadow material={mat} position={[0, 0, 0]}>
         <boxGeometry args={[0.35, 0.15, 0.55]} />
      </mesh>
      
      {/* Throttle Body & Air Filter */}
      <mesh castShadow material={mat} position={[0, -0.15, 0.2]}>
        <cylinderGeometry args={[0.06, 0.06, 0.15, 24]} />
      </mesh>
      <mesh castShadow material={filterMat} position={[0, -0.25, 0.2]}>
        <cylinderGeometry args={[0.12, 0.12, 0.08, 32]} />
      </mesh>

      {/* Intake pipes to cylinders */}
      <Tube points={[[0.15, 0.05, 0.15], [0.25, 0.15, 0.15], [0.35, 0.25, 0.10], [0.45, 0.35, 0.10]]} radius={0.018} material={mat} />
      <Tube points={[[0.15, 0.05, -0.15], [0.25, 0.15, -0.15], [0.35, 0.25, -0.20], [0.45, 0.35, -0.20]]} radius={0.018} material={mat} />
      <Tube points={[[-0.15, 0.05, 0.15], [-0.25, 0.15, 0.15], [-0.35, 0.25, 0.10], [-0.45, 0.35, 0.10]]} radius={0.018} material={mat} />
      <Tube points={[[-0.15, 0.05, -0.15], [-0.25, 0.15, -0.15], [-0.35, 0.25, -0.20], [-0.45, 0.35, -0.20]]} radius={0.018} material={mat} />
    </group>
  )
}

function Propeller({ rpm, selected, viewMode }: { rpm: number, selected: boolean, viewMode: string }) {
  const propRef = useRef<THREE.Group>(null)
  
  useFrame((_, delta) => {
    if (propRef.current) {
      propRef.current.rotation.z += (rpm / 60) * delta * Math.PI * 2
    }
  })

  const hubMat = getMaterial('prophub', selected, false, viewMode)
  const bladeMat = getMaterial('propblade', selected, false, viewMode)
  const tipMat = getMaterial('proptip', selected, false, viewMode)

  return (
    <group position={[0, 0, 0.44]}>
      {/* Spinner */}
      <mesh castShadow material={hubMat} position={[0, 0, 0.15]} rotation={[Math.PI/2, 0, 0]}>
        <coneGeometry args={[0.15, 0.35, 32]} />
      </mesh>
      
      {/* Backplate */}
      <mesh castShadow material={hubMat} position={[0, 0, 0]} rotation={[Math.PI/2, 0, 0]}>
        <cylinderGeometry args={[0.15, 0.15, 0.02, 32]} />
      </mesh>

      <group ref={propRef} position={[0, 0, 0.05]}>
        {/* Hub center */}
        <mesh castShadow material={getMaterial('chrome', false, false, viewMode)} rotation={[Math.PI/2, 0, 0]}>
          <cylinderGeometry args={[0.08, 0.08, 0.1, 32]} />
        </mesh>

        {/* Blade 1 */}
        <group position={[0, 0.6, 0]}>
          <mesh castShadow material={bladeMat} rotation={[0, -0.2, 0]}>
            <boxGeometry args={[0.08, 1.0, 0.015]} />
          </mesh>
          <mesh castShadow material={tipMat} position={[0, 0.45, 0]} rotation={[0, -0.2, 0]}>
            <boxGeometry args={[0.085, 0.1, 0.02]} />
          </mesh>
        </group>

        {/* Blade 2 */}
        <group position={[0, -0.6, 0]}>
          <mesh castShadow material={bladeMat} rotation={[0, -0.2, 0]}>
            <boxGeometry args={[0.08, 1.0, 0.015]} />
          </mesh>
          <mesh castShadow material={tipMat} position={[0, -0.45, 0]} rotation={[0, -0.2, 0]}>
            <boxGeometry args={[0.085, 0.1, 0.02]} />
          </mesh>
        </group>
      </group>
    </group>
  )
}

function Accessories({ selected, faulted, viewMode }: { selected: boolean, faulted: boolean, viewMode: string }) {
  if (viewMode === 'xray') return null
  const altMat = getMaterial('crankcase', selected, faulted, viewMode, MAT_EXHAUST_GLOW)
  const magMat = getMaterial('oil', selected, false, viewMode)
  
  return (
    <group position={[0, 0, 0]}>
      {/* Alternator (Front Left Belt Driven) */}
      <group position={[-0.2, -0.15, 0.35]}>
        <mesh castShadow material={altMat} rotation={[Math.PI/2, 0, 0]}>
          <cylinderGeometry args={[0.06, 0.06, 0.15, 24]} />
        </mesh>
        {/* Belt Pulley */}
        <mesh castShadow material={getMaterial('chrome', false, false, viewMode)} position={[0, 0, 0.08]} rotation={[Math.PI/2, 0, 0]}>
          <cylinderGeometry args={[0.04, 0.04, 0.02, 24]} />
        </mesh>
        {/* Cooling fan on alternator */}
        <mesh castShadow material={getMaterial('chrome', false, false, viewMode)} position={[0, 0, 0.06]} rotation={[0, 0, 0]}>
           <cylinderGeometry args={[0.065, 0.065, 0.01, 12]} />
        </mesh>
      </group>

      {/* Alternator Belt */}
      <mesh castShadow material={MAT_OIL} position={[-0.1, -0.075, 0.43]} rotation={[0, 0, -0.6]}>
        <boxGeometry args={[0.01, 0.28, 0.015]} />
      </mesh>
      <mesh castShadow material={MAT_OIL} position={[-0.1, -0.025, 0.43]} rotation={[0, 0, 0.6]}>
        <boxGeometry args={[0.01, 0.12, 0.015]} />
      </mesh>

      {/* Magnetos (Rear Top) */}
      <mesh castShadow material={magMat} position={[-0.08, 0.2, -0.3]}>
        <boxGeometry args={[0.1, 0.15, 0.1]} />
      </mesh>
      <mesh castShadow material={magMat} position={[0.08, 0.2, -0.3]}>
        <boxGeometry args={[0.1, 0.15, 0.1]} />
      </mesh>
      
      {/* Ignition Harness Ring */}
      <mesh castShadow material={MAT_IGNITION} position={[0, 0.25, -0.2]} rotation={[Math.PI/2, 0, 0]}>
        <torusGeometry args={[0.12, 0.01, 8, 24]} />
      </mesh>
      <Tube points={[[0.12, 0.25, -0.2], [0.2, 0.3, -0.1], [0.3, 0.35, 0.1], [0.45, 0.45, 0.15]]} radius={0.005} material={MAT_IGNITION} />
      <Tube points={[[-0.12, 0.25, -0.2], [-0.2, 0.3, -0.1], [-0.3, 0.35, 0.1], [-0.45, 0.45, 0.15]]} radius={0.005} material={MAT_IGNITION} />
    </group>
  )
}

function EngineMounts({ selected, viewMode }: { selected: boolean, viewMode: string }) {
  if (viewMode === 'xray') return null
  const mat = getMaterial('mount', selected, false, viewMode)
  const ringMat = getMaterial('chrome', false, false, viewMode)

  return (
    <group position={[0, 0, -0.35]}>
      {/* Fire Wall Mount Ring */}
      <mesh castShadow material={ringMat} position={[0, 0, -0.2]}>
        <torusGeometry args={[0.25, 0.015, 12, 32]} />
      </mesh>
      
      {/* Tubular Struts to Engine Block */}
      <Tube points={[[0.25, 0.15, -0.2], [0.15, 0.15, 0.0]]} radius={0.012} material={mat} />
      <Tube points={[[-0.25, 0.15, -0.2], [-0.15, 0.15, 0.0]]} radius={0.012} material={mat} />
      <Tube points={[[0.25, -0.15, -0.2], [0.15, -0.15, 0.0]]} radius={0.012} material={mat} />
      <Tube points={[[-0.25, -0.15, -0.2], [-0.15, -0.15, 0.0]]} radius={0.012} material={mat} />
      
      {/* Vibration Isolators (Rubber) */}
      {[ [0.15, 0.15, 0.0], [-0.15, 0.15, 0.0], [0.15, -0.15, 0.0], [-0.15, -0.15, 0.0] ].map((pos, i) => (
        <mesh key={i} castShadow material={MAT_OIL} position={pos as [number,number,number]} rotation={[0, Math.PI/2, 0]}>
          <cylinderGeometry args={[0.03, 0.03, 0.04, 16]} />
        </mesh>
      ))}
    </group>
  )
}

export function PistonEngineModel({
  rpm,
  faultType,
  anomalyLevel,
  viewMode = 'normal',
  selectedComponent = null,
  affectedSubsystems = [],
}: PistonEngineModelProps) {
  const isAnomaly = Boolean(anomalyLevel === 'WARNING' || anomalyLevel === 'CRITICAL')
  
  const subSet = new Set(affectedSubsystems.map(s => s.toLowerCase()))
  const isCombustion = Boolean(faultType?.includes('combustion') || faultType?.includes('misfire') || faultType?.includes('injector') || subSet.has('combustion'))
  const isFuel = Boolean(faultType?.includes('fuel') || faultType?.includes('injector') || subSet.has('fuel'))
  const isElectrical = Boolean(faultType?.includes('alternator') || subSet.has('electrical'))
  const isThermal = Boolean(faultType?.includes('overheat') || subSet.has('thermal'))
  const isMechanical = Boolean(faultType?.includes('vibration') || subSet.has('mechanical'))
  const isLubrication = Boolean(faultType?.includes('lubrication') || subSet.has('lubrication'))
  
  // Staggered cylinder positions (Lycoming layout)
  const cylSpacing = 0.28
  const cylRightZ = 0.08
  const cylLeftZ = cylRightZ - 0.12
  
  return (
    <group>
      {/* Base / Floor Shadow Catcher */}
      <mesh position={[0, -0.85, 0]} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <circleGeometry args={[2, 64]} />
        <meshStandardMaterial color="#0f172a" roughness={0.9} metalness={0.1} transparent opacity={0.8} />
      </mesh>

      <EngineCrankcase selected={selectedComponent === 'crankcase' || (isMechanical && isAnomaly)} viewMode={viewMode} />
      
      <Cylinder position={[0.2, 0, cylRightZ]} isRight={true} selected={selectedComponent === 'cylinders'} faulted={Boolean((isCombustion || isThermal) && isAnomaly)} viewMode={viewMode} />
      <Cylinder position={[-0.2, 0, cylLeftZ]} isRight={false} selected={selectedComponent === 'cylinders'} faulted={Boolean((isCombustion || isThermal) && isAnomaly)} viewMode={viewMode} />
      
      <Cylinder position={[0.2, 0, cylRightZ - cylSpacing]} isRight={true} selected={selectedComponent === 'cylinders'} faulted={Boolean((isCombustion || isThermal) && isAnomaly)} viewMode={viewMode} />
      <Cylinder position={[-0.2, 0, cylLeftZ - cylSpacing]} isRight={false} selected={selectedComponent === 'cylinders'} faulted={Boolean((isCombustion || isThermal) && isAnomaly)} viewMode={viewMode} />

      <ExhaustSystem faulted={(isCombustion || isThermal) && isAnomaly} viewMode={viewMode} />
      
      <IntakeSystem selected={selectedComponent === 'manifold' || (isFuel && isAnomaly)} viewMode={viewMode} />
      
      <Accessories selected={selectedComponent === 'alternator' || selectedComponent === 'ignition' || (isLubrication && isAnomaly)} faulted={isElectrical && isAnomaly} viewMode={viewMode} />
      
      <EngineMounts selected={selectedComponent === 'mounts' || (isMechanical && isAnomaly)} viewMode={viewMode} />
      
      <Propeller rpm={rpm} selected={selectedComponent === 'propeller'} viewMode={viewMode} />
    </group>
  )
}
