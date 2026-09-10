# Implementation Notes

## Architecture Overview
This project uses a decoupled frontend-backend architecture:
- **Frontend**: React + TypeScript + CesiumJS (Resium wrapper) built with Vite.
- **Backend**: FastAPI (Python) serving a REST API and WebSockets for real-time data.
- **Data Ingestion**: A Python script (`backend/scripts/download_data.py`) runs periodically to fetch data from various sources.

## Implemented Features

### 1. Icebergs
- **Data Source**: BYU (Brigham Young University) Antarctic Iceberg Tracking Database.
- **Processing**: Downloaded as a ZIP file, parsed CSVs, calculated drift velocity and bearing using the Haversine formula and spherical trigonometry.
- **Visualization**: Displayed on the Cesium globe as interactive `PointPrimitives` with velocity vectors indicating drift direction.

### 2. Sea Ice Concentration
- **Data Source**: Mock data (originally intended for NSIDC).
- **Processing**: The backend exposes an A* routing endpoint (`/routes/plan`) that avoids high-risk areas based on Sea Ice Concentration and iceberg proximity.
- **Visualization**: Displayed as a colored point cloud or heatmap on the globe.

### 3. Wind Field
- **Data Source**: Synthetic generation script mimicking GRIB2 output (originally intended for GFS/ERA5).
- **Visualization**: GPU-accelerated particle animation using the `cesium-wind-layer` plugin. The wind layer consumes JSON data representing U and V vectors.

### 4. Ocean Currents
- **Data Source**: Copernicus Marine Service (`copernicusmarine` Python package) with a synthetic fallback if credentials are not provided.
- **Visualization**: Also rendered using `cesium-wind-layer` but configured with a different `colorScale` and `velocityScale` to differentiate from the wind field.

### 5. Shipping Lanes
- **Data Source**: COMNAP (Council of Managers of National Antarctic Programs) logistics corridors.
- **Visualization**: Loaded as a raw `GeoJsonDataSource` in Cesium. A custom `PolylineGlowMaterialProperty` gives the static lanes a glowing `#00ffcc` cyan appearance.

### 6. A* Route Planning
- **Implementation**: The user can input start and end coordinates via the UI.
- **Processing**: The backend calculates an optimal route avoiding icebergs and heavy sea ice using the A* algorithm.
- **Visualization**: The resulting route is displayed as a bold path on the globe, and the camera automatically zooms to fit the route.

## Graceful Degradation
To ensure the dashboard is always functional, all data ingestion points have fallback synthetic data generation in case network access is restricted or external APIs fail.

- Icebergs: Falls back to a mock synthetic set.
- Wind: Falls back to a geostrophic approximation based on latitude.
- Currents: Falls back to synthetic gyre models.
