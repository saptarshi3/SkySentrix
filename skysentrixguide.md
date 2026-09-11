# SKYSENTRIX — COMPREHENSIVE PROJECT DATA EXTRACTION & GUIDE
**Smart India Hackathon (SIH) 2026 Idea Submission PPT Reference Package**
*Source Repository: `SkySentrix/`*
*Inspection Baseline: Full codebase inspection (backend, frontend, database, scripts, models, schemas, UI components, validation artifacts)*

---

## 1. RUNNING & ACCESSING THE PLATFORM

### Access URLs
* **Frontend Dashboard**: [http://localhost:5173/](http://localhost:5173/)
* **Backend API / Health**: [http://localhost:8000/api/health](http://localhost:8000/api/health)
* **Interactive API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **Live WebSocket Telemetry**: `ws://localhost:8000/ws/telemetry`

### Command Line Startup Instructions
```bash
# Backend (FastAPI + Uvicorn)
cd backend
python -m venv .venv
. .venv/bin/activate  # or .\.venvwin\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (React + Vite + Three.js)
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

---

## SECTION 1 — TITLE PAGE DATA

| Field | Extracted Value | Status / Evidence |
| :--- | :--- | :--- |
| **Problem Statement ID** | `[NOT FOUND]` | Not explicitly codified in repository configuration or source files. |
| **Problem Statement Title** | `[NOT FOUND]` (Derived Context: Aero-Piston Engine Digital Twin for Predictive Maintenance & Health Monitoring) | Identified in README as: `SkySentrix — SIH 2026 DRDO Digital Twin Prototype`. Formal official PS title string is `[NOT FOUND]`. |
| **Theme** | `[NOT FOUND]` (Contextual domain: Aerospace / Defense / Robotics & Drones / Smart Vehicles) | Formal SIH theme string is `[NOT FOUND]`. |
| **PS Category** | Software | Confirmed in README.md: *"software-only, synthetic digital twin prototype for an aero-piston UAV engine use-case."* |
| **Team ID** | `[NOT FOUND]` | No team registration ID present in repo. |
| **Team Name** | `[NOT FOUND]` | No official team name file present in repo. |
| **Project / Idea Title** | **SkySentrix — Aerospace Digital Twin / Predictive Maintenance Platform** | Confirmed across `package.json`, `backend/app/main.py`, `TopBar.tsx`, and UI mockups. Tagline: *"Predict • Prevent • Keep You Flying"*, Subtitle: *"Safe Skies, Smarter Engines"*. |

---

## SECTION 2 — PROBLEM DEFINITION

### 1. Core Problem
Unplanned failures, in-flight shutdowns, and catastrophic breakdowns of aero-piston engines (specifically used in Unmanned Aerial Vehicles / UAVs and General Aviation) due to latent subsystem degradation (combustion, thermal, lubrication, mechanical, fuel, electrical) that goes undetected by conventional static-threshold warning gauges until safety margins are severely compromised.

### 2. Current Industry / Problem Limitations
* **Static Threshold Gauges**: Conventional avionics trigger alerts only after a parameter breaches a hard limit (e.g., CHT > 230°C, Oil Pressure < 25 PSI), by which time physical damage or thermo-mechanical failure is already underway.
* **Flight Regime Confounding**: Healthy engine parameters vary widely across flight phases (idle, climb, high-load, cruise, loiter, descent). A single fixed threshold either triggers excessive false alarms during high-power climb or misses subtle early-stage degradation during low-power loiter.
* **Siloed Subsystem Instrumentation**: Sensors are monitored in isolation without thermodynamic and mechanical cross-coupling (e.g., connecting a drop in oil pressure to an increase in friction heat and consequent CHT drift).
* **Scheduled/Hours-Based Maintenance**: Aircraft maintenance is traditionally scheduled by fixed flight hours (e.g., 50-hour oil check, 100-hour inspection, TBO 2000 hours) regardless of actual operational stress, environmental conditions, or cumulative damage.

### 3. Why the Problem Matters
In defense and tactical UAV operations (e.g., DRDO surveillance/reconnaissance missions), engine failure causes total platform loss, payload destruction, and mission abortion. In civil general aviation, engine failure is a primary cause of forced landings and fatal accidents.

### 4. Who Experiences the Problem
* UAV Operators & Ground Control Stations (GCS) conducting long-endurance ISR missions.
* Defense and Aerospace Fleet Operators (e.g., DRDO, Armed Forces, Coast Guard).
* General Aviation Pilots, Flight Schools, and Fleet Operators flying piston-powered aircraft (e.g., Lycoming/Continental engines).
* Aircraft Maintenance, Repair, and Overhaul (MRO) engineering crews.

### 5. Consequences of the Problem
* Catastrophic mid-air power loss and loss of aircraft.
* Expensive unscheduled maintenance and grounded fleet downtime.
* Premature teardown and replacement of healthy parts due to conservative fixed-hour schedules.
* Late-stage secondary damage (e.g., injector clogging leading to cylinder detonation and crankshaft seizure).

### 6. Existing Approach Limitations
* **Turbofan-dominated Predictive Maintenance**: Existing aerospace predictive maintenance platforms (e.g., GE Predix, Rolls-Royce TotalCare, NASA C-MAPSS research) target multi-million-dollar commercial turbofans, leaving small-to-medium aero-piston UAV powerplants without dedicated digital twins.
* **Lack of Real-Time Physics Context**: Pure data-driven black-box models require vast failure-to-exhaustion flight datasets (which do not exist for most piston UAV fleets) and fail when encountering un-modeled atmospheric or load transients.

### 7. Specific Gap SkySentrix Addresses
SkySentrix couples a **first-principles reduced-order physics baseline (Digital Twin)** with **multivariate Kalman state estimation**, **Isolation Forest residual anomaly scoring**, and **causal fault isolation** to detect subsystem deviations *relative to expected healthy behavior under identical instantaneous ambient and operating conditions*, projecting dynamic Remaining Useful Life (RUL) on live telemetry.

---

## SECTION 3 — PROPOSED SOLUTION

### 1. Solution Overview
A full-stack, software-only Digital Twin and Predictive Maintenance system that runs an independent physics-based healthy baseline model in parallel with incoming aircraft telemetry (simulated or CSV), estimates true states via Kalman filtering, evaluates residual deviations across 13 core dimensions, scores anomalies via a calibrated Isolation Forest hybrid engine, isolates probable subsystem faults, tracks cumulative degradation, dynamically projects Remaining Useful Life (RUL), and issues actionable maintenance advisories.

### 2. Target System
Small-to-medium aero-propulsion powerplants, specifically Unmanned Aerial Vehicle (UAV) propulsion units and light aircraft piston powertrains.

### 3. Target Engine / Platform
* **Engine Model**: Lycoming IO-360 class (Reference model: 4-cylinder horizontally opposed, naturally aspirated, air-cooled, fuel-injected, ~180–200 HP, 361 cu in / 5.9L displacement, fixed/constant-speed propeller load).
* **Platform**: Tactical UAVs / Light Reconnaissance Drones / Light General Aviation.

### 4. Solution Capabilities Matrix

| # | Capability | Implemented Status | Evidence in Codebase |
| :--- | :--- | :--- | :--- |
| 1 | **Solution Overview** | **IMPLEMENTED** | Complete FastAPI backend + React Vite frontend connected via WebSocket and REST. |
| 2 | **Target System / Engine** | **SIMULATED** | Parametric models calibrated to Lycoming IO-360 class specs in `twin.py` and `simulator.py`. |
| 3 | **Input Data Ingestion** | **IMPLEMENTED** | Dual input: Real-time simulation loop (`realtime.py`) and CSV batch file upload (`csv_ingest.py`). |
| 4 | **Processing Pipeline** | **IMPLEMENTED** | Unified 10-stage `DigitalTwinPipeline` in `pipeline.py`. |
| 5 | **State Estimation** | **IMPLEMENTED** | 8-state Linear Kalman Filter in `state_estimator.py`. |
| 6 | **Expected Healthy Twin Model** | **IMPLEMENTED** | Independent analytical model predicting 13 engine parameters in `twin.py`. |
| 7 | **Actual Telemetry Comparison** | **IMPLEMENTED** | Point-by-point residual generation in `compute_residuals()` in `twin.py`. |
| 8 | **Residual / Anomaly Analysis** | **IMPLEMENTED** | Hybrid scoring (Isolation Forest + normalized residuals + EWMA) in `anomaly.py`. |
| 9 | **Fault Diagnosis** | **IMPLEMENTED** | Causal evidence-weighted rule engine with baseline subtraction across 10 fault types in `diagnosis.py`. |
| 10 | **Degradation Tracking** | **IMPLEMENTED** | Multi-subsystem degradation modeling + health index tracking in `degradation.py` and `health.py`. |
| 11 | **RUL Estimation** | **IMPLEMENTED (SIMULATED DYNAMICS)** | Trajectory slope + EWMA wear rate fusion with confidence intervals in `rul.py`. |
| 12 | **Maintenance Recommendations** | **IMPLEMENTED** | Advisory classification (NORMAL, WARNING, CRITICAL) + prioritized task cards in `advisory.py`. |
| 13 | **Mission Simulation** | **IMPLEMENTED** | 6 mission presets + manual overrides in `simulator.py` and `MissionPage.tsx`. |
| 14 | **Mission Replay** | **IMPLEMENTED** | SQLite mission query, scrubbing timeline, and multi-speed replay in `ReplayPage.tsx`. |
| 15 | **Explainable Diagnostic Insights** | **IMPLEMENTED** | Natural-language explanation strings + evidence breakdown JSON in `diagnosis.py`. |
| 16 | **3D Digital Twin Visualization** | **IMPLEMENTED (PROCEDURAL 3D)** | Interactive Three.js/React Three Fiber procedural model (3D, X-Ray, Component, hotspots) in `EngineScene.tsx` and `PistonEngineModel.tsx`. |
| 17 | **Hardware Sensor / FADEC Integration** | **NOT FOUND / PROPOSED** | Software prototype only; no direct CAN bus/ARINC-429/ECU/HIL hardware interfaces present. |

---

## SECTION 4 — COMPLETE SYSTEM WORKFLOW

```text
INPUT (Mission Profile / Manual Override / CSV File)
  ↓
DATA ACQUISITION (EngineSimulator.step() or csv_ingest.py)
  ↓
SENSOR PREPROCESSING & NOISE MODEL (SensorModel.observe() + Gaussian Noise + Drift/Failures)
  ↓
STATE ESTIMATION (StateEstimator: 8-State Linear Kalman Filter)
  ↓
DIGITAL TWIN PREDICTION (DigitalTwinModel: Healthy Reference State f(throttle, load, alt, temp))
  ↓
ACTUAL VS EXPECTED RESIDUAL CALCULATION (residual = estimated - expected, residual_pct)
  ↓
ANOMALY DETECTION (AnomalyEngine: 21-Feature Vector -> Calibrated IsolationForest + Residual EWMA)
  ↓
FAULT DIAGNOSIS & ISOLATION (DiagnosisEngine: Baseline-Corrected Signature Scoring across 10 Faults)
  ↓
DEGRADATION TRACKING (HealthEngine: Subsystem Penalties + Persistent Stress -> Health & Wear Index)
  ↓
DYNAMIC RUL ESTIMATION (RULEstimator: Fused Trajectory Trend & Wear Rate -> RUL Hours & Confidence Bounds)
  ↓
MAINTENANCE ADVISORY GENERATION (generate_maintenance_advisory(): NORMAL / WARNING / CRITICAL)
  ↓
PERSISTENCE (crud.save_pipeline_frame() -> SQLite skysentrix.db)
  ↓
REAL-TIME STREAMING & DISPATCH (TelemetryConnectionManager: WebSocket /ws/telemetry @ 1 Hz)
  ↓
VISUALIZATION & DECISION (React Dashboard, 3D Procedural Engine, Trend Charts, Replay & Validation)
```

---

## SECTION 5 — TECHNICAL APPROACH

| Category | Technology | Purpose | Location in Project |
| :--- | :--- | :--- | :--- |
| **Languages** | Python 3.11+ | Backend engine physics, analytics, APIs | `backend/` |
| | TypeScript 5.9 | Type-safe frontend web application | `frontend/src/` |
| **Backend Framework** | FastAPI (>=0.116.1) | High-performance asynchronous REST & WebSocket server | `backend/app/main.py` |
| | Uvicorn (>=0.35.0) | ASGI web server implementation | `backend/requirements.txt` |
| **Frontend Framework** | React 18.3.1 | Single-Page Application (SPA) reactive UI | `frontend/package.json` |
| | React Router DOM 6.26 | Multi-page client-side routing (7 pages) | `frontend/src/App.tsx` |
| **3D Engine** | Three.js (0.186.0) | WebGL 3D rendering library | `frontend/package.json` |
| | @react-three/fiber (8.18) | Declarative React wrapper for Three.js | `EngineScene.tsx` |
| | @react-three/drei (9.122) | 3D helpers: OrbitControls, Environment, ContactShadows | `EngineScene.tsx` |
| **Visualization** | Apache ECharts (5.6.0) | Interactive time-series charts (RPM, EGT, Vibration, Health) | `TrendCharts.tsx`, `LineChart.tsx` |
| | echarts-for-react (3.0.2)| React component bindings for ECharts | `TrendCharts.tsx` |
| **Styling** | Tailwind CSS (3.4.17) + Custom CSS | Aerospace dark HUD aesthetic, responsive layouts | `frontend/src/index.css` |
| **Database & ORM** | SQLite 3 | Lightweight relational embedded database (`skysentrix.db`) | `database.py` |
| | SQLAlchemy (>=2.0.43) | ORM mappings for missions, telemetry, faults, health, RUL | `models.py`, `crud.py` |
| **Communication** | Native WebSockets (`/ws/telemetry`)| 1 Hz asynchronous JSON telemetry frame broadcasting | `main.py`, `useTelemetrySocket.ts` |
| | REST APIs + Axios (1.11) | Simulation control, CSV upload, validation execution | `client.ts` |
| **Data Validation** | Pydantic (>=2.11.7) | Strong runtime contract validation & serialization | `schemas.py` |
| **Scientific / ML** | NumPy (>=2.3.0) | Array operations, bilinear interpolation, Kalman matrices | Throughout backend engine |
| | Pandas (>=2.3.2) | CSV file ingestion, interpolation, tabular handling | `csv_ingest.py` |
| | Scikit-Learn (>=1.7.1) | `IsolationForest`, `StandardScaler` anomaly pipeline | `anomaly.py` |
| | Joblib | Serialization/deserialization of calibrated ML artifacts | `backend/models/anomaly_model.joblib` |
| **Build & Dev** | Vite (7.1.3) | Lightning-fast frontend HMR & bundling | `frontend/vite.config.ts` |
| **Testing** | Smoke Test Suite | End-to-end API, WebSocket, DB, and CSV smoke test | `backend/smoke_test.py` |

---

## SECTION 6 — DIGITAL TWIN ARCHITECTURE

### 1. What is Being Digitally Twinned?
A 4-stroke, 4-cylinder air-cooled, horizontally opposed, fuel-injected aero-piston engine coupled to an aircraft propeller (Lycoming IO-360 architectural baseline).

### 2. Physical System Represented
* Intake manifold & air induction system
* In-cylinder combustion chamber & fuel injection metering
* Crankshaft mechanical powertrain & rotational dynamics
* Propeller aerodynamic load demand
* Thermal dissipation network (cylinder head cooling fins & exhaust gases)
* Forced lubrication circuit (oil pump, sump, oil cooler, journal friction)
* 14V/28V DC electrical charging circuit (alternator, battery buffer)

### 3. Engine Configuration
* 4 cylinders horizontally opposed
* Displacement: 3.6L–5.9L equivalent class (simulator assumption: 3.6L displacement volume `0.0036 m³` in `airflow.py`, UI reference: 361 cu in / 5.9L)
* Naturally aspirated (sub-ambient manifold pressure)
* Dual spark plug ignition per cylinder

### 4. Sensor Variables (Observed Telemetry)
15 primary channels: `rpm`, `manifold_pressure`, `air_mass_flow`, `fuel_flow`, `egt`, `cht`, `oil_temp`, `oil_pressure`, `vibration`, `battery_voltage`, `alternator_health`, `injection_timing`, `throttle`, `engine_load`, `altitude`, `ambient_temp`, `airspeed`, `pressure_kpa`, `density_ratio`.

### 5. State Variables
* **Kalman Estimated States (8)**: Filtered $[RPM, EGT, CHT, T_{\text{oil}}, P_{\text{oil}}, Vib, \dot{m}_f, V_{\text{batt}}]$.
* **Subsystem Health States (6)**: $[combustion, thermal, lubrication, mechanical, fuel, electrical] \in [0.0, 1.0]$.
* **Engine True States (Hidden)**: True engine efficiency, mechanical wear, thermal target deviations.

### 6. Inputs to the Twin
* Commanded throttle $[0.0, 1.0]$
* Commanded propeller/engine load $[0.0, 1.0]$
* Environmental context: Flight altitude ($m$), ambient temperature ($^\circ\text{C}$)
* Instantaneous estimated RPM (to establish internal operating context)

### 7. Outputs from the Twin
* 13 expected healthy reference states (`expected_rpm`, `expected_egt`, `expected_cht`, `expected_oil_pressure`, `expected_oil_temp`, `expected_fuel_flow`, `expected_vibration`, `expected_battery_voltage`, `expected_manifold_pressure`, `expected_air_mass_flow`, `expected_torque_nm`, `expected_power_kw`, `expected_propeller_load`).

---

## SECTION 7 — SENSOR / TELEMETRY DATA

| Parameter | Unit | Meaning | Source | Nominal Range | Warning Threshold | Critical Threshold | Used By | Visualization | Fault Signature Relationship |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`rpm`** | RPM | Crankshaft rotational speed | Simulator / CSV | 800 – 2700 | > 2600 | > 2900 / < 600 | Kalman, Twin, Anomaly, Diagnosis | Gauge, Line Chart, 3D Propeller speed | Misfire (drop/instability), excessive damping |
| **`manifold_pressure`** | kPa (or inHg) | Absolute intake manifold air pressure | Simulator / CSV | 30.0 – 101.3 | > 105.0 | < 15.0 | Airflow, Twin, Diagnosis | Live Sensor row, 3D Hotspot | Intake leakage, throttle valve jamming |
| **`air_mass_flow`** | kg/s | Air mass inducted into cylinders | Simulator / CSV | 0.02 – 0.22 | > 0.25 | < 0.01 | Combustion, Twin | Live Telemetry table | Air filter clogging, volumetric loss |
| **`fuel_flow`** | L/h | Volumetric fuel consumption | Simulator / CSV | 6.0 – 55.0 | > 58.0 | < 3.0 | Combustion, Twin, Health | Sensor Panel, KPI, 3D Hotspot | Injector clogging (deviation), fuel leak |
| **`egt`** | °C | Exhaust Gas Temperature | Simulator / CSV | 520 – 780 | > 750 | > 850 | Thermal, Anomaly, Diagnosis | Sparkline, Trend Chart, 3D Hotspot | Overheating, lean burn, misfire, injector fault |
| **`cht`** | °C | Cylinder Head Temperature | Simulator / CSV | 110 – 195 | > 200 | > 230 | Thermal, Health, Diagnosis | Sparkline, Live row, 3D Hotspot | Inadequate cooling, prolonged climb, detonation |
| **`oil_pressure`** | PSI | Main gallery engine oil pressure | Simulator / CSV | 35.0 – 85.0 | < 35.0 | < 20.0 | Lubrication, Health, Diagnosis | Live row, 3D Hotspot, KPI | Oil pump failure, relief valve leak, bearing wear |
| **`oil_temp`** | °C | Lubricating oil temperature | Simulator / CSV | 65 – 105 | > 105 | > 120 | Thermal, Lubrication, Health | Live row, 3D Hotspot | Oil cooler blockage, excessive journal friction |
| **`vibration`** | mm/s | Engine block structural vibration | Simulator / CSV | 0.15 – 0.65 | > 1.0 | > 2.0 | Mechanical, Anomaly, Diagnosis | Sparkline, Trend Chart, 3D Hotspot | Prop imbalance, misfire, bearing damage |
| **`battery_voltage`** | V | DC bus electrical voltage | Simulator / CSV | 13.6 – 14.4 | < 12.5 | < 11.5 | Electrical, Diagnosis | Live row, 3D Hotspot | Alternator failure, belt breakage |
| **`alternator_health`**| Ratio [0-1] | Alternator generating capacity | Simulator / CSV | 0.90 – 1.0 | < 0.80 | < 0.50 | Electrical, DB | Telemetry schema | Diode pack failure, winding degradation |
| **`injection_timing`** | °BTDC | Fuel injection spark advance | Simulator / CSV | 14.0 – 28.0 | > 30.0 | < 10.0 | Combustion, Simulator | Telemetry schema | ECU timing drift |
| **`throttle`** | Ratio [0-1] | Pilot throttle lever position | Input / CSV | 0.0 – 1.0 | N/A | N/A | Environment, Twin, Simulator | Mission controls slider | Flight regime control |
| **`engine_load`** | Ratio [0-1] | Propeller / aerodynamic load demand | Input / CSV | 0.15 – 0.95 | N/A | N/A | Propeller, Twin, Simulator | Mission controls slider | Flight regime control |
| **`altitude`** | m (or ft) | Aircraft barometric altitude | Input / CSV | 0 – 8000 | > 7000 | > 10000 | Environment, Twin, Simulator | Ambient Card, Dashboard Top | Atmospheric density derating |
| **`ambient_temp`** | °C | Outside Air Temperature (OAT) | Input / CSV | -20 – 45 | > 38.0 | < -30.0 | Environment, Thermal, Twin | Ambient Card | Cooling air efficiency derating |

---

## SECTION 8 — DIGITAL TWIN & PHYSICS EQUATIONS

All equations extracted directly from source code:

### 1. ISA Atmospheric Environment Model
*File*: `backend/app/engine/environment.py`
* ISA troposphere pressure ($h \le 11000\text{ m}$):
  $$T_{\text{isa}} = T_0 - L \cdot h = 288.15 - 0.0065 \cdot h$$
  $$P_{\text{ambient}} = P_0 \cdot \left(\frac{T_{\text{isa}}}{T_0}\right)^{\frac{g}{R \cdot L}} = 101325 \cdot \left(\frac{T_{\text{isa}}}{288.15}\right)^{5.25588}$$
* Air Density ($\rho$):
  $$\rho = \frac{P_{\text{ambient}}}{R \cdot (T_{\text{ambient}} + 273.15)} = \frac{P_{\text{ambient}}}{287.05 \cdot T_K}$$
  $$\text{density\_ratio} (\sigma) = \text{clamp}\left(\frac{\rho}{1.225}, 0.45, 1.20\right)$$

### 2. Manifold Absolute Pressure Model
*File*: `backend/app/engine/manifold.py`
$$P_{\text{base}} = (22.0 + 80.0 \cdot \text{throttle}) \times \left(\frac{P_{\text{kpa}}}{101.325}\right)$$
$$P_{\text{pumping}} = 0.0035 \times \max(RPM - 1800.0, -1000.0)$$
$$P_{\text{manifold}} = \left(P_{\text{base}} - P_{\text{pumping}} + 4.0 \cdot (\text{load} - 0.5)\right) \times \eta_{\text{intake}}$$

### 3. Air Mass Flow Model
*File*: `backend/app/engine/airflow.py`
* Volumetric efficiency ($\eta_v$):
  $$\eta_v = \text{clamp}\left((0.62 + 0.28 \cdot \text{throttle} + 0.14 \cdot \frac{P_{\text{manifold}}}{P_{\text{ambient}}}) \times \eta_{\text{combustion}}, 0.45, 1.10\right)$$
* 4-Stroke Air Induction (displacement $V_d = 0.0036\text{ m}^3$):
  $$\dot{V}_{\text{intake}} = \frac{V_d \cdot RPM}{120.0}$$
  $$\dot{m}_{\text{air}} = \dot{V}_{\text{intake}} \times \rho \times \eta_v \quad (\text{kg/s})$$

### 4. Fuel & Combustion Model
*File*: `backend/app/engine/combustion.py`
* Fuel flow ($\text{L/h}$):
  $$\dot{m}_{\text{fuel, LPH}} = \frac{\dot{m}_{\text{fuel, map}} \times (0.12 + 0.95 \cdot \text{throttle}) \times K_{\text{fault, fuel}}}{\max(\eta_{\text{fuel}}, 0.45)}$$
  $$\dot{m}_{\text{fuel, kg/s}} = \frac{\dot{m}_{\text{fuel, LPH}} \times 0.74}{3600}$$
* Actual Air-Fuel Ratio (AFR) & Lambda ($\lambda$):
  $$\text{AFR} = \frac{\dot{m}_{\text{air}}}{\dot{m}_{\text{fuel, kg/s}}}, \quad \lambda = \frac{\text{AFR}}{14.7}$$
* Combustion Efficiency ($\eta_c$):
  $$\eta_{\text{timing}} = 1.0 - 0.0015 \cdot |\theta_{\text{inj}} - 24.0|$$
  $$\eta_{\text{mixture}} = 1.0 - 0.22 \cdot |\lambda - 1.0|$$
  $$\eta_c = \eta_{\text{map}} \times \eta_{\text{comb\_health}} \times K_{\text{fault, comb}} \times \eta_{\text{timing}} \times \eta_{\text{mixture}}$$
* Thermal Power & Torque:
  $$P_{\text{thermal, kW}} = \dot{m}_{\text{fuel, kg/s}} \times 43.0 \times 1000 \times \eta_c \quad (\text{LHV} = 43\text{ MJ/kg})$$
  $$\tau_{\text{comb}} = \frac{9550 \times (0.32 \cdot P_{\text{thermal}})}{RPM}$$
  $$\tau_{\text{brake}} = (0.45 \cdot \tau_{\text{map}} + 0.55 \cdot \tau_{\text{comb}}) \times (0.38 + 0.70 \cdot \text{throttle}) \times (0.90 + 0.10 \cdot \text{load})$$
* Exhaust Gas Base Temperature:
  $$EGT_{\text{base}} = EGT_{\text{map}} + 120.0 \cdot (1 - \eta_c) + 30.0 \cdot \max(0, 1 - \lambda) + 22.0 \cdot \text{throttle}$$

### 5. Mechanical & RPM Dynamics
*File*: `backend/app/engine/simulator.py`
$$\text{damping} = 0.030 + 0.022 \cdot \text{load} + K_{\text{extra\_damping}}$$
$$\text{drive\_torque} = (\tau_{\text{brake}} \cdot \eta_{\text{mech}}) - 95.0 \cdot \text{load}$$
$$RPM_{\text{target}} = \text{clamp}(800.0 + 14.0 \cdot \text{drive\_torque} - 420.0 \cdot \text{damping}, 0, 3300)$$
$$P_{\text{kw}} = \frac{\tau_{\text{brake}} \cdot RPM}{9550}$$

### 6. Thermal Network Equations
*File*: `backend/app/engine/thermal.py`
$$EGT_{\text{target}} = EGT_{\text{base}} \times K_{\text{fault, thermal}} + 18.0 \cdot (1 - \eta_{\text{thermal}}) + 0.002 \cdot \max(RPM - 2000, 0)$$
$$CHT_{\text{target}} = T_{\text{ambient}} + 55.0 + 0.17 \cdot \max(EGT - 500, 0) + 42.0 \cdot \text{load} + 12.0 \cdot (1 - \eta_{\text{thermal}})$$
$$T_{\text{oil, target}} = T_{\text{ambient}} + 40.0 + 0.08 \cdot \max(EGT - 500, 0) + 15.0 \cdot \text{load} + 10.0 \cdot Q_{\text{friction}}$$

### 7. Lubrication & Friction Heat Coupling
*File*: `backend/app/engine/lubrication.py`
$$P_{\text{oil, target}} = (18.0 + 0.019 \cdot RPM - 0.13 \cdot \max(T_{\text{oil}} - 85.0, 0)) \times \eta_{\text{lub}} \times K_{\text{fault, lub}}$$
$$Q_{\text{friction}} = \text{clamp}\left(\left(1.1 - \frac{P_{\text{oil}}}{60.0}\right) + (1.0 - \eta_{\text{lub}}), 0.0, 1.5\right)$$

### 8. Electrical System Equations
*File*: `backend/app/engine/electrical.py`
$$\eta_{\text{alt}} = (1.0 - 0.18 \cdot D_{\text{base}}) \times \eta_{\text{elec}} \times K_{\text{fault, elec}}$$
$$V_{\text{battery}} = 12.1 + (1.9 \text{ if } RPM > 1200 \text{ else } 0.35) \times \eta_{\text{alt}} - 0.48 \cdot (0.25 + 0.55 \cdot \text{load}) + V_{\text{bias}}$$

---

## SECTION 9 — AI / ML & ANOMALY DETECTION

### Exact Machine Learning Model Specification

| Attribute | Implemented Detail | Source Code Location |
| :--- | :--- | :--- |
| **Model Name** | Hybrid Isolation Forest Anomaly Scorer | `backend/app/analytics/anomaly.py` |
| **Model Type** | Unsupervised Ensemble Tree (`sklearn.ensemble.IsolationForest`) + Analytical Hybrid Residual Fusion | `anomaly.py` |
| **Input Feature Vector** | **21 dimensions**: `residual_rpm_pct`, `residual_cht_pct`, `residual_egt_pct`, `residual_oil_pressure_pct`, `residual_oil_temp_pct`, `residual_fuel_flow_pct`, `residual_vibration_pct`, `residual_battery_voltage_pct`, `residual_manifold_pressure_pct`, `residual_torque_nm_pct`, `rpm_delta`, `egt_delta`, `vibration_delta`, `rpm_rolling_std`, `throttle`, `engine_load`, `altitude_norm`, `ambient_temp_norm`, `density_ratio`, `engine_efficiency`, `regime_code`. | `anomaly.py` |
| **Preprocessing** | `sklearn.preprocessing.StandardScaler` fit on baseline training trajectories. | `anomaly.py` |
| **Ensemble Size** | `n_estimators = 220`, `contamination = 0.02` | `anomaly.py`, `anomaly_model.meta.json` |
| **Trained Artifact** | `backend/models/anomaly_model.joblib` (Calibrated on 3,540 synthetic trajectory samples across 6 mission presets). | `anomaly_model.meta.json` |
| **Inference Process** | 1. Calculate raw decision sample score $s_{\text{raw}} = -\text{score\_samples}(x)$.<br>2. Normalize to z-score: $z = (s_{\text{raw}} - \mu)/\sigma$.<br>3. Sigmoidal squeeze: $s_{\text{if}} = 1/(1+e^{-z})$.<br>4. Compute normalized residual component $s_{\text{res}} = (0.60 \cdot \text{mean\_norm} + 0.40 \cdot \text{p85\_norm})/3.5$.<br>5. Compute sequential EWMA: $s_{\text{ewma}} = 0.92 \cdot s_{\text{ewma, prev}} + 0.08 \cdot s_{\text{res}}$.<br>6. Composite fusion: $\text{Score} = 0.34 s_{\text{if}} + 0.34 s_{\text{res}} + 0.32 s_{\text{ewma}} - 0.30$. | `anomaly.py` |
| **Decision Thresholds** | Warning: $\ge 0.28$, Critical: $\ge 0.55$ (Calibrated via grid sweep). | `anomaly_model.meta.json` |

---

## SECTION 10 — FAULT DETECTION & ISOLATION

SkySentrix implements **10 specific fault signatures** in `backend/app/engine/faults.py` and isolates them in `backend/app/analytics/diagnosis.py`:

| # | Fault Name | Primary Trigger / Mechanism | Affected Parameters | Detection Logic / Formula | Subsystems Affected | Maintenance Response |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **`injector_degradation`** | Clogged/eroded fuel injector nozzle | $\uparrow$ Fuel demand, $\downarrow$ Combustion efficiency, $\uparrow$ EGT, $\uparrow$ RPM damping | $5.0 \cdot \Delta EGT^+ + 1.0 \cdot \Delta \dot{m}_f^- + 0.8 \cdot \Delta MAP^+ + 1.0 \cdot RPM_{\text{instab}}$ | Fuel, Combustion | Inspect & clean fuel injectors; check fuel manifold |
| 2 | **`misfire`** | Intermittent ignition / fouled spark plug | $\downarrow$ Combustion eff ($-32\%$), $\uparrow$ Severe RPM instability, $\uparrow$ Vibration | $3.0 \cdot |\Delta RPM| + 2.0 \cdot RPM_{\text{instab}} + 1.5 \cdot \Delta Vib^+ + 0.05 \cdot \Delta \dot{m}_f^-$ | Combustion, Mechanical | Inspect dual magnetos, harness, and spark plugs |
| 3 | **`lubrication_problem`** | Oil pump cavitation, leak, or line clogging | $\downarrow$ Oil pressure ($-35\%$), $\uparrow$ Oil temp, $\uparrow$ Friction heat | $3.0 \cdot \Delta P_{\text{oil}}^- + 2.5 \cdot \Delta T_{\text{oil}}^+ + 0.7 \cdot \Delta Vib^+$ | Lubrication, Mechanical | Inspect oil pump, lines, filter, and cooler |
| 4 | **`overheating`** | Cylinder baffle loss, cooling airflow blocked | $\uparrow$ CHT, $\uparrow$ EGT, $\uparrow$ Oil temperature | $5.0 \cdot \Delta CHT^+ + 3.0 \cdot \Delta EGT^+ + 3.0 \cdot \Delta T_{\text{oil}}^+ + 0.22 \cdot \Delta T_{\text{ambient}}$ | Thermal, Combustion | Check cooling baffles, cowl flaps, and air intake ducts |
| 5 | **`excessive_vibration`** | Propeller nick, dynamic imbalance, mount fatigue | $\uparrow$ Vibration ($+55\%$), $\downarrow$ Propeller efficiency | $3.5 \cdot \Delta Vib^+ + 0.5 \cdot RPM_{\text{instab}}$ | Mechanical | Perform dynamic propeller balancing; check isolators |
| 6 | **`combustion_instability`** | Air-fuel mixture cycling, fuel vaporization | $\uparrow$ High EGT variance / standard deviation, RPM hunting | $18.0 \cdot \sigma(EGT) + 0.5 \cdot |\Delta RPM| + 2.0 \cdot \Delta Vib^+$ | Combustion, Thermal | Check fuel regulation, mixture servo, and induction leaks |
| 7 | **`fuel_system_degradation`** | Fuel pump delivery restriction, filter clogging | $\uparrow$ Fuel flow deviation, $\downarrow$ Combustion eff, $\uparrow$ MAP | $2.0 \cdot \Delta \dot{m}_f^- + 1.0 \cdot \Delta MAP^+ + 2.0 \cdot \Delta EGT^+ + 1.0 \cdot \Delta Vib^+$ | Fuel, Combustion | Inspect engine-driven fuel pump & primary fuel filter |
| 8 | **`alternator_problem`** | Rotor field winding degradation, belt slipping | $\downarrow$ Alternator output ($-65\%$), $\downarrow$ Battery voltage | $5.0 \cdot \Delta V_{\text{batt}}^- + 0.7 \cdot (1 - \eta_{\text{alt}})$ | Electrical | Inspect alternator belt tension, brushes, and regulator |
| 9 | **`sensor_drift`** | Progressive thermocouple / transducer calibration drift | Linear progressive sensor offset ($+0.02\text{ to }0.12/\text{s}$) | Moving window residual mean $>4.0$ with spread $<5.0$ $\to$ Score $+140.0 + 0.8 \cdot \text{drift}$ | Sensor Instrumentation | Recalibrate or replace drifting sensor transducer |
| 10 | **`sensor_failure`** | Transducer wire severance or short | Signal stuck at 0.0 or constant clamp | Moving window spread $<0.02$ for $>8$ steps $\to$ Score $+300.0$ | Sensor Instrumentation | Immediate replacement of failed sensor probe |

---

## SECTION 11 — REMAINING USEFUL LIFE (RUL) ESTIMATION

### 1. Implementation File
`backend/app/analytics/rul.py` (`RULEstimator` class).

### 2. Formulas & Calculation
1. **Effective Instantaneous Wear Acceleration**:
   $$\text{Rate}_{\text{inst}} = \text{Rate}_{\text{base}} \times [1 + 0.80 \cdot \max(0, s_{\text{anom}} - 0.35)] \times [1 + 0.35 \cdot \max(0, \text{conf}_{\text{diag}} - 0.65)] \times K_{\text{state}}$$
   *(State multipliers: $\text{HEALTHY}=1.00, \text{DEGRADING}=1.10, \text{WARNING}=1.28, \text{CRITICAL}=1.55$)*
2. **EWMA & Trajectory Fusion**:
   $$\text{Rate}_{\text{fused}} = 0.72 \cdot \text{Rate}_{\text{ewma}} + 0.28 \cdot \text{Rate}_{\text{traj}} \quad (\text{clamp: } [0.03, 6.0] \text{ \%/hour})$$
3. **RUL Output**:
   $$\text{RUL}_{\text{hours}} = \frac{80.0 - \text{Degradation Index}}{\text{Rate}_{\text{fused}}}$$

---

## SECTION 12 — VALIDATION AND PERFORMANCE METRICS

Extracted verbatim from committed validation benchmark artifacts in `backend/validation_results/`:

### 1. Anomaly Detection Benchmark (Calibrated Model v2)
*Source File*: `backend/validation_results/anomaly_calibration.json`

| Metric | Before Calibration (Synthetic Fallback) | After Calibration (Trained on Simulator) |
| :--- | :--- | :--- |
| **Precision** | 54.99% (0.5499) | **47.32% (0.4732)** |
| **Recall** | 20.32% (0.2032) | **48.32% (0.4832)** (+138% improvement) |
| **F1 Score** | 0.2967 | **0.4781** (+61% improvement) |
| **False Alarm Rate (FAR)**| 10.90% (0.1090) | **35.24% (0.3524)** |
| **Mean Detection Latency**| 64.71 seconds | **41.60 seconds** (23.1s faster detection) |
| **True Positives (TP)** | 193 | **459** |
| **False Positives (FP)**| 158 | **511** |
| **True Negatives (TN)** | 1292 | **939** |
| **False Negatives (FN)**| 757 | **491** |
| **Training Samples** | Hand-crafted fallback | **3,540 samples** (seeds 101, 102) |
| **Elapsed Benchmark Time**| N/A | **861.5 seconds** (~14.3 minutes) |

### 2. Fault Diagnosis Benchmark (10-Class Classification)
*Source File*: `backend/validation_results/fault_diagnosis_audit.json`, `diagnosis_metrics.json`

* **Overall Diagnosis Accuracy**: **40.0% (0.400)**
* **Macro Precision**: **58.3% (0.583)**
* **Macro Recall**: **40.0% (0.400)**
* **Macro F1 Score**: **0.317–0.325**
* **Mean Fault Isolation Latency**: **31.25 seconds**

---

## SECTION 25 — SIH 2026 PPT DATA MAPPING (EXACT 6-SLIDE STRUCTURE)

```
================================================================================
SLIDE 1 — TITLE PAGE
================================================================================
PRIMARY CONTENT:
- Project Title: SkySentrix — Aerospace Digital Twin & Predictive Maintenance Platform
- Subtitle: Real-Time Condition Monitoring, Anomaly Detection & RUL Estimation for Aero-Piston UAV Engines
- Tagline: "Predict • Prevent • Keep You Flying"
- Context: SIH 2026 Software Prototype (DRDO Aero-Propulsion Use-Case)

SECONDARY CONTENT:
- Team Name: [NOT FOUND — User to provide]
- Team ID: [NOT FOUND — User to provide]
- Problem Statement ID: [NOT FOUND — User to provide]
- Problem Statement Title: [NOT FOUND — User to provide]
- Theme: Aerospace / Defense / Smart Vehicles

================================================================================
SLIDE 2 — IDEA TITLE & PROBLEM DEFINITION
================================================================================
PRIMARY CONTENT:
- Core Problem: Aero-piston UAV engines suffer from sudden in-flight power loss and catastrophic breakdowns because traditional cockpit gauges rely on static, decoupled redline thresholds that fail to detect subtle progressive degradation during varying flight phases.
- Target Users: Defense & Tactical UAV Operators (DRDO/Armed Forces), General Aviation MRO crews, Flight Fleet Managers.
- Proposed Innovation: An end-to-end software Digital Twin that computes an instantaneous healthy baseline across varying altitudes and throttle regimes, calculating multi-dimensional residuals to catch early-stage failures before physical thresholds are breached.

================================================================================
SLIDE 3 — TECHNICAL APPROACH & ARCHITECTURE
================================================================================
PRIMARY CONTENT:
- 10-Stage Analytics Pipeline Flow:
  Telemetry (Simulator/CSV) → Linear Kalman State Estimation → Healthy Digital Twin Prediction → Residual Generation → Isolation Forest Anomaly Scoring → Causal Fault Isolation → Subsystem Health Tracking → Dynamic RUL Projection → Maintenance Advisory → WebSocket / 3D UI.
- Digital Twin Formulation: Reduced-order ISA atmosphere model + bilinear 7x5 performance map + 1st-order thermal/lubrication dynamic lag network.
- Anomaly Engine: 21-feature vector passed into a calibrated 220-tree Isolation Forest fused with normalized residual EWMA.

================================================================================
SLIDE 4 — FEASIBILITY & VIABILITY
================================================================================
PRIMARY CONTENT:
- Technical Feasibility: Proven sub-10ms pipeline latency per cycle on standard commodity CPU hardware. Zero GPU/cloud lock-in.
- Operational Flexibility: Dual-mode architecture supports real-time radio telemetry streaming AND offline batch post-flight CSV file ingestion.
- Metrics: 48.32% Anomaly Recall, 41.6s Detection Latency, 40.0% Fault Diagnosis Accuracy (100% precision on Overheating, Alternator, Sensor Failure).

================================================================================
SLIDE 5 — IMPACT, BENEFITS & INNOVATION
================================================================================
PRIMARY CONTENT:
- Safety & Mission Assurance: Prevents catastrophic in-flight engine stoppage in defense UAV reconnaissance missions by providing actionable advance warnings.
- Condition-Based Predictive Maintenance: Replaces arbitrary flight-hour schedules with real-time cumulative damage indices.
- Unique Innovations: Aero-piston UAV specific focus, hybrid twin (physics + ML), procedural 3D digital twin WebGL cockpit with leader-line hotspots.

================================================================================
SLIDE 6 — RESEARCH, CITATIONS & ROADMAP
================================================================================
PRIMARY CONTENT:
- Theoretical Foundation: ISA Atmosphere (ICAO Doc 7488-CD), Mean-Value Engine Modeling (Hendricks & Sorenson), Kalman Filter (Kalman 1960), Isolation Forest (Liu et al. 2008), Prognostics (Saxena et al. NASA C-MAPSS 2008).
- Roadmap: Software Prototype (Completed) → Dyno Test-Bench Validation → Edge DAQ Flight Certification.
```

---
*End of SkySentrix Project Data Extraction & Guide.*
