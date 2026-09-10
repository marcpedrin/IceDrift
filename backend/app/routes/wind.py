"""Wind field route: /wind/field — real-time Southern Ocean wind vectors."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query
from loguru import logger

from app.models.schemas import WindFieldResponse, WindCell
from app.services.cache_service import get_cache
from app.services.ingestion_service import get_ingestion
from app.services.weather_service import get_weather

router = APIRouter(prefix="/wind", tags=["Wind Field"])


@router.get("/field", response_model=WindFieldResponse)
async def get_wind_field(
    resolution: int = Query(1, ge=1, le=5, description="Grid resolution in degrees (1 = full density, 5 = sparse)"),
):
    """
    Return a Southern Ocean wind vector grid at 1° spacing.

    Each cell contains:
    - **u10**: eastward wind component (m/s)
    - **v10**: northward wind component (m/s)
    - **speed_ms**: wind magnitude
    - **direction_deg**: meteorological direction (0° = North, 90° = East)

    Source: Open-Meteo ERA5 reanalysis (daily ingestion) with Southern Ocean climatology fallback.
    Cached for 1 hour.
    """
    cache = get_cache()
    cache_key = cache.make_key("wind_field", str(resolution))

    cached = await cache.get(cache_key)
    if cached:
        logger.debug("Wind field cache hit")
        return WindFieldResponse(**cached)

    ingestion = get_ingestion()
    all_cells = ingestion.get_wind_cells()

    if all_cells:
        # Filter by requested resolution (subsample by stride)
        if resolution > 1:
            cells_raw = [
                c for c in all_cells
                if round(c["lat"]) % resolution == 0 and round(c["lon"]) % resolution == 0
            ]
        else:
            cells_raw = all_cells
        source = "Open-Meteo ERA5 (ingested)"
    else:
        # Live generation from weather service
        logger.info("No cached wind grid – generating live from Open-Meteo …")
        cells_raw = await _generate_live_wind_grid(resolution)
        source = "Open-Meteo ERA5 (live)"

    cells = [WindCell(**c) for c in cells_raw]
    response = WindFieldResponse(
        timestamp=datetime.utcnow(),
        source=source,
        resolution_deg=float(resolution),
        cells=cells,
        bbox={"lat_min": -90.0, "lat_max": -55.0, "lon_min": -180.0, "lon_max": 180.0},
    )

    await cache.set(cache_key, response.model_dump(mode="json"), ttl=3600)  # 1h TTL
    logger.info("Wind field served: {} cells, res={}°", len(cells), resolution)
    return response


async def _generate_live_wind_grid(resolution: int = 1) -> list[dict]:
    """Generate wind grid on-the-fly from Open-Meteo for key sample points."""
    import math
    weather = get_weather()
    cells = []

    lats = list(range(-89, -54, resolution))
    lons = list(range(-180, 180, resolution))

    # Fetch a subset of real points, fill rest with climatology
    sample_lats = lats[::3]
    sample_lons = lons[::3]
    real_data: dict[tuple, dict] = {}

    for lat in sample_lats:
        for lon in sample_lons[:20]:  # Limit concurrent calls
            try:
                w = await weather.get_current_weather(float(lat), float(lon))
                real_data[(lat, lon)] = w
            except Exception:
                pass

    for lat in lats:
        for lon in lons:
            # Find nearest real sample
            nearest = None
            best_d = float("inf")
            for (slat, slon), data in real_data.items():
                d = math.sqrt((lat - slat) ** 2 + (lon - slon) ** 2)
                if d < best_d:
                    best_d = d
                    nearest = data

            if nearest and best_d <= 4.0:
                u10 = nearest["wind_u"]
                v10 = nearest["wind_v"]
                speed = nearest["wind_speed_ms"]
                direction = nearest["wind_direction_deg"]
                src = nearest.get("source", "Open-Meteo")
            else:
                # Climatology fallback
                u10, v10, speed, direction = _climatology(lat, lon)
                src = "climatology"

            cells.append({
                "lat": float(lat),
                "lon": float(lon),
                "u10": u10,
                "v10": v10,
                "speed_ms": round(speed, 2),
                "direction_deg": round(direction, 1),
                "source": src,
            })

    return cells


def _climatology(lat: float, lon: float):
    """Southern Ocean wind climatology."""
    import math
    if lat < -70:
        speed, direction = 5.5, 120.0
    elif lat < -60:
        speed, direction = 8.5, 260.0
    else:
        speed, direction = 6.5, 255.0
    dir_rad = math.radians(direction)
    u = round(-speed * math.sin(dir_rad), 3)
    v = round(-speed * math.cos(dir_rad), 3)
    return u, v, speed, direction
