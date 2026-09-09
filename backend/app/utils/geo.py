"""Geospatial utility functions for IceNavigator."""
from __future__ import annotations

import math
from typing import Tuple


# ─────────────────────────── Constants ────────────────────────────────────────

EARTH_RADIUS_KM = 6371.0
EARTH_RADIUS_M = 6_371_000.0


# ─────────────────────────── Core Functions ───────────────────────────────────

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres between two (lat, lon) points."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing (0–360°) from point 1 to point 2."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlambda = math.radians(lon2 - lon1)
    x = math.sin(dlambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def destination_point(lat: float, lon: float, bearing_deg_val: float, distance_km: float) -> Tuple[float, float]:
    """
    Compute destination given start, bearing, and distance.
    Returns (lat, lon).
    """
    d = distance_km / EARTH_RADIUS_KM
    phi1 = math.radians(lat)
    lam1 = math.radians(lon)
    theta = math.radians(bearing_deg_val)

    phi2 = math.asin(
        math.sin(phi1) * math.cos(d) + math.cos(phi1) * math.sin(d) * math.cos(theta)
    )
    lam2 = lam1 + math.atan2(
        math.sin(theta) * math.sin(d) * math.cos(phi1),
        math.cos(d) - math.sin(phi1) * math.sin(phi2),
    )
    return math.degrees(phi2), math.degrees(lam2)


def latlon_to_grid_index(lat: float, lon: float, lat_min: float, lon_min: float,
                          lat_step: float, lon_step: float) -> Tuple[int, int]:
    """Convert geographic coordinate to nearest grid cell indices (row, col)."""
    row = round((lat - lat_min) / lat_step)
    col = round((lon - lon_min) / lon_step)
    return row, col


def grid_index_to_latlon(row: int, col: int, lat_min: float, lon_min: float,
                          lat_step: float, lon_step: float) -> Tuple[float, float]:
    """Convert grid cell indices to center geographic coordinate."""
    lat = lat_min + row * lat_step
    lon = lon_min + col * lon_step
    return lat, lon


def clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, value))


def normalize_lon(lon: float) -> float:
    """Normalize longitude to [-180, 180]."""
    while lon > 180:
        lon -= 360
    while lon < -180:
        lon += 360
    return lon


def bounding_box(lat: float, lon: float, radius_km: float):
    """Return (lat_min, lat_max, lon_min, lon_max) bounding box for circle."""
    dlat = math.degrees(radius_km / EARTH_RADIUS_KM)
    dlon = math.degrees(radius_km / (EARTH_RADIUS_KM * math.cos(math.radians(lat))))
    return lat - dlat, lat + dlat, lon - dlon, lon + dlon


def interpolate_path(lat1: float, lon1: float, lat2: float, lon2: float, n_points: int = 10):
    """Generate n_points great-circle interpolated waypoints between two positions."""
    points = []
    for i in range(n_points + 1):
        t = i / n_points
        points.append((lat1 + t * (lat2 - lat1), lon1 + t * (lon2 - lon1)))
    return points
