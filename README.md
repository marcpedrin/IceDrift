# 🧊 IceNavigator
## Antarctic Navigation Decision Support System
### Smart India Hackathon 2026

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)
[![Cesium](https://img.shields.io/badge/Cesium-1.119-00b8ff?logo=cesium)](https://cesium.com)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)](https://python.org)

IceNavigator is a production-grade web application for Antarctic maritime navigation, combining real-time sea ice forecasting, iceberg tracking, AIS ship monitoring, and A* route optimization on a 3D Cesium globe.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser → Cesium 3D Globe (React + TypeScript + Vite)         │
│           5 layers: Ice / Icebergs / Ships / Routes / Cones     │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI Backend (Python 3.11)                                  │
│  ├─ IceNet (pretrained U-Net) → Sea Ice Concentration forecast  │
│  ├─ DRIFT (pretrained LSTM) + Physics → Iceberg trajectories    │
│  ├─ A* Router → Optimal routes (ice + iceberg + bathymetry)    │
│  ├─ AIS Service → MarineTraffic + mock fallback                 │
│  ├─ Sentinel Hub OGC → Satellite imagery                        │
│  └─ GEBCO NetCDF → Bathymetry depth queries                     │
├─────────────────────────────────────────────────────────────────┤
│  Redis → Cache (6h ice, 12h icebergs, 60s ships)               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Option A: Docker Compose (Recommended)

```bash
# 1. Clone and setup
git clone <repo>
cd icenavigator
cp .env.example .env
# Edit .env with your API keys (optional – works without keys)

# 2. Start all services
docker-compose up -d

# 3. Open app
open http://localhost
```

### Option B: Local Development

**Backend:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

pip install -r requirements.txt

# Download data (optional – app works with mock data)
python scripts/download_data.py --byu-icebergs

# Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

---

## Features

### 🌊 Sea Ice Heatmap (Layer 1)
- IceNet pretrained U-Net model (MC-Dropout T=30 for uncertainty)
- Physics seasonal fallback when weights not present
- 7-day forecast with date slider
- Blue → Cyan → White color ramp with opacity control

### 🗻 Iceberg Tracking (Layer 2 + 3)
- BYU/NSIDC Antarctic iceberg database
- DRIFT pretrained LSTM + Coriolis physics model
- 72h trajectory prediction
- MC-Dropout uncertainty cone (expanding Gaussian)
- Click → Sentinel-2 satellite imagery popup

### ⛴️ Ship Tracking (Layer 4)
- MarineTraffic AIS API (with rich mock fallback)
- Real-time WebSocket push every 60s
- Ship types: research, icebreaker, cargo, tanker, passenger, supply
- 24h position history trails
- Click → ship details popup

### 🗺 Route Planning (Layer 5)
- A* algorithm with 8-directional grid
- Risk scoring: ice (40%) + iceberg (30%) + bathymetry (20%) + weather (10%)
- Ship ice class profiles (Open Water → Icebreaker)
- Natural language explanation
- Click globe to set start/end points

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | System health check |
| `/ice/forecast` | GET | Sea ice concentration grid (lead_day=0-7) |
| `/icebergs/all` | GET | All tracked icebergs + trajectories |
| `/icebergs/{id}` | GET | Single iceberg with satellite image |
| `/ships/nearby` | GET | AIS ship positions |
| `/ws/ships` | WebSocket | Live ship position updates |
| `/navigation/route` | POST | Plan A* optimized route |
| `/navigation/replan` | POST | Replan from current position |

**API Docs:** http://localhost:8000/docs

---

## Pretrained Model Setup

### IceNet (Sea Ice Forecast)
```bash
git clone https://github.com/SFI-Visual-Intelligence/SFI-VI-IceNet-Task-Force
cd SFI-VI-IceNet-Task-Force
# Follow their README to download pretrained weights
cp checkpoints/icenet_pretrained.pth ../backend/checkpoints/icenet/
```

### DRIFT (Iceberg Drift)
```bash
git clone https://github.com/marco-jaeger/drift
cd drift
# Follow their README to download pretrained weights
cp models/drift_pretrained.pth ../backend/checkpoints/drift/
```

> **Note:** Without pretrained weights, the app uses physics-based models (seasonal ice model + Coriolis drift) that are immediately functional without any ML dependencies.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your keys:

| Variable | Required | Description |
|---|---|---|
| `CESIUM_ION_TOKEN` | ⭐ Recommended | 3D globe tiles (free tier) |
| `VITE_CESIUM_TOKEN` | ⭐ Recommended | Frontend Cesium token |
| `MARINETRAFFIC_API_KEY` | Optional | Live AIS data |
| `SENTINEL_HUB_CLIENT_ID` | Optional | Satellite imagery |
| `SENTINEL_HUB_CLIENT_SECRET` | Optional | Satellite imagery |
| `CDSAPI_KEY` | Optional | ERA5 wind download |
| `EARTHDATA_USER/PASS` | Optional | NSIDC data access |

> All API integrations degrade gracefully – the app works fully with mock data when keys are absent.

---

## Verification

```bash
# Health check
curl http://localhost:8000/health

# Ice forecast (first call may take 5-10s to generate)
curl "http://localhost:8000/ice/forecast?lead_day=0"

# All icebergs
curl http://localhost:8000/icebergs/all

# Plan a route
curl -X POST http://localhost:8000/navigation/route \
  -H "Content-Type: application/json" \
  -d '{
    "start_lat": -65.0,
    "start_lon": 0.0,
    "end_lat": -60.0,
    "end_lon": 30.0,
    "ship_type": "icebreaker"
  }'

# WebSocket test (install wscat: npm i -g wscat)
wscat -c ws://localhost:8000/ws/ships
```

---

## Project Structure

```
icenavigator/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry
│   │   ├── routes/                  # API endpoints
│   │   │   ├── ice.py
│   │   │   ├── icebergs.py
│   │   │   ├── ships.py
│   │   │   └── navigation.py
│   │   ├── services/               # Business logic
│   │   │   ├── icenet_service.py   # IceNet pretrained wrapper
│   │   │   ├── drift_service.py    # DRIFT + physics drift
│   │   │   ├── routing_service.py  # A* router
│   │   │   ├── ais_service.py      # MarineTraffic AIS
│   │   │   ├── satellite_service.py # Sentinel Hub
│   │   │   ├── bathymetry_service.py # GEBCO reader
│   │   │   ├── cache_service.py    # Redis + disk cache
│   │   │   └── uncertainty_service.py # MC-Dropout cones
│   │   ├── models/schemas.py       # Pydantic schemas
│   │   └── utils/geo.py            # Haversine, bearing, etc.
│   ├── checkpoints/                # Pretrained model weights
│   ├── data/                       # Downloaded datasets
│   ├── scripts/download_data.py
│   ├── config.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   └── src/
│       ├── App.tsx                 # Root component + state
│       ├── components/
│       │   ├── Globe/              # Cesium globe + layers
│       │   ├── Sidebar/            # Control panel
│       │   ├── Popups/             # Iceberg/Ship/Route popups
│       │   └── Legend/             # Map legend
│       ├── hooks/
│       │   ├── useWebSocket.ts     # Live ship WS
│       │   └── useCesiumViewer.ts  # Camera utilities
│       ├── services/api.ts         # Axios API client
│       └── types/index.ts          # TypeScript types
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Globe | Cesium.js 1.119 + Resium |
| Frontend | React 18 + TypeScript + Vite |
| Styling | Tailwind CSS + Framer Motion |
| Charts | Recharts |
| Backend | FastAPI 0.115 + Python 3.11 |
| ML | PyTorch 2.4 (IceNet U-Net + DRIFT LSTM) |
| Data | xarray, netCDF4, geopandas, scipy |
| Cache | Redis 7 + disk fallback |
| Deploy | Docker + nginx |

---

*IceNavigator — SIH 2026 | Antarctic Navigation Decision Support System*
