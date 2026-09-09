"""Navigation routes: /navigation/route, /navigation/replan, /health"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter

from app.models.schemas import (
    RouteRequest, RouteResponse, ReplanRequest,
    HealthResponse, RouteWaypoint, RiskBreakdown,
)
from app.services.cache_service import get_cache
from app.services.icenet_service import get_icenet
from app.services.routing_service import get_routing
from app.services.bathymetry_service import get_bathymetry
from loguru import logger

router = APIRouter(tags=["Navigation"])


@router.post("/navigation/route", response_model=RouteResponse)
async def plan_route(req: RouteRequest):
    """
    Plan an optimized A* route from start to end, avoiding sea ice and icebergs.

    - Loads current sea-ice concentration from IceNet
    - Loads current iceberg positions from drift model
    - A* finds minimum-risk path respecting ship ice class limits
    - Returns waypoints, distance, ETA, fuel estimate, risk breakdown, and explanation
    """
    cache = get_cache()
    cache_key = cache.make_key(
        "route",
        f"{req.start_lat:.3f}", f"{req.start_lon:.3f}",
        f"{req.end_lat:.3f}", f"{req.end_lon:.3f}",
        req.ship_type.value,
    )

    cached = await cache.get(cache_key)
    if cached:
        logger.debug("Route cache hit")
        return RouteResponse(**cached)

    # Load ice grid into router
    routing = get_routing()
    icenet = get_icenet()
    ice_cells = icenet.forecast(lead_day=0)
    routing.update_ice_grid(ice_cells)

    # Load icebergs into router
    from app.routes.icebergs import _load_byu_icebergs
    routing.update_icebergs(_load_byu_icebergs())

    # Run A* routing
    result = routing.find_route(
        start_lat=req.start_lat,
        start_lon=req.start_lon,
        end_lat=req.end_lat,
        end_lon=req.end_lon,
        ship_type=req.ship_type.value,
        min_depth_m=req.min_depth_m,
        avoid_icebergs=req.avoid_icebergs,
    )

    # Build response
    waypoints = [RouteWaypoint(**wp) for wp in result["waypoints"]]
    rb = RiskBreakdown(**result["risk_breakdown"])
    response = RouteResponse(
        route_id=result["route_id"],
        waypoints=waypoints,
        distance_km=result["distance_km"],
        eta_hours=result["eta_hours"],
        fuel_estimate_tons=result.get("fuel_estimate_tons"),
        risk_score=result["risk_score"],
        risk_breakdown=rb,
        explanation=result["explanation"],
        alternatives=[],
        timestamp=datetime.utcnow(),
    )

    await cache.set(cache_key, response.model_dump(mode="json"), ttl=1800)  # 30 min cache

    logger.info("Route planned: {}km, ETA {}h, risk {:.2f}",
                result["distance_km"], result["eta_hours"], result["risk_score"])
    return response


@router.post("/navigation/replan", response_model=RouteResponse)
async def replan_route(req: ReplanRequest):
    """
    Replan route from current position (e.g., after deviation or new hazard detected).
    Bypasses route cache and forces fresh A* calculation.
    """
    fresh_req = RouteRequest(
        start_lat=req.current_lat,
        start_lon=req.current_lon,
        end_lat=req.end_lat,
        end_lon=req.end_lon,
        ship_type=req.ship_type,
    )

    # Invalidate old route cache
    cache = get_cache()
    cache_key = cache.make_key(
        "route",
        f"{req.current_lat:.3f}", f"{req.current_lon:.3f}",
        f"{req.end_lat:.3f}", f"{req.end_lon:.3f}",
        req.ship_type.value,
    )
    await cache.delete(cache_key)

    return await plan_route(fresh_req)


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """System health check: verifies all services and model status."""
    from app.services.cache_service import get_cache

    services = {}
    models = {}

    # Check cache
    cache = get_cache()
    try:
        await cache.set("_health", "ok", ttl=10)
        services["cache"] = "ok" if cache._redis_ok else "disk_only"
    except Exception:
        services["cache"] = "error"

    # Check bathymetry
    bathy = get_bathymetry()
    services["bathymetry"] = "loaded" if bathy._loaded else "physics_model"

    # Check IceNet
    icenet = get_icenet()
    models["icenet"] = "pretrained" if not icenet._use_physics else "physics_fallback"

    # Check DRIFT
    from app.services.drift_service import get_drift
    drift = get_drift()
    models["drift"] = "pretrained" if not drift._use_physics else "physics_fallback"

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow(),
        services=services,
        models=models,
    )
