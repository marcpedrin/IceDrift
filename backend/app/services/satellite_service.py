"""Sentinel Hub OGC WMS client for iceberg satellite imagery."""
from __future__ import annotations

import base64
from typing import Optional

import httpx
from loguru import logger


# Sentinel-2 True Color WMS parameters
SENTINEL_WMS_TEMPLATE = (
    "https://services.sentinel-hub.com/ogc/wms/{instance_id}"
    "?SERVICE=WMS&REQUEST=GetMap&LAYERS=TRUE_COLOR&STYLES="
    "&FORMAT=image%2Fpng&TRANSPARENT=true&VERSION=1.1.1"
    "&WIDTH=512&HEIGHT=512&SRS=EPSG%3A4326"
    "&BBOX={lon_min},{lat_min},{lon_max},{lat_max}"
    "&TIME={date}"
)

# Fallback: public GIBS NASA imagery (no auth required)
NASA_GIBS_TEMPLATE = (
    "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
    "?SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0"
    "&LAYERS=MODIS_Terra_CorrectedReflectance_TrueColor"
    "&FORMAT=image/png&WIDTH=512&HEIGHT=512"
    "&CRS=EPSG:4326"
    "&BBOX={lat_min},{lon_min},{lat_max},{lon_max}"
    "&TIME={date}"
)


class SatelliteService:
    """Fetches satellite imagery for iceberg locations."""

    def __init__(self, client_id: str = "", client_secret: str = "", instance_id: str = ""):
        self.client_id = client_id
        self.client_secret = client_secret
        self.instance_id = instance_id
        self._token: Optional[str] = None

    async def get_iceberg_image_url(
        self,
        lat: float,
        lon: float,
        date: str = "2024-09-01",
        radius_deg: float = 0.05,
    ) -> str:
        """
        Return a WMS URL for satellite imagery around the iceberg location.
        Uses Sentinel Hub if credentials available, otherwise falls back to NASA GIBS.
        """
        lat_min = lat - radius_deg
        lat_max = lat + radius_deg
        lon_min = lon - radius_deg
        lon_max = lon + radius_deg

        if self.instance_id:
            return SENTINEL_WMS_TEMPLATE.format(
                instance_id=self.instance_id,
                lat_min=lat_min, lat_max=lat_max,
                lon_min=lon_min, lon_max=lon_max,
                date=date,
            )

        # NASA GIBS fallback (public, no auth needed)
        return NASA_GIBS_TEMPLATE.format(
            lat_min=lat_min, lat_max=lat_max,
            lon_min=lon_min, lon_max=lon_max,
            date=date,
        )

    async def fetch_image_base64(self, url: str) -> Optional[str]:
        """Fetch image and return as base64 string for embedding."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return base64.b64encode(resp.content).decode("utf-8")
        except Exception as exc:
            logger.warning("Satellite image fetch failed: {}", exc)
        return None


_satellite_instance: Optional[SatelliteService] = None


def get_satellite() -> SatelliteService:
    global _satellite_instance
    if _satellite_instance is None:
        from config import get_settings
        s = get_settings()
        _satellite_instance = SatelliteService(
            client_id=s.sentinel_hub_client_id,
            client_secret=s.sentinel_hub_client_secret,
            instance_id=s.sentinel_hub_instance_id,
        )
    return _satellite_instance
