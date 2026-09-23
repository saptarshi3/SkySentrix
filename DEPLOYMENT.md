# SkySentrix Deployment Guide

This guide details the complete production deployment procedure for the **SkySentrix Aerospace / UAV Digital Twin Prototype**, configured for a public demonstration (e.g., SIH Judges evaluation).

---

## 1. Architecture

```text
               USER / SIH JUDGE BROWSER
                          │
                          ▼
            Vercel Frontend (SPA - React + Vite)
            https://<project-name>.vercel.app
                 │                    │
    HTTPS REST   │                    │  WSS WebSocket
    (API calls)  │                    │  (Real-Time Telemetry)
                 ▼                    ▼
            Render Backend Service (FastAPI + Uvicorn)
            https://<service-name>.onrender.com
                          │
          ┌───────────────┴───────────────┐
          ▼                               ▼
    Physics/ML Pipeline             SQLite Database
  (Lycoming IO-360 Twin)           (skysentrix.db)
```

---

## 2. Repository Structure

The repository contains both frontend and backend in a monorepo structure:

```text
SkySentrix/
├── backend/
│   ├── app/
│   │   ├── analytics/        # ML models (Anomaly, Diagnosis, Health, RUL)
│   │   ├── db/               # SQLite database setup and SQLAlchemy CRUD
│   │   ├── engine/           # Aero-piston physics simulator & twin models
│   │   ├── models/           # Pydantic schemas
│   │   ├── services/         # Realtime engine, telemetry pipeline, advisory
│   │   ├── config.py         # Mission presets & engine telemetry parameters
│   │   └── main.py           # FastAPI application entry point, CORS, /health
│   ├── models/               # Pre-trained ML classifiers (.joblib & metadata)
│   ├── .env.example          # Backend environment variable template
│   └── requirements.txt      # Python runtime dependencies
├── frontend/
│   ├── src/
│   │   ├── api/client.ts     # Axios REST client & dynamic WebSocket URL
│   │   ├── components/3d/    # Three.js 3D Lycoming IO-360 digital twin viewport
│   │   ├── context/          # TelemetryContext (WebSocket & state management)
│   │   ├── pages/            # Mission Control (/demo), Dashboard, Settings, etc.
│   │   ├── App.tsx           # React router routes & app shell
│   │   └── main.tsx          # React DOM entry point
│   ├── .env.example          # Frontend environment variable template
│   ├── package.json          # Frontend scripts & dependencies
│   ├── vercel.json           # SPA route rewrites for Vercel
│   └── vite.config.ts        # Vite configuration
├── render.yaml               # Render Infrastructure-as-Code Blueprint
├── DEPLOYMENT.md             # This deployment guide
└── HANDOVER.md               # Engineering agent log & handover state
```

---

## 3. Backend Deployment (Render)

### Service Configuration
- **Platform**: Render (Web Service)
- **Root Directory**: `backend`
- **Environment**: `Python 3` (Python 3.11.9 recommended)
- **Build Command**:
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command**:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```
- **Health Check Path**: `/health`
- **Auto-Deploy**: Yes (on push to `main`)

### Environment Variables on Render

| Variable | Recommended Demo Value | Description |
|---|---|---|
| `PORT` | *(Provided by Render automatically)* | Web server port |
| `HOST` | `0.0.0.0` | Bind address |
| `CORS_ALLOW_ALL` | `true` *(or set `CORS_ORIGINS`)* | Enables frontend cross-origin requests |
| `CORS_ORIGINS` | `https://<your-app>.vercel.app,http://localhost:5173` | Specific allowed origins (if CORS_ALLOW_ALL is false) |
| `PYTHON_VERSION` | `3.11.9` | Pinned Python runtime version |

---

## 4. Frontend Deployment (Vercel)

### Project Configuration
- **Framework Preset**: `Vite`
- **Root Directory**: `frontend` *(Critical: set to `frontend` in Project Settings)*
- **Build Command**: `npm run build` (or `tsc -b && vite build`)
- **Output Directory**: `dist`
- **Install Command**: `npm install`

### SPA Route Rewrites (`frontend/vercel.json`)
The repository includes `frontend/vercel.json` configured with:
```json
{
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```
This ensures refreshing or directly navigating to nested routes (e.g. `/demo`, `/analytics`, `/history`, `/settings`) returns `index.html` rather than a 404 error.

### Environment Variables on Vercel

| Variable | Example Value | Description |
|---|---|---|
| `VITE_API_URL` | `https://skysentrix-backend.onrender.com` | Base URL of deployed Render backend without trailing slash |
| `VITE_WS_URL` | *(Optional)* `wss://skysentrix-backend.onrender.com/ws/telemetry` | WebSocket URL. If omitted, client.ts automatically derives `wss://.../ws/telemetry` from `VITE_API_URL`. |

---

## 5. CORS Configuration

The backend CORS middleware is configured dynamically in `backend/app/main.py`:
- Reads `CORS_ORIGINS` or `ALLOWED_ORIGINS` (comma-separated list of origins).
- If `CORS_ALLOW_ALL=true`, it allows all origins (`*`) with `allow_credentials=False` to strictly comply with CORS specifications.
- Defaults to `http://localhost:5173`, `http://127.0.0.1:5173`, and `http://localhost:3000` for local development.

---

## 6. WebSocket Protocol

- **Endpoint**: `/ws/telemetry`
- **Local Dev**: `ws://localhost:8000/ws/telemetry`
- **Production**: `wss://<your-render-app>.onrender.com/ws/telemetry`
- `frontend/src/api/client.ts` automatically converts `https://` to `wss://` based on `VITE_API_URL`, ensuring secure WebSocket connections over SSL when served on HTTPS.

---

## 7. SQLite Behavior & Persistence

- **Location**: `backend/skysentrix.db`
- **Initialization**: Automatic on startup via `crud.init_db()` in `backend/app/db/crud.py`.
- **Render Free Tier Limitation**: Free Render instances use an ephemeral filesystem. If the container sleeps after inactivity or restarts, local SQLite files reset to default state.
- **Suitability for Demo**: Fully sufficient for the SIH 2026 prototype evaluation because all simulations (telemetry streaming, 3D twin, anomaly injection, RUL tracking, and maintenance advisories) are generated dynamically in real-time.
- **Enterprise Upgrade**: For permanent multi-session historical storage, set `DATABASE_URL=postgresql://...` to connect a managed PostgreSQL instance without code changes.

---

## 8. Health Check Endpoints

- **Root Health Check**: `GET /health`  
  Returns:
  ```json
  {
    "status": "healthy",
    "service": "SkySentrix Backend",
    "version": "0.1.0"
  }
  ```
- **API Health Check**: `GET /api/health`  
  Returns service status and synthetic data note.

---

## 9. Step-by-Step Deployment Instructions

### A. Deploy Backend to Render

1. Log in to [Render](https://dashboard.render.com/).
2. Click **New +** -> **Web Service**.
3. Connect your Git repository (`SkySentrix`).
4. Configure service parameters:
   - **Name**: `skysentrix-backend` (or your preferred name)
   - **Region**: Closest to your users (e.g., Singapore or Oregon)
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Under **Advanced** -> **Health Check Path**: set `/health`.
6. Add Environment Variables:
   - `CORS_ALLOW_ALL` = `true`
   - `PYTHON_VERSION` = `3.11.9`
7. Click **Create Web Service**.
8. Wait for deployment to complete. Copy your Render URL (e.g., `https://skysentrix-backend.onrender.com`).
9. Verify by opening `https://skysentrix-backend.onrender.com/health` in your browser. You should see `{"status":"healthy",...}`.

*(Alternatively, use Render Blueprints with the included `render.yaml` file).*

---

### B. Deploy Frontend to Vercel

1. Log in to [Vercel](https://vercel.com/).
2. Click **Add New...** -> **Project**.
3. Import your Git repository (`SkySentrix`).
4. Under **Project Settings**:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click "Edit" and choose `frontend`.
5. Under **Environment Variables**, add:
   - **Key**: `VITE_API_URL`
   - **Value**: `https://<your-render-backend-name>.onrender.com` (use your actual Render backend URL, without trailing slash)
6. Click **Deploy**.
7. Once deployed, open your Vercel URL (e.g. `https://skysentrix.vercel.app`).

---

## 10. Post-Deployment Verification Checklist

After deploying both services, run through these verification steps:

- [ ] **Backend Health Probe**: Open `https://<render-backend>.onrender.com/health` in browser. Response is HTTP 200 with `status: "healthy"`.
- [ ] **Frontend Load**: Open `https://<vercel-frontend>.vercel.app/demo`. The Mission Control UI loads with the dark aerospace theme.
- [ ] **3D Engine Viewport**: The 3D Lycoming IO-360 engine model renders in the center-left viewport with OrbitControls active.
- [ ] **Socket / API Connection**: Header connection pill displays `ONLINE` (green) or `STANDBY`.
- [ ] **Start SIH Demo**: Click **START SIH 2026 DEMO** in the Operator Simulation Console:
  - Simulation status changes to `RUNNING`.
  - Mission timer counts up.
  - 3D engine starts rotating dynamically with RPM.
  - Sensor comparison table shows live sensor updates with deviation bars.
  - Model prediction cards display Anomaly Score, Diagnosed Fault, Health Index, and RUL.
  - System State Timeline steps through diagnostic stages.
- [ ] **Fault Injection**: Select a fault type (e.g., `injector_degradation`), set severity, and click `INJECT FAULT`. Notice anomaly alert, 3D cylinder hotspot highlight, and Predictive Maintenance Advisory trigger.
- [ ] **SPA Direct Route Refresh**: Navigate to `/analytics` or `/settings` and hit browser refresh (F5). The page reloads cleanly without 404.

---

## 11. Common Issues & Troubleshooting

### Issue 1: Render Free Tier "Cold Start" (Spin-Down Delay)
- **Symptom**: On initial visit after 15+ minutes of inactivity, the frontend displays "Reconnecting..." or "Offline" for ~30–50 seconds.
- **Cause**: Render's free tier spins down inactive web services to save resources.
- **Resolution**: This is normal on free tier. Once spun up, the connection establishes automatically. For instant wakeups without cold starts, upgrade the Render instance to Starter ($7/month).

### Issue 2: CORS Network Errors
- **Symptom**: Browser console logs `Access to XMLHttpRequest blocked by CORS policy`.
- **Cause**: Backend origin filter does not include the exact Vercel URL.
- **Fix**: Ensure `CORS_ALLOW_ALL=true` is set in Render Environment Variables, or add your full Vercel URL to `CORS_ORIGINS` (e.g., `https://skysentrix.vercel.app`).

### Issue 3: WebSocket Connection Refused (Mixed Content)
- **Symptom**: `SecurityError: The operation is insecure` or `Mixed Content: The page was loaded over HTTPS, but attempted to connect to insecure WebSocket endpoint 'ws://...'`.
- **Cause**: `VITE_API_URL` was configured with `http://` instead of `https://`.
- **Fix**: Set `VITE_API_URL=https://<your-render-backend>.onrender.com` in Vercel Environment Variables. `client.ts` will automatically connect via `wss://`.

### Issue 4: 404 on Direct Route Refresh
- **Symptom**: Navigating to `https://<app>.vercel.app/demo` directly or reloading results in 404 Not Found.
- **Cause**: Vercel web server treats the route as a filesystem path.
- **Fix**: Confirm `frontend/vercel.json` is present with the SPA rewrite rule.
