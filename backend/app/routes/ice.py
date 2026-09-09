"""Ice forecast route: /ice/forecast"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from loguru import logger

from app.models.schemas import IceForecastResponse, IceCellResponse
from app.services.cache_service import get_cache
from app.services.icenet_service import get_icenet

router = APIRouter(prefix="/ice", tags=["Ice Forecast"])


@router.get("/forecast", response_model=IceForecastResponse)
async def get_ice_forecast(
    lead_day: int = Query(0, ge=0, le=7, description="Forecast lead day (0=today)"),
    date: Optional[str] = Query(None, description="Reference date YYYY-MM-DD (default: today)"),
):
    """
    Return sea-ice concentration (SIC) forecast grid for the Southern Ocean.

    - **lead_day**: Days ahead to forecast (0–7)
    - **date**: Reference date for forecast

    Returns a grid of cells with lat, lon, concentration (0–1), and uncertainty.
    Uses IceNet pretrained model (MC-Dropout) if weights available, else physics model.
    """
    cache = get_cache()
    cache_key = cache.make_key("ice_forecast", str(lead_day), date or "today")

    cached = await cache.get(cache_key)
    if cached:
        logger.debug("Ice forecast cache hit: lead_day={}", lead_day)
        return IceForecastResponse(**cached)

    ref_time = datetime.utcnow()
    if date:
        try:
            ref_time = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            pass

    icenet = get_icenet()
    cells_raw = icenet.forecast(lead_day=lead_day, reference_time=ref_time)

    cells = [IceCellResponse(**c) for c in cells_raw]
    response = IceForecastResponse(
        timestamp=ref_time,
        lead_day=lead_day,
        cells=cells,
        model_version="icenet-v2",
        source="IceNet pretrained (physics fallback)" if icenet._use_physics else "IceNet pretrained",
    )

    # Cache for 6 hours
    from config import get_settings
    ttl = get_settings().ice_cache_ttl
    await cache.set(cache_key, response.model_dump(mode="json"), ttl=ttl)

    logger.info("Ice forecast generated: {} cells, lead_day={}", len(cells), lead_day)
    return response
