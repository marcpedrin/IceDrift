"""AIS ship tracking service – MarineTraffic API with rich mock fallback."""
from __future__ import annotations

import random
import math
from datetime import datetime, timedelta
from typing import Optional

import httpx
from loguru import logger


SHIP_TYPES = ["cargo", "tanker", "passenger", "icebreaker", "research", "supply"]
FLAGS = ["NO", "GB", "US", "AU", "AR", "CL", "RU", "DE", "FR", "JP"]

MOCK_SHIPS = [
    {"mmsi": "257123456", "name": "MV ARCTIC SUNRISE", "ship_type": "research",
     "lat": -62.5, "lon": -45.2, "speed_knots": 8.2, "course_deg": 215, "destination": "McMurdo Station", "flag": "NO", "length_m": 50.0},
    {"mmsi": "319001234", "name": "SA AGULHAS II", "ship_type": "research",
     "lat": -56.1, "lon": 2.3, "speed_knots": 12.5, "course_deg": 180, "destination": "Cape Town", "flag": "ZA", "length_m": 134.0},
    {"mmsi": "477123456", "name": "XUELONG 2", "ship_type": "research",
     "lat": -68.2, "lon": 76.5, "speed_knots": 6.8, "course_deg": 120, "destination": "Zhongshan Station", "flag": "CN", "length_m": 122.0},
    {"mmsi": "273456789", "name": "ADMIRAL VLADIMIRSKY", "ship_type": "icebreaker",
     "lat": -69.8, "lon": -5.4, "speed_knots": 14.2, "course_deg": 90, "destination": "Mirny Station", "flag": "RU", "length_m": 162.0},
    {"mmsi": "512345678", "name": "RRS DISCOVERY", "ship_type": "research",
     "lat": -60.3, "lon": -40.1, "speed_knots": 10.1, "course_deg": 340, "destination": "Stanley", "flag": "GB", "length_m": 100.0},
    {"mmsi": "701234567", "name": "NATHANIEL B. PALMER", "ship_type": "research",
     "lat": -64.7, "lon": -63.2, "speed_knots": 7.5, "course_deg": 260, "destination": "Palmer Station", "flag": "US", "length_m": 94.0},
    {"mmsi": "710987654", "name": "BETANZOS", "ship_type": "supply",
     "lat": -63.1, "lon": -57.8, "speed_knots": 9.3, "course_deg": 155, "destination": "King George Island", "flag": "CL", "length_m": 80.0},
    {"mmsi": "209876543", "name": "MV OCEAN VICTORY", "ship_type": "passenger",
     "lat": -58.4, "lon": -26.7, "speed_knots": 15.0, "course_deg": 310, "destination": "Ushuaia", "flag": "BS", "length_m": 115.0},
]


def _generate_history(lat: float, lon: float, course_deg: float, speed_knots: float, n_hours: int = 24) -> list[dict]:
    """Generate last 24h position history (reverse-interpolate from current position)."""
    history = []
    speed_kmh = speed_knots * 1.852
    for i in range(n_hours, 0, -1):
        dist_km = speed_kmh * i
        rev_bearing = (course_deg + 180) % 360
        dlat = (dist_km / 111.32) * math.cos(math.radians(rev_bearing))
        dlon = (dist_km / (111.32 * math.cos(math.radians(lat)))) * math.sin(math.radians(rev_bearing))
        history.append({
            "lat": round(lat + dlat, 4),
            "lon": round(lon + dlon, 4),
            "timestamp": (datetime.utcnow() - timedelta(hours=i)).isoformat(),
        })
    return history


class AISService:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self._base_url = "https://services.marinetraffic.com/api"

    async def get_nearby_ships(
        self,
        lat: float = -65.0,
        lon: float = 0.0,
        radius_nm: float = 500.0,
    ) -> list[dict]:
        """Fetch ships from MarineTraffic API, or return mock data."""
        if self.api_key:
            try:
                return await self._fetch_from_api(lat, lon, radius_nm)
            except Exception as exc:
                logger.warning("MarineTraffic API failed: {}. Using mock data.", exc)
        return self._mock_ships()

    async def _fetch_from_api(self, lat: float, lon: float, radius_nm: float) -> list[dict]:
        url = f"{self._base_url}/exportvessels/v:8/{self.api_key}/MINLAT:{lat - 5}/MAXLAT:{lat + 5}/MINLON:{lon - 10}/MAXLON:{lon + 10}/protocol:jsono"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return [self._parse_vessel(v) for v in data.get("DATA", [])]

    @staticmethod
    def _parse_vessel(v: dict) -> dict:
        return {
            "mmsi": str(v.get("MMSI", "")),
            "name": v.get("SHIPNAME", "Unknown"),
            "ship_type": v.get("TYPE_NAME", "unknown").lower(),
            "lat": float(v.get("LAT", 0)),
            "lon": float(v.get("LON", 0)),
            "speed_knots": float(v.get("SPEED", 0)) / 10,
            "course_deg": float(v.get("COURSE", 0)),
            "destination": v.get("DESTINATION", ""),
            "flag": v.get("FLAG", ""),
            "length_m": float(v.get("LENGTH", 0)),
            "history": [],
            "last_updated": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def _mock_ships() -> list[dict]:
        ships = []
        for s in MOCK_SHIPS:
            ship = dict(s)
            ship["history"] = _generate_history(
                s["lat"], s["lon"], s["course_deg"], s["speed_knots"]
            )
            ship["last_updated"] = datetime.utcnow().isoformat()
            ships.append(ship)
        return ships


_ais_instance: Optional[AISService] = None


def get_ais() -> AISService:
    global _ais_instance
    if _ais_instance is None:
        from config import get_settings
        s = get_settings()
        _ais_instance = AISService(api_key=s.marinetraffic_api_key)
    return _ais_instance
