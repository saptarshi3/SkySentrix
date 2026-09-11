# SkySentrix — SIH 2026 DRDO Digital Twin Prototype

> **Scope**: software-only, synthetic digital twin prototype for an aero-piston UAV engine use-case.
> 
> **Important**: This project does **not** use real DRDO engine telemetry and is **not** aerospace-certified.

---

## 1) Current Architecture (Implemented)

```text
Simulator / CSV
  -> Sensor Preprocess
  -> State Estimator (Kalman)
  -> Healthy Digital Twin Prediction
  -> Residual Engine
  -> Isolation Forest + Residual Scoring
  -> Fault Diagnosis
  -> Health / Degradation Tracking
  -> RUL Estimation
  -> Maintenance Advisory
  -> SQLite Persistence
  -> WebSocket / REST
  -> Frontend Dashboard + Replay
```

The implementation separates:
1. **True engine state** (`EngineTrueState`)  
2. **Observed sensor telemetry** (`SensorModel`)  
3. **Estimated state** (`StateEstimator`)  
4. **Healthy expected state** (`DigitalTwinModel`)  

---

## 2) Project Structure

```text
SkySentrix/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── engine/
│   │   │   ├── simulator.py
│   │   │   ├── twin.py
│   │   │   ├── faults.py
│   │   │   ├── environment.py
│   │   │   ├── performance_map.py
│   │   │   ├── manifold.py
│   │   │   ├── airflow.py
│   │   │   ├── combustion.py
│   │   │   ├── thermal.py
│   │   │   ├── lubrication.py
│   │   │   ├── electrical.py
│   │   │   ├── propeller.py
│   │   │   ├── sensor_model.py
│   │   │   ├── degradation.py
│   │   │   ├── state.py
│   │   │   └── state_estimator.py
│   │   ├── analytics/
│   │   │   ├── anomaly.py
│   │   │   ├── diagnosis.py
│   │   │   ├── health.py
│   │   │   └── rul.py
│   │   ├── services/
│   │   │   ├── pipeline.py
│   │   │   ├── realtime.py
│   │   │   ├── csv_ingest.py
│   │   │   ├── validation.py
│   │   │   └── advisory.py
│   │   ├── db/
│   │   │   ├── database.py
│   │   │   ├── models.py
│   │   │   └── crud.py
│   │   └── models/schemas.py
│   ├── requirements.txt
│   └── smoke_test.py
├── frontend/
│   └── src/
│       ├── pages/
│       ├── components/
│       ├── api/client.ts
│       └── types.ts
└── README.md
```

---

## 3) Engine Model Summary

`EngineSimulator` executes a coupled reduced-order chain:

```text
Mission profile -> throttle/load/altitude/temp/airspeed
-> environment (pressure, density)
-> manifold pressure
-> air mass flow
-> combustion (fuel/efficiency/torque/EGT base)
-> mechanical response (RPM/torque/power)
-> thermal path (EGT -> CHT -> oil temp)
-> lubrication (oil pressure + friction heat feedback)
-> electrical (alternator + battery)
-> subsystem degradation update
-> sensor observation (noise/bias/drift/failure)
```

### Key implemented relationships
- `density_ratio = (pressure_kpa / 101.325) * (288.15 / T_K)` (in `environment.py`)
- `manifold_pressure = f(throttle, rpm, ambient pressure, load, intake health)`
- `air_mass_flow = f(rpm, manifold pressure, density, throttle, combustion health)`
- `fuel/torque/egt_base = f(airflow, timing, perf-map sample, subsystem health, fault multipliers)`
- `power_kw = torque_nm * rpm / 9550`
- Thermal coupling: `combustion -> EGT -> CHT -> oil_temp` with different time constants
- `oil_pressure = f(rpm, oil_temp, lubrication health, lubrication fault multiplier)`
- `battery_voltage = f(rpm, alternator_health, electrical load)`

---

## 4) Digital Twin + Residuals

`DigitalTwinModel` is intentionally independent from simulator internals and predicts healthy expected values using:
- operating context (throttle/load/altitude/ambient)
- environment model
- performance map
- estimator-smoothed states

Residuals are computed as:
- `residual = estimated - expected`
- `residual_pct = residual / max(abs(expected), 1e-4) * 100`

---

## 5) Faults and Sensor Effects

`FaultManager` supports causal influences for:
- `injector_degradation`
- `misfire`
- `lubrication_problem`
- `overheating`
- `excessive_vibration`
- `combustion_instability`
- `fuel_system_degradation`
- `alternator_problem`

Sensor faults remain separate overlays:
- `sensor_drift` (progressive offset)
- `sensor_failure` (stuck/fail value)

---

## 6) Health and RUL

### Health (`analytics/health.py`)
Health is persistent and combines:
- residual persistence,
- anomaly score,
- diagnosis confidence,
- subsystem-health penalties,
- thermal/oil/mechanical abnormality indicators.

Outputs:
- `health_index`
- `degradation_index`
- `degradation_rate_per_hour`
- subsystem health breakdown
- `state`: `HEALTHY | DEGRADING | WARNING | CRITICAL`

### RUL (`analytics/rul.py`)
Sequential synthetic estimator using:
- degradation trajectory history,
- EWMA wear-rate,
- trend slope fusion,
- anomaly/diagnosis/state acceleration,
- confidence interval from recent rate variability.

Outputs:
- `current_rul_hours`
- `trend`
- `confidence_low_hours`, `confidence_high_hours`
- explicit synthetic-data warning note

---

## 7) Database

SQLite file: `backend/skysentrix.db`

Tables include:
- `missions`
- `telemetry`
- `fault_events`
- `anomaly_events`
- `health_history`
- `rul_predictions`
- `maintenance_events`
- `engine_passports` (engine history / cumulative hours / degradation trend)

`crud.init_db()` includes lightweight additive migration for schema evolution.

---

## 8) Run Instructions

### Backend
```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Optional:
```bash
VITE_API_URL=http://localhost:8000 npm run dev
```

---

## 9) Smoke Test

```bash
cd backend
./.venv2/bin/python smoke_test.py
```

Covers:
- API health
- simulation start/stop
- WebSocket stream
- fault injection response
- twin residual consistency
- DB writes
- replay endpoint
- CSV ingestion
- validation endpoint

---

## 10) Validation Notes

Validation metrics are generated from synthetic trajectories and synthetic labels.
They are useful for regression and relative comparison, **not** for certification claims.

---

## 11) Limitations (Explicit)

- No real engine dataset in this prototype
- No airworthiness certification
- No hardware ECU/FADEC/HIL integration
- Model parameters/maps are synthetic/parametric assumptions
- RUL is prototype-grade and not field-validated
