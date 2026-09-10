"""Navigation routes: /navigation/route, /navigation/replan, /health"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from loguru import logger

from app.models.schemas import (
    RouteRequest, RouteResponse, ReplanRequest,
    HealthResponse, RouteWaypoint, RiskBreakdown, IngestionStatus,
)
from app.services.cache_service import get_cache
from app.services.icenet_service import get_icenet
from app.services.routing_service import get_routing
from app.services.bathymetry_service import get_bathymetry

router = APIRouter(tags=["Navigation"])


def _load_router_state(routing) -> None:
    """
    Populate the A* router's ice grid and iceberg hash from the ingestion service.
    Falls back to IceNet physics forecast if ingestion data not ready.
    """
    # Ice grid: prefer ingested NSIDC grid, fall back to IceNet physics
    from app.services.ingestion_service import get_ingestion
    ingestion = get_ingestion()

    sic_cells = ingestion.get_sic_cells()
    if not sic_cells:
        logger.info("Navigation: ingested SIC grid empty, using IceNet forecast")
        icenet    = get_icenet()
        sic_cells = icenet.forecast(lead_day=0)

    routing.update_ice_grid(sic_cells)
    logger.debug("Router: ice grid loaded ({} cells)", len(sic_cells))

    # Icebergs: from ingested CSV
    icebergs = ingestion.get_icebergs()
    routing.update_icebergs(icebergs)
    logger.debug("Router: iceberg index loaded ({} bergs)", len(icebergs))


@router.post("/navigation/route", response_model=RouteResponse)
async def plan_route(req: RouteRequest):
    """
    Plan an A* optimized route across the Southern Ocean.

    **Cost function**: distance × (1 + 3 × risk)
    **Risk components** (weighted):
    - Sea ice (40%): from NSIDC ingested SIC grid / IceNet U-Net
    - Iceberg proximity (30%): spatial hash, 10km exclusion / 50km caution zones
    - Bathymetry (20%): GEBCO depth, grounding avoidance
    - Weather (10%): Open-Meteo wind speed risk

    **Ship ice class limits** (POLAR Code):
    - `open_water` → SIC ≤ 10%
    - `ice_class_1a` → SIC ≤ 70%
    - `icebreaker` → SIC ≤ 100%

    Returns waypoints, distance, ETA, fuel estimate (HFO tons), risk breakdown,
    and natural-language explanation.
    """
    cache     = get_cache()
    cache_key = cache.make_key(
        "route",
        f"{req.start_lat:.2f}", f"{req.start_lon:.2f}",
        f"{req.end_lat:.2f}",  f"{req.end_lon:.2f}",
        req.ship_type.value,
    )

    cached = await cache.get(cache_key)
    if cached:
        logger.debug("Route cache hit")
        return RouteResponse(**cached)

    # Load state into router
    routing = get_routing()
    _load_router_state(routing)

    # A* route finding
    result = routing.find_route(
        start_lat      = req.start_lat,
        start_lon      = req.start_lon,
        end_lat        = req.end_lat,
        end_lon        = req.end_lon,
        ship_type      = req.ship_type.value,
        min_depth_m    = req.min_depth_m,
        avoid_icebergs = req.avoid_icebergs,
    )

    waypoints = [RouteWaypoint(**wp) for wp in result["waypoints"]]
    rb        = RiskBreakdown(**result["risk_breakdown"])
    response  = RouteResponse(
        route_id          = result["route_id"],
        waypoints         = waypoints,
        distance_km       = result["distance_km"],
        eta_hours         = result["eta_hours"],
        fuel_estimate_tons= result.get("fuel_estimate_tons"),
        risk_score        = result["risk_score"],
        risk_breakdown    = rb,
        explanation       = result["explanation"],
        alternatives      = [],
        timestamp         = datetime.now(tz=timezone.utc),
    )

    await cache.set(cache_key, response.model_dump(mode="json"), ttl=1800)

    logger.info(
        "Route planned: {:.0f}km ETA {:.1f}h risk {:.3f} [{}]",
        result["distance_km"], result["eta_hours"], result["risk_score"],
        req.ship_type.value,
    )
    return response


@router.post("/navigation/replan", response_model=RouteResponse)
async def replan_route(req: ReplanRequest):
    """
    Emergency replan from current position.
    Bypasses cache and forces fresh A* calculation with latest hazard data.
    """
    fresh_req = RouteRequest(
        start_lat  = req.current_lat,
        start_lon  = req.current_lon,
        end_lat    = req.end_lat,
        end_lon    = req.end_lon,
        ship_type  = req.ship_type,
    )

    # Invalidate old cache entry
    cache     = get_cache()
    cache_key = cache.make_key(
        "route",
        f"{req.current_lat:.2f}", f"{req.current_lon:.2f}",
        f"{req.end_lat:.2f}",    f"{req.end_lon:.2f}",
        req.ship_type.value,
    )
    await cache.delete(cache_key)

    logger.info("Route replan triggered from ({:.3f}, {:.3f})", req.current_lat, req.current_lon)
    return await plan_route(fresh_req)


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Comprehensive system health check.
    Reports status of: cache, bathymetry, IceNet, DRIFT, ingestion service.
    """
    services: dict[str, str] = {}
    models:   dict[str, str] = {}

    # Cache
    cache = get_cache()
    try:
        await cache.set("_health", "ok", ttl=10)
        services["cache"] = "redis" if getattr(cache, "_redis_ok", False) else "disk_fallback"
    except Exception:
        services["cache"] = "error"

    # Bathymetry
    bathy = get_bathymetry()
    services["bathymetry"] = "gebco_loaded" if bathy._loaded else "physics_model"

    # IceNet
    icenet = get_icenet()
    models["icenet"] = "pretrained_unet" if not icenet._use_physics else "physics_seasonal"
    ingested_cells   = len(icenet._ingested_grid)
    models["icenet_grid"] = f"{ingested_cells}_cells_ingested"

    # DRIFT
    from app.services.drift_service import get_drift
    drift = get_drift()
    models["drift"] = "lstm_pretrained" if not drift._use_physics else "rk4_physics"

    # Ingestion service
    from app.services.ingestion_service import get_ingestion
    ingestion = get_ingestion()
    ing_status = ingestion.status()
    services["ingestion"] = (
        f"ok:{ing_status['icebergs_loaded']}bergs,"
        f"{ing_status['sic_cells_loaded']}SIC,"
        f"{ing_status['routes_loaded']}routes"
    )
    if ing_status.get("data_age_hours"):
        services["data_age"] = f"{ing_status['data_age_hours']:.1f}h"

    return HealthResponse(
        status    = "healthy",
        version   = "2.0.0",
        timestamp = datetime.now(tz=timezone.utc),
        services  = services,
        models    = models,
        ingestion = IngestionStatus(**ing_status),
    )
