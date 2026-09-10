# 🧊 IceNavigator — Architecture & System Context

## 1. Project Overview & Mission

**IceNavigator** is an Antarctic Maritime Navigation Decision Support System engineered for the **Smart India Hackathon (SIH) 2026**.

Navigating the Southern Ocean and Antarctic coastal waters poses severe hazards to polar research vessels, supply ships, and icebreakers:
* Rapidly evolving **sea ice concentration (SIC)** driven by polar winds and ocean currents.
* Drifting **icebergs and bergy bits** tracked across millions of square kilometers.
* **Extreme weather**, katabatic wind bursts, and uncharted shallow bathymetry prone to grounding.
* Limited communication bandwidth requiring real-time, resilient client-server operations.

IceNavigator provides a mission-critical digital twin combining **deep-learning sea-ice forecasts**, **physics-informed iceberg drift predictions**, **real-time AIS ship monitoring**, and **multi-objective A\* route planning** on an interactive **3D Cesium globe**.

---

## 2. High-Level System Architecture

IceNavigator follows a decoupled, service-oriented architecture designed for low-latency spatial queries, real-time telemetry streaming, and automated graceful degradation.

```mermaid
graph TB
    subgraph Client ["Frontend Layer (Browser / WebGL)"]
        UI["React 18 + Vite + Tailwind CSS"]
        Cesium["Cesium 3D Digital Twin (Resium)"]
        Controls["Sidebar / Layer Manager / Time Slider"]
        WSClient["WebSocket Client (Auto-reconnect)"]
    end

    subgraph Gateway ["API Gateway & Application Server"]
        FastAPI["FastAPI 0.115 (Python 3.12/3.11)"]
        CORS["CORS & GZip Middleware"]
        WSServer["WebSocket Hub (/ws/ships)"]
    end

    subgraph Engines ["Computational & Modeling Engines"]
        IceNetSvc["IceNet Service<br/>(Pretrained U-Net CNN + Seasonal Fallback)"]
        DriftSvc["DRIFT Service<br/>(LSTM Neural Net + IICG Coriolis Physics)"]
        RouterSvc["A* Routing Service<br/>(8-Directional Polar Grid Optimization)"]
        BathySvc["Bathymetry Service<br/>(GEBCO NetCDF Depth Queries)"]
        WeatherSvc["Weather Service<br/>(Open-Meteo & ERA5 Wind Vectors)"]
        UncertaintySvc["Uncertainty Engine<br/>(MC-Dropout & Expanding Gaussian Cones)"]
    end

    subgraph DataSources ["Data & External Service Integrations"]
        CDS["Copernicus Climate Data Store (ERA5)"]
        NASA["NASA Earthdata / NSIDC (Sea Ice)"]
        BYU["BYU Antarctic Iceberg Database"]
        MT["MarineTraffic AIS API (+ High-fidelity Mocks)"]
        Sentinel["Sentinel Hub OGC (Sentinel-2 Imagery)"]
        GEBCO["GEBCO NetCDF Bathymetry"]
    end

    subgraph Persistence ["Caching & State Store"]
        Redis["Redis 7 (Distributed Cache)"]
        MemCache["In-Memory / Disk Cache Fallback"]
    end

    Controls --> UI
    UI --> Cesium
    WSClient <-->|Live AIS stream (60s)| WSServer
    UI -->|REST queries & route planning| FastAPI

    FastAPI --> CORS
    CORS --> Engines

    IceNetSvc --> UncertaintySvc
    DriftSvc --> UncertaintySvc
    RouterSvc --> IceNetSvc
    RouterSvc --> DriftSvc
    RouterSvc --> BathySvc
    RouterSvc --> WeatherSvc

    IceNetSvc -.-> CDS & NASA
    DriftSvc -.-> BYU
    Engines -.-> Redis
    Redis -.-> MemCache
    FastAPI -.-> MT
    FastAPI -.-> Sentinel
    BathySvc -.-> GEBCO
```

---

## 3. Core Subsystems & Technical Details

### 3.1 Sea Ice Concentration (SIC) Forecasting (Layer 1)
* **Model Pipeline**: Wraps the **IceNet** architecture (convolutional U-Net CNN trained on ERA5 reanalysis and CMIP6 climate models).
* **Epistemic Uncertainty**: Employs Monte Carlo Dropout ($T=30$ passes) during inference to calculate variance per spatial cell.
* **Physics Fallback**: If pretrained `.pth` weights are not installed, the engine seamlessly switches to an analytical seasonal sinusoidal equation based on latitude, month, and polar day cycles:
  $$\text{SIC}(lat, day) = f(\text{latitude}, \sin(\omega \cdot t)) + \mathcal{N}(0, \sigma^2)$$
* **Forecast Horizon**: 0 to 7 lead days across the Southern Ocean bounding box (`-90.0°S` to `-55.0°S`, `-180.0°W` to `180.0°E`).
* **Visual Rendering**: Color ramp interpolating dynamically from dark blue (open ocean, $0.0$) through cyan to solid white/frost (pack ice, $1.0$) with client-side opacity controls.

### 3.2 Iceberg Tracking & Trajectory Modeling (Layers 2 & 3)
* **Data Origin**: BYU/NSIDC Antarctic Iceberg Database tracking named giant bergs (e.g., A-23A, B-15, D-28) alongside smaller tabular bergs.
* **Drift Dynamics**:
  * **Deep Learning**: DRIFT LSTM network taking 10 input features (past positions, velocity, wind vectors, current vectors).
  * **Physics Core (IICG Standards)**:
    $$\vec{v}_{\text{iceberg}} = \alpha \vec{v}_{\text{wind}} + \vec{v}_{\text{current}} + \vec{f} \times \vec{v}_{\text{iceberg}}$$
    where $\alpha \approx 0.018$ (wind factor) and $\vec{f} = 2\Omega \sin(\text{lat})\hat{k}$ is the Coriolis parameter ($\Omega = 7.2921 \times 10^{-5}\text{ rad/s}$).
* **72-Hour Prediction & Cones**: Generates forward projection points every 6 hours with expanding Gaussian uncertainty envelopes ($\sigma_{lat}, \sigma_{lon}$).
* **Satellite High-Res Imagery**: Integrates Sentinel-2 L2A optical imagery via Sentinel Hub WMS/REST API with fallback synthetic radar footprints.

### 3.3 AIS Ship Monitoring & Telemetry (Layer 4)
* **Telemetry**: Ingests vessel coordinates, speed over ground (SOG in knots), course over ground (COG in degrees), heading, destination, flag, and 24-hour historical trail points.
* **Vessel Categories**: Research vessels (e.g., *RV Polarstern*, *RRS Sir David Attenborough*), Polar Icebreakers, Cargo, Tankers, Passenger/Expedition, and Supply ships.
* **Real-time Streaming**: Bi-directional FastAPI WebSocket (`/ws/ships`) pushes position updates to connected clients at 60-second intervals.
* **Graceful Degradation**: If MarineTraffic credentials are unset, a simulated AIS generator maintains realistic vessel movements based on typical Antarctic logistics routes.

### 3.4 Multi-Factor A* Route Planning (Layer 5)
* **Search Space**: 8-directional graph traversal over a discretized polar grid ($0.5^\circ \approx 55\text{ km}$ resolution at $60^\circ\text{S}$).
* **Comprehensive Risk Cost Function**:
  $$\text{Cost}(u \to v) = \text{Distance}(u, v) \times \left(1.0 + 3.0 \times \text{Risk}(v)\right)$$
  where $\text{Risk}(v)$ is a weighted combination:
  $$\text{Risk} = 0.40 \times \text{IceRisk} + 0.30 \times \text{IcebergRisk} + 0.20 \times \text{BathymetryRisk} + 0.10 \times \text{WeatherRisk}$$
* **Ship Ice Class Constraints**:
  | Ice Class | Max Allowable SIC | Speed Penalty Factor | Notes |
  |---|---|---|---|
  | **Open Water** | $\le 10\%$ | $3.0\times$ | Unreinforced hulls; strict ice avoidance |
  | **Ice Class 1C** | $\le 30\%$ | $2.0\times$ | Light ice conditions |
  | **Ice Class 1B** | $\le 50\%$ | $1.5\times$ | Medium ice conditions |
  | **Ice Class 1A** | $\le 70\%$ | $1.2\times$ | Heavy ice conditions |
  | **Ice Class 1AS** | $\le 85\%$ | $1.1\times$ | Severe polar pack ice |
  | **Icebreaker** | $\le 100\%$ | $1.0\times$ | Full polar icebreaking capability |
* **Bathymetric Safety**: Rejects or severely penalizes waypoints where water depth from GEBCO netCDF falls below vessel draft safety margins (default $20\text{ m}$).
* **Replanning**: `/navigation/replan` recalculates the route from the ship's current position if ice drift blocks forward segments.

---

## 4. Technology Stack Matrix

| Subsystem | Technology | Purpose |
|---|---|---|
| **Globe & Geospatial** | CesiumJS 1.119 + Resium | 3D ellipsoidal globe, terrain rendering, polylines, billboards, polygons |
| **Frontend Framework** | React 18 + TypeScript | Component tree, custom hooks, reactive state management |
| **Build & Bundler** | Vite 5 | Fast HMR, optimized production tree-shaking |
| **Styling & UI** | Tailwind CSS 3.4 + Framer Motion 11 | Polished dark mode UI, translucent glass panels, micro-animations |
| **Data Visualization** | Recharts 2.10 | Iceberg size distribution, route elevation/depth & risk profiles |
| **Backend Framework** | FastAPI 0.115 + Uvicorn | Async REST API, WebSocket server, auto OpenAPI/Swagger docs |
| **Deep Learning** | PyTorch 2.4 / Torchvision | IceNet U-Net and DRIFT LSTM neural network inference |
| **Geospatial & Scientific** | GeoPandas, Shapely, PyProj, Rasterio | Coordinate reference systems, polygon bounding, spatial math |
| **Data Arrays & Grids** | NumPy, SciPy, Pandas, xarray, NetCDF4 | EASE2 polar grids, NetCDF4 GEBCO bathymetry, multidimensional arrays |
| **Cache & State** | Redis 7 + Disk/In-memory fallback | High-speed response caching (6h ice, 12h icebergs, 1m AIS) |
| **Containerization** | Docker & Docker Compose | Multi-container deployment (FastAPI backend + Nginx frontend + Redis) |

---

## 5. Repository File Structure

```
IceDrift/
├── context.md                     # System context, architecture & developer reference
├── README.md                      # Quick start and project documentation
├── docker-compose.yml             # Full-stack Docker orchestration
├── .env.example                   # Environment configuration template
├── .env                           # Local environment secrets and endpoints
│
├── backend/
│   ├── config.py                  # Pydantic Settings (env vars, TTLs, model dirs)
│   ├── Dockerfile                 # Python 3.11/3.12 container definition
│   ├── requirements.txt           # Python backend dependencies
│   ├── venv/                      # Local Python virtual environment
│   ├── checkpoints/               # Directory for IceNet & DRIFT weights
│   ├── data/                      # Local datasets (GEBCO netCDF, iceberg tracks)
│   ├── scripts/
│   │   └── download_data.py       # Automated dataset downloader
│   └── app/
│       ├── main.py                # FastAPI lifecycle, middleware, router mounts
│       ├── models/
│       │   └── schemas.py         # Pydantic request/response schemas & Enums
│       ├── routes/
│       │   ├── ice.py             # GET /ice/forecast endpoint
│       │   ├── icebergs.py        # GET /icebergs/all and /icebergs/{id}
│       │   ├── ships.py           # GET /ships/nearby and WS /ws/ships
│       │   └── navigation.py      # POST /navigation/route & /navigation/replan
│       ├── services/
│       │   ├── icenet_service.py  # Pretrained IceNet U-Net + seasonal physics
│       │   ├── drift_service.py   # DRIFT LSTM + Coriolis physics drift
│       │   ├── routing_service.py # A* polar grid routing algorithm
│       │   ├── ais_service.py     # MarineTraffic API + rich mock fallback
│       │   ├── satellite_service.py # Sentinel Hub OGC satellite imagery
│       │   ├── bathymetry_service.py# GEBCO NetCDF depth query engine
│       │   ├── weather_service.py # Open-Meteo & ERA5 wind vectors
│       │   ├── cache_service.py   # Redis connection + memory/disk cache
│       │   └── uncertainty_service.py # MC-Dropout cone generation
│       └── utils/
│           └── geo.py             # Haversine, bearing, and interpolation utilities
│
└── frontend/
    ├── package.json               # Frontend dependencies and npm scripts
    ├── tsconfig.json              # TypeScript configuration
    ├── vite.config.ts             # Vite bundler configuration + Cesium plugin
    ├── tailwind.config.js         # Tailwind theme & design tokens
    ├── nginx.conf                 # Nginx reverse proxy configuration
    ├── Dockerfile                 # Multi-stage production build container
    ├── index.html                 # Single-page HTML entry point
    └── src/
        ├── main.tsx               # React DOM bootstrapping
        ├── App.tsx                # Master UI layout, layer toggles, state hooks
        ├── index.css              # Global styles & Cesium overrides
        ├── types/
        │   └── index.ts           # Shared TypeScript interfaces & types
        ├── services/
        │   └── api.ts             # Axios client & REST endpoint handlers
        ├── hooks/
        │   ├── useWebSocket.ts    # Reconnecting WebSocket client for AIS ships
        │   └── useCesiumViewer.ts # Cesium camera fly-to and viewport utilities
        └── components/
            ├── Globe/
            │   ├── CesiumGlobe.tsx     # 3D globe root, event handlers, click picking
            │   ├── IceHeatmapLayer.tsx # Sea ice concentration visual overlay
            │   ├── IcebergLayer.tsx    # Iceberg billboards, tracks & uncertainty cones
            │   ├── ShipLayer.tsx       # AIS vessel markers, headings & trails
            │   └── RouteLayer.tsx      # A* calculated route polyline & waypoints
            ├── Sidebar/
            │   └── Sidebar.tsx         # Route planning form, layer switches, stats
            ├── Popups/
            │   ├── IcebergPopup.tsx    # Details card with Sentinel-2 preview
            │   ├── ShipPopup.tsx       # Vessel specs, SOG, COG, history
            │   └── RoutePopup.tsx      # Risk breakdown, ETA, distance profile
            └── Legend/
                └── Legend.tsx          # Concentration color scale & map symbology
```

---

## 6. API Interface Specifications

| Method | Route | Description | Input / Parameters | Response Type |
|---|---|---|---|---|
| `GET` | `/health` | Application health check | None | `{"status": "ok", "models": {...}, "cache": bool}` |
| `GET` | `/ice/forecast` | Sea ice concentration grid | `lead_day: int` (0–7) | `IceForecastResponse` (cells with lat, lon, conc, uncertainty) |
| `GET` | `/icebergs/all` | All tracked icebergs | None | `IcebergListResponse` (trajectories, sizes, velocities) |
| `GET` | `/icebergs/{id}` | Single iceberg detail | `id: str` | `IcebergResponse` (with Sentinel satellite imagery URL) |
| `GET` | `/ships/nearby` | AIS vessel locations | Optional bounding box / radius | `ShipListResponse` (positions, heading, speed, history) |
| `WS` | `/ws/ships` | Real-time AIS WebSocket push | None (Persistent connection) | Pushes `ShipListResponse` every 60s |
| `POST` | `/navigation/route` | Compute A* optimal route | `RouteRequest` (start, end, ice_class, draft) | `RouteResponse` (waypoints, distance km, ETA, risk breakdown) |
| `POST` | `/navigation/replan` | Dynamic mid-voyage reroute | `ReplanRequest` (current pos, destination, ice_class) | `RouteResponse` |

---

## 7. Data Flow & Execution Sequences

### Route Calculation Flow
1. **User Interaction**: User clicks two points on the 3D Cesium globe or types coordinates in the **Sidebar**, selects the ship's **Ice Class** (e.g. *Ice Class 1A*), and triggers **Calculate Route**.
2. **API Request**: Frontend issues `POST /navigation/route` with start/end coordinates and vessel constraints.
3. **Backend Risk Synthesis**:
   - `IceNetService` supplies the spatial sea ice concentration grid for lead day 0.
   - `DriftService` supplies predicted iceberg coordinates intersecting the temporal window.
   - `BathymetryService` evaluates water depth against the safety threshold ($20\text{ m}$).
   - `WeatherService` supplies Southern Ocean wind vectors.
4. **Graph Search**: `RoutingService` executes A* search across permissible grid nodes, calculating traversal cost factoring distance and combined risk score.
5. **Response & Visualization**: Backend returns waypoints, distance, ETA, and risk breakdown. Cesium renders the 3D route ribbon colored by risk segment.

---

## 8. Operational Modes & Graceful Degradation

| Service | When API Key / Checkpoint Available | When Missing / Degraded |
|---|---|---|
| **IceNet** | Pretrained PyTorch U-Net inference on EASE2 grid | Analytical sinusoidal seasonal physics model |
| **Iceberg Drift** | Pretrained DRIFT LSTM trajectory neural network | IICG Coriolis + wind/current numerical physics model |
| **AIS Ships** | Real-time MarineTraffic API telemetry stream | Synthetic AIS simulator with realistic polar vessels |
| **Satellite Imagery** | High-resolution Sentinel-2 true-color/false-color | Procedural synthetic radar backscatter imagery |
| **Bathymetry** | High-resolution GEBCO NetCDF ocean depths | Analytical distance-to-shelf depth estimation |
| **Cache** | High-throughput distributed Redis cache | Thread-safe in-memory cache with disk spillover |

---

## 9. Quick Development & Verification Commands

### Start Backend
```powershell
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
* Interactive Swagger UI: `http://localhost:8000/docs`

### Start Frontend
```powershell
cd frontend
npm run dev
```
* Web Application: `http://localhost:5173`

### Health & Route Verification
```bash
# Health Check
curl http://localhost:8000/health

# Ice Forecast
curl "http://localhost:8000/ice/forecast?lead_day=0"

# Route Computation
curl -X POST http://localhost:8000/navigation/route \
  -H "Content-Type: application/json" \
  -d '{"start_lat": -65.0, "start_lon": 0.0, "end_lat": -60.0, "end_lon": 30.0, "ship_type": "icebreaker"}'
```
