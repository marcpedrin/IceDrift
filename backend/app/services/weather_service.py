"""Free Weather Service using Open-Meteo API (100% free, no API key required)."""
from __future__ import annotations

import math
from typing import Optional

import httpx
from loguru import logger

from app.services.cache_service import get_cache


class WeatherService:
    """
    Fetches real-time atmospheric and wind conditions for Antarctic coordinates
    using the Open-Meteo public API (free, open data, zero authentication).
    """

    def __init__(self, base_url: str = "https://api.open-meteo.com/v1"):
        self.base_url = base_url.rstrip("/")

    async def get_current_weather(self, lat: float, lon: float) -> dict:
        """
        Fetch current temperature, wind speed, direction, and pressure.
        Returns dictionary with raw values and decomposed (u, v) wind vectors in m/s.
        """
        cache = get_cache()
        cache_key = cache.make_key("weather", f"{lat:.1f}", f"{lon:.1f}")

        cached = await cache.get(cache_key)
        if cached:
            return cached

        # Fetch from Open-Meteo
        url = (
            f"{self.base_url}/forecast"
            f"?latitude={lat:.4f}&longitude={lon:.4f}"
            f"&current=temperature_2m,wind_speed_10m,wind_direction_10m,surface_pressure"
            f"&wind_speed_unit=ms"
        )

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

            current = data.get("current", {})
            temp_c = float(current.get("temperature_2m", -12.0))
            speed_ms = float(current.get("wind_speed_10m", 6.5))
            dir_deg = float(current.get("wind_direction_10m", 240.0))
            pressure_hpa = float(current.get("surface_pressure", 990.0))

            # Meteorological to Cartesian (u: eastward, v: northward)
            dir_rad = math.radians(dir_deg)
            wind_u = round(-speed_ms * math.sin(dir_rad), 3)
            wind_v = round(-speed_ms * math.cos(dir_rad), 3)

            result = {
                "latitude": lat,
                "longitude": lon,
                "temperature_c": temp_c,
                "wind_speed_ms": speed_ms,
                "wind_direction_deg": dir_deg,
                "wind_u": wind_u,
                "wind_v": wind_v,
                "surface_pressure_hpa": pressure_hpa,
                "source": "Open-Meteo Free API",
                "cached": False,
            }

            from config import get_settings
            ttl = get_settings().weather_cache_ttl
            await cache.set(cache_key, result, ttl=ttl)
            return result

        except Exception as exc:
            logger.warning("Open-Meteo weather fetch failed ({}), using polar climatology.", exc)
            return self._fallback_weather(lat, lon)

    def get_current_weather_sync(self, lat: float, lon: float) -> dict:
        """Synchronous version for model pipelines."""
        try:
            url = (
                f"{self.base_url}/forecast"
                f"?latitude={lat:.4f}&longitude={lon:.4f}"
                f"&current=temperature_2m,wind_speed_10m,wind_direction_10m,surface_pressure"
                f"&wind_speed_unit=ms"
            )
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    current = data.get("current", {})
                    speed_ms = float(current.get("wind_speed_10m", 6.5))
                    dir_deg = float(current.get("wind_direction_10m", 240.0))
                    dir_rad = math.radians(dir_deg)
                    return {
                        "latitude": lat,
                        "longitude": lon,
                        "temperature_c": float(current.get("temperature_2m", -12.0)),
                        "wind_speed_ms": speed_ms,
                        "wind_direction_deg": dir_deg,
                        "wind_u": round(-speed_ms * math.sin(dir_rad), 3),
                        "wind_v": round(-speed_ms * math.cos(dir_rad), 3),
                        "surface_pressure_hpa": float(current.get("surface_pressure", 990.0)),
                        "source": "Open-Meteo Free API",
                    }
        except Exception:
            pass
        return self._fallback_weather(lat, lon)

    @staticmethod
    def _fallback_weather(lat: float, lon: float) -> dict:
        """Realistic Southern Ocean katabatic/westerlies wind climatology."""
        # Dominant Southern Ocean westerlies (west-to-east at -50° to -65°S)
        # Katabatic easterlies near Antarctic coast (<-65°S)
        if lat < -65.0:
            wind_u = 3.5   # Easterly/offshore component
            wind_v = -4.0  # Katabatic northward flow
            speed = 5.3
            direction = 135.0
            temp = -18.5
        else:
            wind_u = -6.5  # Strong westerlies
            wind_v = 2.0
            speed = 6.8
            direction = 250.0
            temp = -5.0

        return {
            "latitude": lat,
            "longitude": lon,
            "temperature_c": temp,
            "wind_speed_ms": speed,
            "wind_direction_deg": direction,
            "wind_u": wind_u,
            "wind_v": wind_v,
            "surface_pressure_hpa": 985.0,
            "source": "Southern Ocean Climatology (Offline Fallback)",
        }


_weather_instance: Optional[WeatherService] = None


def get_weather() -> WeatherService:
    global _weather_instance
    if _weather_instance is None:
        from config import get_settings
        s = get_settings()
        _weather_instance = WeatherService(base_url=s.open_meteo_url)
    return _weather_instance
