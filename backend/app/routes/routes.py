"""Polar route corridors: /routes/polar — real Antarctic logistics routes with danger coding."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query
from loguru import logger

from app.models.schemas import (
    PolarRoutesResponse, PolarRouteResponse, RouteSegmentRisk, RiskLevel
)
from app.services.cache_service import get_cache
from app.services.ingestion_service import get_ingestion, get_route_scorer
from app.services.icenet_service import get_icenet

from fastapi.responses import JSONResponse
import json
from pathlib import Path

router = APIRouter(prefix="/routes", tags=["Polar Routes"])

@router.get("/geojson")
async def get_polar_routes_geojson():
    """Return raw polar routes as GeoJSON for Cesium."""
    geojson_path = Path("data/polar_routes.geojson")
    if geojson_path.exists():
        with open(geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(content=data)
    return JSONResponse(content={"error": "Not found"}, status_code=404)

@router.get("/polar", response_model=PolarRoutesResponse)
async def get_polar_routes(
    route_id: Optional[str] = Query(None, description="Filter by specific route ID"),
    scored: bool = Query(True, description="Include per-segment risk scoring"),
):
    """
    Return all real Antarctic logistics supply corridors with per-segment danger coding.

    Segments are color-coded:
    - **safe** (GREEN)    — SIC < 20% and no icebergs within 200km
    - **moderate** (YELLOW) — SIC 20-60% or iceberg 50-200km away
    - **high** (RED)      — SIC > 60%, iceberg < 50km, or grounding hazard

    Routes are derived from COMNAP polar logistics corridors and historical AIS data.
    Cached for 30 minutes (risk scores update with fresh SIC and iceberg data).
    """
    cache = get_cache()
    cache_key = cache.make_key("polar_routes", str(route_id or "all"), str(scored))

    cached = await cache.get(cache_key)
    if cached:
        logger.debug("Polar routes cache hit")
        return PolarRoutesResponse(**cached)

    ingestion = get_ingestion()
    raw_routes = ingestion.get_routes()

    if not raw_routes:
        logger.warning("No polar routes loaded – returning empty")
        response = PolarRoutesResponse(count=0, routes=[], timestamp=datetime.utcnow())
        return response

    # Filter by route_id if requested
    if route_id:
        raw_routes = [
            r for r in raw_routes
            if r.get("properties", {}).get("route_id", "").lower() == route_id.lower()
        ]

    # Score segments with current ice + iceberg data
    sic_cells = ingestion.get_sic_cells()
    icebergs = ingestion.get_icebergs()

    if not sic_cells:
        # Fall back to IceNet for SIC
        icenet = get_icenet()
        sic_cells = icenet.forecast(lead_day=0)

    scorer = get_route_scorer()
    scored_routes_raw = scorer.score_routes(raw_routes, sic_cells, icebergs) if scored else []

    # If scoring failed or not requested, build minimal response from raw
    if not scored_routes_raw:
        scored_routes_raw = _routes_from_raw(raw_routes)

    routes = []
    for r in scored_routes_raw:
        segments = [
            RouteSegmentRisk(
                seg_id=s["seg_id"],
                start_lat=s["start_lat"],
                start_lon=s["start_lon"],
                end_lat=s["end_lat"],
                end_lon=s["end_lon"],
                center_lat=s["center_lat"],
                center_lon=s["center_lon"],
                length_km=s.get("length_km", 50.0),
                risk_level=RiskLevel(s.get("risk_level", "safe")),
                risk_score=s.get("risk_score", 0.0),
                ice_concentration=s.get("ice_concentration", 0.0),
                iceberg_proximity_km=s.get("iceberg_proximity_km"),
            )
            for s in r.get("segments", [])
        ]

        routes.append(PolarRouteResponse(
            route_id=r["route_id"],
            name=r["name"],
            route_type=r.get("route_type", "supply"),
            distance_km=float(r.get("distance_km", 0)),
            typical_vessel=r.get("typical_vessel", "supply"),
            overall_risk=RiskLevel(r.get("overall_risk", "safe")),
            overall_risk_score=float(r.get("overall_risk_score", 0.0)),
            segments=segments,
            waypoints=r.get("waypoints", []),
            timestamp=datetime.utcnow(),
        ))

    # Estimate SIC data age
    ice_age_hours = None
    last_run_file = ingestion._data_dir / ".last_ingestion"
    if last_run_file.exists():
        try:
            ts = float(last_run_file.read_text().strip())
            ice_age_hours = (datetime.now(tz=timezone.utc).timestamp() - ts) / 3600
        except Exception:
            pass

    response = PolarRoutesResponse(
        count=len(routes),
        routes=routes,
        timestamp=datetime.utcnow(),
        ice_forecast_age_hours=round(ice_age_hours, 2) if ice_age_hours else None,
    )

    await cache.set(cache_key, response.model_dump(mode="json"), ttl=1800)  # 30 min
    logger.info("Polar routes served: {} routes, {} total segments",
                len(routes), sum(len(r.segments) for r in routes))
    return response


def _routes_from_raw(raw_routes: list[dict]) -> list[dict]:
    """Build minimal (unscored) route records from raw GeoJSON features."""
    result = []
    for feature in raw_routes:
        props = feature.get("properties", {})
        segments = feature.get("segments", [])
        coords = feature.get("geometry", {}).get("coordinates", [])
        waypoints = [{"lat": c[1], "lon": c[0]} for c in coords]
        result.append({
            "route_id": props.get("route_id", ""),
            "name": props.get("name", ""),
            "route_type": props.get("route_type", "supply"),
            "distance_km": props.get("distance_km", 0),
            "typical_vessel": props.get("typical_vessel", "supply"),
            "overall_risk": "safe",
            "overall_risk_score": 0.0,
            "segments": segments,
            "waypoints": waypoints,
        })
    return result
