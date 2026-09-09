"""Iceberg tracking routes: /icebergs/all and /icebergs/{id}"""
from __future__ import annotations

import math
import random
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from app.models.schemas import IcebergResponse, IcebergListResponse, TrajectoryPoint
from app.services.cache_service import get_cache
from app.services.drift_service import get_drift
from app.services.satellite_service import get_satellite
from app.services.uncertainty_service import compute_uncertainty_cone

router = APIRouter(prefix="/icebergs", tags=["Icebergs"])


def _load_byu_icebergs() -> list[dict]:
    """Load BYU/NSIDC iceberg tracks CSV or return realistic mock data."""
    from pathlib import Path
    from config import get_settings

    csv_path = get_settings().byu_iceberg_path
    if csv_path.exists():
        try:
            import pandas as pd
            df = pd.read_csv(csv_path)
            icebergs = []
            for _, row in df.iterrows():
                icebergs.append({
                    "id": str(row.get("iceberg_id", f"A{random.randint(1,99):02d}")),
                    "lat": float(row["lat"]),
                    "lon": float(row["lon"]),
                    "size_km2": float(row.get("area_km2", 10.0)),
                    "length_km": float(row.get("length_km", 3.0)),
                    "width_km": float(row.get("width_km", 2.0)),
                    "velocity_ms": float(row.get("velocity_ms", 0.1)),
                    "heading_deg": float(row.get("heading_deg", 180)),
                })
            return icebergs
        except Exception as exc:
            logger.warning("BYU CSV load failed: {}. Using mock icebergs.", exc)

    # Rich mock icebergs – realistic positions and sizes in Southern Ocean
    return [
        {"id": "A23A", "lat": -75.2, "lon": -25.1, "size_km2": 3900.0, "length_km": 90.0, "width_km": 40.0, "velocity_ms": 0.08, "heading_deg": 15},
        {"id": "A76A", "lat": -63.5, "lon": -55.2, "size_km2": 4320.0, "length_km": 135.0, "width_km": 26.0, "velocity_ms": 0.12, "heading_deg": 30},
        {"id": "B22A", "lat": -68.1, "lon": -10.3, "size_km2": 1150.0, "length_km": 45.0, "width_km": 18.0, "velocity_ms": 0.15, "heading_deg": 45},
        {"id": "C28B", "lat": -61.8, "lon": 5.7,  "size_km2": 280.0,  "length_km": 20.0, "width_km": 10.0, "velocity_ms": 0.22, "heading_deg": 70},
        {"id": "D15A", "lat": -66.5, "lon": 40.2, "size_km2": 650.0,  "length_km": 30.0, "width_km": 15.0, "velocity_ms": 0.18, "heading_deg": 120},
        {"id": "E09C", "lat": -59.3, "lon": -30.1,"size_km2": 95.0,   "length_km": 12.0, "width_km": 6.0,  "velocity_ms": 0.30, "heading_deg": 200},
        {"id": "F31A", "lat": -72.4, "lon": 60.8, "size_km2": 2200.0, "length_km": 70.0, "width_km": 25.0, "velocity_ms": 0.05, "heading_deg": 180},
        {"id": "G12B", "lat": -64.7, "lon": -70.5,"size_km2": 380.0,  "length_km": 22.0, "width_km": 12.0, "velocity_ms": 0.25, "heading_deg": 310},
        {"id": "H44A", "lat": -57.9, "lon": -45.3,"size_km2": 55.0,   "length_km": 8.0,  "width_km": 4.0,  "velocity_ms": 0.40, "heading_deg": 260},
        {"id": "I07D", "lat": -70.2, "lon": 90.1, "size_km2": 820.0,  "length_km": 35.0, "width_km": 18.0, "velocity_ms": 0.10, "heading_deg": 150},
        {"id": "J19A", "lat": -61.1, "lon": 20.4, "size_km2": 145.0,  "length_km": 14.0, "width_km": 7.0,  "velocity_ms": 0.28, "heading_deg": 85},
        {"id": "K03B", "lat": -74.8, "lon": -80.2,"size_km2": 5100.0, "length_km": 110.0,"width_km": 35.0, "velocity_ms": 0.04, "heading_deg": 5},
    ]


@router.get("/all", response_model=IcebergListResponse)
async def get_all_icebergs(
    include_trajectories: bool = Query(True, description="Include predicted trajectories"),
    forecast_hours: int = Query(72, ge=6, le=168, description="Trajectory forecast horizon (hours)"),
):
    """
    Return all tracked Antarctic icebergs with positions and trajectories.

    Data source: BYU/NSIDC iceberg tracking database (CSV).
    Trajectories from DRIFT pretrained model or physics drift model.
    Uncertainty cones from MC-Dropout ensemble (T=30).
    """
    cache = get_cache()
    cache_key = cache.make_key("icebergs_all", str(include_trajectories), str(forecast_hours))

    cached = await cache.get(cache_key)
    if cached:
        return IcebergListResponse(**cached)

    raw_icebergs = _load_byu_icebergs()
    drift = get_drift()
    satellite = get_satellite()

    icebergs = []
    for berg in raw_icebergs:
        # Generate trajectory
        trajectory = []
        uncertainty_cone = []

        if include_trajectories:
            traj_raw = drift.predict_trajectory(
                lat=berg["lat"], lon=berg["lon"],
                heading_deg=berg["heading_deg"],
                velocity_ms=berg["velocity_ms"],
                wind_u=-5.0, wind_v=3.0,  # typical Southern Ocean winds
                current_u=0.1, current_v=-0.05,
                hours_ahead=forecast_hours,
            )
            trajectory = [TrajectoryPoint(**p) for p in traj_raw]

            # MC-Dropout ensemble for uncertainty cone
            ensemble = drift.mc_dropout_ensemble(
                lat=berg["lat"], lon=berg["lon"],
                heading_deg=berg["heading_deg"],
                velocity_ms=berg["velocity_ms"],
                hours_ahead=forecast_hours,
                n_samples=30,
            )
            uncertainty_cone = compute_uncertainty_cone(ensemble)

        # Satellite image URL
        img_url = await satellite.get_iceberg_image_url(
            lat=berg["lat"], lon=berg["lon"],
            date=datetime.utcnow().strftime("%Y-%m-%d"),
        )

        first_seen = datetime.utcnow() - timedelta(days=random.randint(30, 365))

        icebergs.append(IcebergResponse(
            id=berg["id"],
            lat=berg["lat"],
            lon=berg["lon"],
            size_km2=berg["size_km2"],
            length_km=berg["length_km"],
            width_km=berg["width_km"],
            velocity_ms=berg["velocity_ms"],
            heading_deg=berg["heading_deg"],
            first_seen=first_seen,
            last_updated=datetime.utcnow(),
            trajectory=trajectory,
            uncertainty_cone=uncertainty_cone,
            satellite_image_url=img_url,
        ))

    response = IcebergListResponse(
        count=len(icebergs),
        icebergs=icebergs,
        timestamp=datetime.utcnow(),
    )

    from config import get_settings
    await cache.set(cache_key, response.model_dump(mode="json"), ttl=get_settings().iceberg_cache_ttl)

    logger.info("Iceberg list generated: {} icebergs", len(icebergs))
    return response


@router.get("/{iceberg_id}", response_model=IcebergResponse)
async def get_iceberg(
    iceberg_id: str,
    forecast_hours: int = Query(72, ge=6, le=168),
):
    """Get a specific iceberg by ID with full trajectory and satellite image."""
    all_resp = await get_all_icebergs(include_trajectories=True, forecast_hours=forecast_hours)
    for berg in all_resp.icebergs:
        if berg.id.upper() == iceberg_id.upper():
            return berg
    raise HTTPException(status_code=404, detail=f"Iceberg {iceberg_id} not found")
