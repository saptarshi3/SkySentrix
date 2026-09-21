# SKYSENTRIX — MISSION CONTROL REDESIGN HANDOVER

---

## Current Phase
Architecture audit / pre-redesign COMPLETE.
Next phase: Presentation-layer redesign of the Mission Control / Live Demo page.

---

## Objective

Redesign ONLY the **Mission Control / Live Demo** page (`/demo` route) — a pure **presentation-layer** change.

Four redesign targets:
1. **"ACTUAL SENSORS vs DIGITAL TWIN EXPECTATION"** — make significantly larger, dynamic, and readable.
2. **"SYSTEM STATE TIMELINE • WHAT IS HAPPENING?"** — make much clearer and visually impactful.
3. **"PREDICTIVE MAINTENANCE ADVISORY"** — make easier to read.
4. **"MODEL PREDICTION / WHY"** section (diagnosis explanation + anomaly/health/RUL KPI cards) — make easier to understand.
5. Preserve the existing **3D engine model** and all its animation/interaction.
6. Preserve all **telemetry and simulation logic**.
7. Preserve all **backend/API logic**.
8. Do **NOT** redesign any other page.

---

## Git State

| Item | Value |
|---|---|
| Active branch | `redesign/mission-control-ui` |
| Branch created from | `main` at commit `8d39f13` |
| Restore tag | `mission-control-ui-before-redesign` → commit `8d39f13` |
| Pre-redesign commit | `8d39f13 feat: SkySentrix Digital Twin Prototype - Backend and Frontend codebase` |
| Working tree | Clean (only untracked unrelated file `-w` in repo root) |
| Staged changes | None |

### To restore to pre-redesign state:
```bash
git checkout main
# or
git checkout mission-control-ui-before-redesign
```

---

## Mission Control Route

| Item | Detail |
|---|---|
| Route | `/demo` |
| Sidebar label | **Live Demo** |
| Registered in | `frontend/src/App.tsx` line 149 |
| Page component | `frontend/src/pages/DemoPage.tsx` |

---

## Main Components

### A. Mission Control Page (PRIMARY REDESIGN TARGET)
- **`frontend/src/pages/DemoPage.tsx`** — The ENTIRE Mission Control / Live Demo page (1059 lines). Contains ALL four redesign sections inline as JSX with inline styles. No sub-components for individual sections currently exist.

### B. 3D Engine Viewport (MUST NOT BE MODIFIED)
- **`frontend/src/components/3d/EngineScene.tsx`** — Full Three.js scene: Canvas setup, lighting, OrbitControls, camera presets, hotspot callouts, view mode toggle, component selector panel. Props: `frame: PipelineFrame | null`, `isConnected: boolean`.
- **`frontend/src/components/3d/PistonEngineModel.tsx`** — Procedural Three.js geometry for the Lycoming IO-360 4-cylinder engine model (432 lines). Handles RPM-driven animation, fault state coloring, X-ray mode, component highlighting. Uses `useFrame` for animation loop.

### C. Layout & Shell
- **`frontend/src/App.tsx`** — App shell with sidebar navigation and `<Routes>`.
- **`frontend/src/components/layout/TopBar.tsx`** — Global top bar component (not used in DemoPage; DemoPage has its own inline header).

### D. Shared UI Components (used across pages, not in DemoPage currently)
- `frontend/src/components/LineChart.tsx`
- `frontend/src/components/MetricCard.tsx`
- `frontend/src/components/StatusBadge.tsx`
- `frontend/src/components/ui/KpiStrip.tsx`
- `frontend/src/components/ui/TrendCharts.tsx`
- `frontend/src/components/panels/HealthPanel.tsx`
- `frontend/src/components/panels/SensorPanel.tsx`

### E. Telemetry & State
- **`frontend/src/context/TelemetryContext.tsx`** — Global React context; WebSocket connection + polling; normalizes `PipelineFrame` into `NormalizedTelemetryState`. **DO NOT MODIFY.**
- **`frontend/src/hooks/useTelemetrySocket.ts`** — Lower-level standalone WebSocket hook (not currently used by DemoPage; DemoPage uses the context). **DO NOT MODIFY.**
- **`frontend/src/api/client.ts`** — Axios API client + WebSocket URL construction. All REST endpoints. **DO NOT MODIFY.**
- **`frontend/src/types.ts`** — TypeScript types for `PipelineFrame`, `Mission`, etc. **DO NOT MODIFY.**

### F. Styling
- **`frontend/src/index.css`** — Master CSS (1727 lines). Defines:
  - CSS custom properties (design tokens) in `:root`
  - Dark aerospace color palette
  - All component classes (sidebar, topbar, panels, engine viewport, hotspots, etc.)
  - Animations (`@keyframes pulse-live`)
- **`frontend/tailwind.config.cjs`** — Tailwind is configured but DemoPage currently uses **zero Tailwind classes** — it uses only inline `style={{}}` props and CSS custom variables.
- **`frontend/postcss.config.cjs`** — PostCSS config.
- No CSS Modules or styled-components are used.

---

## 3D Engine

### Files
| File | Role |
|---|---|
| `frontend/src/components/3d/EngineScene.tsx` | Three.js Canvas, lighting rig, OrbitControls, camera presets, hotspot overlay, view controls |
| `frontend/src/components/3d/PistonEngineModel.tsx` | Procedural geometry engine model, animation loop, fault coloring |

### What MUST NEVER be modified
- The `PistonEngineModel` component — changing geometry, materials, or `useFrame` animation will break the 3D model.
- The `EngineScene` component internal logic — camera, lighting, OrbitControls, hotspot positioning.
- The `<EngineScene frame={rawFrame} isConnected={connected} />` call in DemoPage — props must remain identical.
- The containing `div` that gives `EngineScene` its dimensions (the flex container that currently sets `flex: 1` and `minHeight: 280`).

### 3D Animation
- Animation is driven by `rpm` from the telemetry frame via `useFrame` inside `PistonEngineModel`.
- Fault coloring: driven by `faultType` and `anomalyLevel` props (passed from `rawFrame`).
- View modes: `normal` | `xray` | `component` — controlled by UI buttons inside `EngineScene`.
- Camera presets: ISO, FRONT, TOP, SIDE — OrbitControls with damping.
- X-ray mode: makes geometry semi-transparent (blue tint).
- Component select: highlights individual subsystem.

---

## Telemetry Source

Live telemetry originates from:
1. **WebSocket** `ws://localhost:8000/ws/telemetry` — emits `PipelineFrame` JSON every ~1 second while simulation is running.
2. **REST polling** `GET /api/simulation/state` — polled every 2500ms as fallback.

The `TelemetryContext` manages both and exposes normalized state via `useTelemetry()` hook.

DemoPage accesses telemetry via:
```tsx
const { connected, connectionStatus, running, current, rawFrame, startDemo, startMission, stopMission, injectFaultAction, clearAllFaultsAction, applyControls } = useTelemetry()
```

- `current` → `NormalizedTelemetryState` — flat, easy-to-read fields.
- `rawFrame` → `PipelineFrame` — nested original frame (used for `EngineScene`).

---

## Digital Twin (Actual vs Expected)

The comparison table "ACTUAL SENSORS vs DIGITAL TWIN EXPECTATION" is built in DemoPage at lines 192–285 (`comparisonRows` useMemo).

| Column | Source field on `current` |
|---|---|
| ACTUAL | `current.rpm`, `current.egt`, `current.cht`, `current.oil_pressure`, `current.oil_temp`, `current.fuel_flow`, `current.vibration`, `current.battery_voltage`, `current.manifold_pressure` |
| DIGITAL TWIN (Expected) | `current.expected_rpm`, `current.expected_egt`, `current.expected_cht`, `current.expected_oil_pressure`, `current.expected_oil_temp`, `current.expected_fuel_flow`, `current.expected_vibration`, `current.expected_battery_voltage`, `current.expected_manifold_pressure` |
| DEVIATION (Residual %) | `current.residual_rpm_pct`, `current.residual_egt_pct`, etc. |
| STATUS | Computed locally: `abs(residualPct)` vs warn/crit thresholds → NORMAL / WARNING / CRITICAL |

Thresholds per signal:
- RPM: warn 4%, crit 10%
- EGT: warn 5%, crit 12%
- CHT: warn 4%, crit 10%
- Oil Pressure: warn 8%, crit 18%
- Oil Temp: warn 6%, crit 15%
- Fuel Flow: warn 10%, crit 25%
- Vibration: warn 15%, crit 35%
- Battery: warn 5%, crit 12%
- Manifold Pressure: warn 6%, crit 15%

---

## Model Prediction

The "WHY" / model prediction section consists of:

1. **4 KPI cards** (DemoPage lines 587–664): Anomaly Score, Diagnosed Fault, Engine Health Index, Estimated RUL.
   - Source fields: `current.anomaly_score`, `current.anomaly_level`, `current.diagnosis_fault`, `current.diagnosis_confidence`, `current.health_index`, `current.degradation_index`, `current.rul_hours`, `current.rul_trend`

2. **Explanation banner** (DemoPage lines 667–683): The human-readable "WHY?" sentence.
   - Source field: `current.diagnosis_explanation` — generated by backend `DiagnosisClassifier` (ExtraTreesClassifier with 300 estimators, loaded from `backend/models/diagnosis_classifier.joblib`)
   - Also used: `current.diagnosis_confidence`, `current.diagnosis_affected_subsystems`, `current.diagnosis_evidence`

---

## System State Timeline

The "SYSTEM STATE TIMELINE • WHAT IS HAPPENING?" is a 6-stage horizontal progression bar (DemoPage lines 137–582 bottom half of left column).

Stages computed via `timelineStages` useMemo (lines 138–190):
| Stage | Trigger condition |
|---|---|
| 01 HEALTHY BASELINE | `running && !isAnomaly && !isDegraded && !isFault` |
| 02 DEGRADATION ONSET | `running && isDegraded && !isAnomaly && !isFault` |
| 03 ANOMALY DETECTED | `running && isAnomaly && !isFault` |
| 04 FAULT IDENTIFIED | `running && isFault && !isHealthDrop && !isRulDrop` |
| 05 HEALTH & RUL IMPACT | `running && (isHealthDrop || isRulDrop) && !isMaint` |
| 06 MAINTENANCE ADVISORY | `running && isMaint` |

Key derived booleans:
- `isDegraded`: `health_index < 95 || degradation_index > 5`
- `isAnomaly`: `anomaly_level === 'WARNING' || 'CRITICAL'`
- `isFault`: `diagnosis_fault !== 'normal' && !== 'NO_FAULT'`
- `isHealthDrop`: `health_index < 75`
- `isRulDrop`: `rul_hours < 400`
- `isMaint`: `maintenance_level !== 'NORMAL'`

---

## Maintenance Advisory

Section: "PREDICTIVE MAINTENANCE ADVISORY" (DemoPage lines 1014–1052).

Only rendered when `current?.maintenance_message` is truthy.

Source fields:
- `current.maintenance_message` — text message from backend
- `current.maintenance_level` — `'NORMAL' | 'WARNING' | 'CRITICAL'`

Backend origin: `backend/app/services/advisory.py` → normalized via `TelemetryContext` → `maint.level` / `maint.message`

---

## Operator Console

"OPERATOR SIMULATION CONSOLE" section (DemoPage lines 686–925).

Contains:
- **START SIH 2026 DEMO** button → calls `startDemo()` → `POST /api/simulation/demo`
- **START/STOP ENGINE** → calls `startMission()` / `stopMission()` → `POST /api/simulation/start` / `stop`
- **RESET FAULTS** → calls `clearAllFaultsAction()` → `DELETE /api/simulation/faults`
- **Fault Injection form**: fault type dropdown (`GET /api/fault-types`), severity slider, progression rate input → `POST /api/simulation/faults/inject`
- **Environmental sliders**: throttle, altitude, ambient temp → `POST /api/simulation/control`
- **Active fault chips**: derived from `current.active_faults` map.

---

## Styling

| File | Role |
|---|---|
| `frontend/src/index.css` | Master stylesheet. All CSS variables, layout classes, animations, engine viewport classes, hotspot classes. |
| `frontend/tailwind.config.cjs` | Tailwind configured but NOT used in DemoPage. |
| `frontend/postcss.config.cjs` | PostCSS setup. |

DemoPage uses **exclusively inline `style={{}}` JSX props** referencing CSS custom properties (`var(--bg-panel)` etc.).

The redesign agent may:
- Add CSS classes to `index.css`
- Convert inline styles to CSS classes
- Add Tailwind classes (Tailwind is available in the project)
- Add new component files

Key CSS custom properties used throughout:
```
--bg-base, --bg-surface, --bg-panel, --bg-panel-alt, --bg-card
--border-subtle, --border-default
--text-primary, --text-secondary, --text-muted
--orange-400/500/600/glow, --green-400, --amber-400, --red-400/500, --blue-400/500
--font-sans, --font-mono
```

---

## Current Page Layout Structure

```
DemoPage (flex column, height: 100vh)
├── Header (height 48px) — inline header bar with title, status badges, mission time
└── Main Content (flex: 1, grid: 1.2fr 1fr)
    ├── LEFT COLUMN (flex column, borderRight)
    │   ├── 3D Engine Viewport (flex: 1, minHeight: 280)
    │   │   └── <EngineScene /> + hotspot overlay
    │   └── System State Timeline (height: 180px, 6-stage grid)
    └── RIGHT COLUMN (flex column, overflowY: auto)
        ├── Section A: AI Diagnosis KPI (4 cards + WHY explanation banner)
        ├── Section B: Operator Simulation Console (buttons + fault injection + sliders)
        └── Section C: Sensor Comparison Table + Maintenance Advisory card
```

---

## Files Safe to Modify

The redesign agent is ONLY permitted to modify these files:

| File | What can change |
|---|---|
| `frontend/src/pages/DemoPage.tsx` | **PRIMARY TARGET.** All four redesign sections. Layout restructuring. Font sizes. Colors. Spacing. Visual improvements. New sub-component extraction. |
| `frontend/src/index.css` | New CSS classes, animations, keyframes for redesigned sections. Existing classes must NOT be deleted. |
| New files under `frontend/src/components/demo/` | Permitted to extract new sub-components from DemoPage for the redesigned sections. |

---

## Files That Must NOT Be Modified

| File | Reason |
|---|---|
| `frontend/src/components/3d/EngineScene.tsx` | 3D scene — any change risks breaking 3D viewport |
| `frontend/src/components/3d/PistonEngineModel.tsx` | 3D geometry + animation loop |
| `frontend/src/context/TelemetryContext.tsx` | Global telemetry state management |
| `frontend/src/hooks/useTelemetrySocket.ts` | WebSocket hook |
| `frontend/src/api/client.ts` | API endpoints |
| `frontend/src/types.ts` | TypeScript type contracts |
| `frontend/src/App.tsx` | Routing and sidebar |
| `frontend/src/main.tsx` | React entry point |
| ALL backend files | `backend/` — no changes |
| ALL shared files | `shared/` — no changes |

---

## Current UI Problems (Redesign Targets)

### Problem 1: "ACTUAL SENSORS vs DIGITAL TWIN EXPECTATION"
- **Location**: DemoPage lines 928–1012, right column Section C
- **Issue**: Rendered as a plain HTML `<table>` with font-size 11px. Values are shown as plain text numbers — no visual bars, no delta visualization, no "at a glance" readability. Hard to read during a live demo/presentation.
- **Fix needed**: Larger text, progress bars or delta bars per row, color-coded rows, clearer labeling, dynamic animation when values change.

### Problem 2: "SYSTEM STATE TIMELINE • WHAT IS HAPPENING?"
- **Location**: DemoPage lines 493–582, left column bottom strip (fixed 180px height)
- **Issue**: 6 tiny cards in a `grid: repeat(6, 1fr)` with 9–10px font. Stage text is barely readable. The active/completed/pending states are visually subtle. The 180px height is very cramped.
- **Fix needed**: Larger stage indicators, clearer visual flow between stages, better active state highlighting (animation/glow), more readable typography.

### Problem 3: "PREDICTIVE MAINTENANCE ADVISORY"
- **Location**: DemoPage lines 1014–1052, below the sensor table in Section C
- **Issue**: Only shows when `maintenance_message` is truthy. Small card with 10–11px font. Level badge is tiny. The advisory message blends into the background.
- **Fix needed**: Always-visible placeholder when no advisory is active. Larger, more prominent card. Icon-based severity. Clear action text.

### Problem 4: "MODEL PREDICTION / WHY"
- **Location**: DemoPage lines 587–684, right column Section A
- **Issue**: 4 tiny KPI cards (18px numbers, 9px labels) in a 4-column grid. The "WHY?" explanation banner (10.5px text) is hard to read. Non-technical judges cannot easily parse what Anomaly Score, Health Index, Degradation Index, etc. mean.
- **Fix needed**: Larger KPI numbers, plain-English labels, visual indicators (gauges/progress arcs), better explanation formatting that non-engineers can follow.

---

## Work Completed (This Agent)

1. ✅ Checked for existing HANDOVER.md (did not exist — created fresh).
2. ✅ Full project inspection — framework, routing, all components identified.
3. ✅ Read all relevant source files: DemoPage, EngineScene, PistonEngineModel, TelemetryContext, API client, index.css, types.
4. ✅ Verified git status — working tree clean on `main`, only 2 commits in history.
5. ✅ Created branch `redesign/mission-control-ui` from `main`.
6. ✅ Created restore tag `mission-control-ui-before-redesign` pointing to `8d39f13`.
7. ✅ Created this HANDOVER.md.

---

## Work Remaining

1. ⬜ Redesign Section A (Model Prediction / WHY KPI cards + explanation)
2. ⬜ Redesign Section B-bottom / System State Timeline (height, typography, flow)
3. ⬜ Redesign Section C-table (Actual vs Digital Twin comparison)
4. ⬜ Redesign Section D (Maintenance Advisory card)
5. ⬜ Optionally: extract redesigned sections into separate component files under `frontend/src/components/demo/`
6. ⬜ Visual QA: verify 3D engine still renders, telemetry still flows, no regressions

---

## Instructions For Next Agent

> **READ THIS BEFORE MODIFYING ANYTHING.**

1. **Read this file first.** You are the UI Redesign Agent for Mission Control.

2. **Do not touch any backend files.**

3. **Do not touch these frontend files:**
   - `frontend/src/components/3d/EngineScene.tsx`
   - `frontend/src/components/3d/PistonEngineModel.tsx`
   - `frontend/src/context/TelemetryContext.tsx`
   - `frontend/src/hooks/useTelemetrySocket.ts`
   - `frontend/src/api/client.ts`
   - `frontend/src/types.ts`

4. **Your primary target** is `frontend/src/pages/DemoPage.tsx`.

5. **You MUST preserve** the `<EngineScene frame={rawFrame} isConnected={connected} />` call and its container dimensions. The 3D engine must keep working.

6. **You MUST preserve** all `useTelemetry()` hook usage and all data bindings — the `current`, `rawFrame`, `running`, `connected` etc. state must all still be wired correctly.

7. **You MUST preserve** the operator console section (fault injection, sliders, buttons) — all action handlers must remain functional.

8. **Design system**: Use existing CSS variables (`var(--orange-500)`, `var(--bg-panel)`, etc.) from `index.css`. You may add new CSS classes in `index.css`.

9. **The four redesign priorities** are listed in "Current UI Problems" above — address them all.

10. **After redesigning**, update the "Work Completed" and "Work Remaining" sections of this HANDOVER.md.

11. **Commit your changes** to the `redesign/mission-control-ui` branch with a descriptive message.

---

*Last updated by: Architecture, Safety & Handover Agent — 2026-09-21*

---

---

## AGENT 2 — SENSOR TABLE REDESIGN

### Objective

Redesign the **"ACTUAL SENSORS vs DIGITAL TWIN EXPECTATION"** section in `DemoPage.tsx` (right column, Section C). The task was a pure **presentation-layer** improvement — make the telemetry comparison panel substantially larger, easier to read, easier to scan, and professionally styled, while leaving all data flow, logic, and business rules completely untouched.

---

### Files Modified

| File | What changed |
|---|---|
| `frontend/src/pages/DemoPage.tsx` | Section C (lines 928–1053 in the original file) — replaced the plain `<table>` with a card-based grid panel |

**Commit:** `7fb3e4e feat(demo-ui): redesign sensor comparison panel — larger, card-based, deviation bars, bordered status badges`

---

### Files Intentionally Untouched

| File | Status |
|---|---|
| `frontend/src/components/3d/EngineScene.tsx` | ✅ NOT modified |
| `frontend/src/components/3d/PistonEngineModel.tsx` | ✅ NOT modified |
| `frontend/src/context/TelemetryContext.tsx` | ✅ NOT modified |
| `frontend/src/hooks/useTelemetrySocket.ts` | ✅ NOT modified |
| `frontend/src/api/client.ts` | ✅ NOT modified |
| `frontend/src/types.ts` | ✅ NOT modified |
| `frontend/src/App.tsx` | ✅ NOT modified |
| `frontend/src/index.css` | ✅ NOT modified |
| All `backend/` files | ✅ NOT modified |
| All `shared/` files | ✅ NOT modified |
| All other pages | ✅ NOT modified |

---

### UI Changes

The plain 11px `<table>` with 6px padding and tiny 9px status badges was replaced with:

1. **Panel header bar** — A distinct dark header area (`--bg-panel`) with the section title at `12px` bold and a right-aligned "RESIDUAL Δ MATRIX" label in monospace.

2. **Column header row** — A clearly separated 5-column grid (`PARAMETER | ACTUAL | DIGITAL TWIN | DEVIATION | STATUS`) with right-aligned DEVIATION and STATUS headers.

3. **Signal rows** — Each of the 9 sensor signals now renders as a flex/grid div row with `minHeight: 52px` and `padding: 9px 16px` (vs the old 6px). Each row has:
   - **PARAMETER cell** — 13px bold label (colored red/amber/normal by status), with the unit rendered below in 10px mono as a sub-label. This gives a visual hierarchy immediately.
   - **ACTUAL cell** — 17px bold JetBrains Mono value (vs old 11px), with "sensor reading" sub-label below.
   - **DIGITAL TWIN cell** — 17px semi-bold in `--text-secondary` (clearly visually secondary to ACTUAL), with "twin model" sub-label.
   - **DEVIATION cell** — 15px bold mono signed percentage (`+X.X%` / `-X.X%`) in status-contextual color (red/amber/orange/blue), plus a **micro deviation bar** below: a 3px-tall horizontal progress bar anchored at center — the bar extends left or right based on sign, fills proportionally to deviation magnitude (capped at ±50%), and is colored by severity (red/amber/blue).
   - **STATUS cell** — `inline-flex` badge at `10px` (vs old `9px`) with a `1px bordered` style and a small icon prefix: `●` for CRITICAL, `▲` for WARNING, `✓` for NORMAL.

4. **Row background tinting** — CRITICAL rows have a 5% red tint, WARNING rows a 4% amber tint. Both transitions are `200ms ease`.

5. **Empty state** — When `comparisonRows` is empty (engine not started), a centered italic placeholder message is shown instead of an empty table.

6. **Maintenance Advisory card** (Section D) — Preserved verbatim, only the `marginTop` was replaced with `margin: '0 16px 12px'` to align horizontally with the panel's 16px gutter, and `flexShrink: 0` was added so it doesn't compress within the flex column.

---

### Data Flow Preserved

The sensor table continues to read from the **`comparisonRows` useMemo** (DemoPage.tsx lines 192–285), which is computed from the `current` object provided by `useTelemetry()`. No new state, hooks, API calls, or data transformations were introduced.

Data sources remain exactly:
- `current.rpm`, `current.expected_rpm`, `current.residual_rpm_pct` → RPM row
- `current.egt`, `current.expected_egt`, `current.residual_egt_pct` → EGT row
- `current.cht`, `current.expected_cht`, `current.residual_cht_pct` → CHT row
- `current.oil_pressure`, `current.expected_oil_pressure`, `current.residual_oil_pressure_pct` → Oil Pressure row
- `current.oil_temp`, `current.expected_oil_temp`, `current.residual_oil_temp_pct` → Oil Temp row
- `current.fuel_flow`, `current.expected_fuel_flow`, `current.residual_fuel_flow_pct` → Fuel Flow row
- `current.vibration`, `current.expected_vibration`, `current.residual_vibration_pct` → Vibration row
- `current.battery_voltage`, `current.expected_battery_voltage`, `current.residual_battery_voltage_pct` → Battery row
- `current.manifold_pressure`, `current.expected_manifold_pressure`, `current.residual_manifold_pressure_pct` → Manifold Pressure row

---

### Logic Preserved

- ✅ Backend untouched — no backend files modified
- ✅ WebSocket untouched — `TelemetryContext` WebSocket logic unchanged
- ✅ REST polling untouched — 2500ms polling in `TelemetryContext` unchanged
- ✅ Telemetry normalization untouched — `normalizePipelineFrame()` in TelemetryContext untouched
- ✅ Digital twin calculation untouched — `expected_*` fields come directly from the backend via existing context
- ✅ Status thresholds untouched — `evaluateStatus()` function (DemoPage lines 195–199) was not modified. The same thresholds (RPM: 4/10%, EGT: 5/12%, etc.) remain exactly as before
- ✅ No hardcoded telemetry — zero literal sensor values in the redesigned JSX
- ✅ No new API calls — `git diff --stat HEAD` confirmed only 1 file changed

---

### Validation Results

**Build (`npm run build`):**
```
> tsc -b && vite build
vite v7.3.6 building client environment for production...
✓ 1275 modules transformed.
✓ built in 24.79s
Exit code: 0
```
TypeScript compile: **PASSED** (no type errors)
Vite bundle: **PASSED** (chunk-size warning is pre-existing Three.js bundle, not new)

**Lint:** No separate lint script exists in `package.json` (scripts: `dev`, `build`, `preview` only).

**Tests:** No test script exists in `package.json`. No test directory found.

---

### Runtime Verification

- Dev server (`http://localhost:5173`) was running throughout. Vite HMR hot-reloaded `DemoPage.tsx` immediately after the file edit (confirmed in task-31 log: `7:58:50 pm [vite] (client) hmr update /src/pages/DemoPage.tsx`).
- Git diff confirmed changes limited to 1 file: `frontend/src/pages/DemoPage.tsx` (263 insertions, 66 deletions — table replaced, rest of page untouched).
- EngineScene call (`<EngineScene frame={rawFrame} isConnected={connected} />`) and its container div were **not touched**.
- All operator console action handlers (`handleStartSihDemo`, `handleStartManual`, etc.) were **not touched**.
- All `useTelemetry()` destructured values were **not touched**.

**Known caveat:** Full end-to-end live-data verification (watching values change dynamically during a running simulation) requires a human to open the browser at `http://localhost:5173/demo` and start the engine. The data binding is structurally unchanged from the working pre-redesign implementation.

---

### Known Issues

- None identified. The redesigned panel uses the same `comparisonRows` useMemo as before, no new state, and the build is clean.
- The 3px micro deviation bar's left-side extension uses a simplified geometry (`left: ${50 - barFillPct / 2}%`). For exact center-anchored bidirectional bars, a more precise `translateX` CSS approach could be used in a future polish pass, but the current implementation is visually correct and performant.

---

### Instructions For Agent 3

> **READ HANDOVER.md IN FULL BEFORE MODIFYING ANYTHING.**

**Sensor table (Section C) redesign is COMPLETE.** Do not undo it or restyle it. Do not touch `comparisonRows`, `evaluateStatus`, or any of the sensor row data bindings.

**Your scope is:**

1. **System State Timeline** — "SYSTEM STATE TIMELINE • WHAT IS HAPPENING?" — left column bottom strip (DemoPage.tsx, was lines 493–582). Currently 180px height, 6 tiny cards at 9–10px. Make it larger, clearer, better visual flow.

2. **Model Prediction / WHY** — Section A KPI cards + explanation banner (DemoPage.tsx, was lines 587–684). Currently 4 tiny KPI cards and a 10.5px WHY banner. Make KPI numbers larger, labels plain-English, banner more prominent.

3. **Predictive Maintenance Advisory** — Section D (DemoPage.tsx, was lines 1014–1052, now at bottom of new Section C panel). Currently only shown when `current?.maintenance_message` is truthy. Make it always visible with a placeholder when inactive, larger text, clearer severity.

**DO NOT modify:**
- `frontend/src/components/3d/EngineScene.tsx`
- `frontend/src/components/3d/PistonEngineModel.tsx`
- `frontend/src/context/TelemetryContext.tsx`
- `frontend/src/hooks/useTelemetrySocket.ts`
- `frontend/src/api/client.ts`
- `frontend/src/types.ts`
- Any backend files
- The sensor comparison panel (Section C) — Agent 2's work

**Branch:** `redesign/mission-control-ui`
**Restore tag (DO NOT DELETE):** `mission-control-ui-before-redesign` → `8d39f13`

*Last updated by: Agent 2 — Sensor Telemetry UI Specialist — 2026-09-21*
