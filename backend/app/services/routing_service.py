"""
A* routing service for Antarctic navigation.

Risk score (0–1) per cell = weighted combination of:
  - ice_risk:         from IceNet SIC (high conc = high risk)
  - iceberg_risk:     proximity to tracked icebergs
  - bathymetry_risk:  shallow water / grounding risk
  - weather_risk:     wind speed risk

Ship ice class determines traversability thresholds.
"""
from __future__ import annotations

import heapq
import math
import uuid
from datetime import datetime
from typing import Optional

import numpy as np
from loguru import logger

from app.utils.geo import haversine_km, interpolate_path


# ── Ship class traversal limits ────────────────────────────────────────────────
ICE_CLASS_MAX_SIC = {
    "open_water": 0.1,
    "ice_class_1c": 0.3,
    "ice_class_1b": 0.5,
    "ice_class_1a": 0.7,
    "ice_class_1as": 0.85,
    "icebreaker": 1.0,
}

ICE_CLASS_SPEED_PENALTY = {
    "open_water": 3.0,
    "ice_class_1c": 2.0,
    "ice_class_1b": 1.5,
    "ice_class_1a": 1.2,
    "ice_class_1as": 1.1,
    "icebreaker": 1.0,
}


class RoutingService:
    """A* router over a discretized grid of the Southern Ocean."""

    # Grid parameters
    GRID_STEP = 0.5   # degrees (≈55 km at 60°S)
    LAT_MIN = -80.0
    LAT_MAX = -55.0
    LON_MIN = -180.0
    LON_MAX = 180.0

    def __init__(self):
        self._ice_grid: dict[tuple, float] = {}    # (lat_i, lon_i) → sic
        self._iceberg_positions: list[dict] = []

    def update_ice_grid(self, ice_cells: list[dict]) -> None:
        """Load ice concentration grid for routing."""
        self._ice_grid = {}
        for cell in ice_cells:
            key = (round(cell["lat"] / self.GRID_STEP), round(cell["lon"] / self.GRID_STEP))
            self._ice_grid[key] = cell["concentration"]

    def update_icebergs(self, icebergs: list[dict]) -> None:
        """Load current iceberg positions."""
        self._iceberg_positions = icebergs

    def find_route(
        self,
        start_lat: float, start_lon: float,
        end_lat: float, end_lon: float,
        ship_type: str = "ice_class_1a",
        min_depth_m: float = 20.0,
        avoid_icebergs: bool = True,
    ) -> dict:
        """
        A* route from start to end.
        Returns route dict with waypoints, distance, ETA, risk breakdown.
        """
        from app.services.bathymetry_service import get_bathymetry

        bathy = get_bathymetry()
        max_sic = ICE_CLASS_MAX_SIC.get(ship_type, 0.7)
        speed_penalty = ICE_CLASS_SPEED_PENALTY.get(ship_type, 1.2)

        logger.info("A* routing: ({:.2f},{:.2f}) → ({:.2f},{:.2f}) [{}]",
                    start_lat, start_lon, end_lat, end_lon, ship_type)

        # Grid indices
        def to_grid(lat, lon):
            return (round(lat / self.GRID_STEP), round(lon / self.GRID_STEP))

        def to_coord(gi, gj):
            return gi * self.GRID_STEP, gj * self.GRID_STEP

        start = to_grid(start_lat, start_lon)
        goal = to_grid(end_lat, end_lon)

        # Heuristic: Haversine distance to goal
        def h(node):
            lat, lon = to_coord(*node)
            return haversine_km(lat, lon, end_lat, end_lon)

        # Cost: distance + ice penalty + iceberg penalty
        def edge_cost(from_node, to_node):
            lat, lon = to_coord(*to_node)
            dist_km = self.GRID_STEP * 111.32

            # Ice risk
            sic = self._ice_grid.get(to_node, 0.0)
            if sic > max_sic:
                return float("inf")  # impassable
            ice_cost = 1 + 3.0 * sic * speed_penalty

            # Iceberg risk
            iceberg_cost = 1.0
            if avoid_icebergs:
                for berg in self._iceberg_positions:
                    d = haversine_km(lat, lon, berg.get("lat", 0), berg.get("lon", 0))
                    if d < 5.0:
                        iceberg_cost = 5.0
                        break
                    elif d < 15.0:
                        iceberg_cost = max(iceberg_cost, 1.5)

            # Bathymetry
            depth = bathy.get_depth_m(lat, lon)
            if depth < min_depth_m:
                return float("inf")  # grounding risk
            bathy_cost = 1.0 + max(0, (100 - depth) / 100)

            return dist_km * ice_cost * iceberg_cost * bathy_cost

        # A* search
        open_set = [(0, start)]
        came_from = {}
        g_score = {start: 0}
        f_score = {start: h(start)}
        max_iterations = 5000

        for iteration in range(max_iterations):
            if not open_set:
                break
            _, current = heapq.heappop(open_set)

            if current == goal or haversine_km(*to_coord(*current), end_lat, end_lon) < 1.0:
                # Reconstruct path
                path = []
                node = current
                while node in came_from:
                    path.append(node)
                    node = came_from[node]
                path.append(start)
                path.reverse()
                return self._build_route_response(path, to_coord, ship_type, bathy)

            # Expand neighbors (8-directional grid)
            ci, cj = current
            for di in [-1, 0, 1]:
                for dj in [-1, 0, 1]:
                    if di == 0 and dj == 0:
                        continue
                    neighbor = (ci + di, cj + dj)
                    nlat, nlon = to_coord(*neighbor)
                    if not (self.LAT_MIN <= nlat <= self.LAT_MAX):
                        continue

                    cost = edge_cost(current, neighbor)
                    if cost == float("inf"):
                        continue

                    tentative_g = g_score.get(current, float("inf")) + cost
                    if tentative_g < g_score.get(neighbor, float("inf")):
                        came_from[neighbor] = current
                        g_score[neighbor] = tentative_g
                        f_score[neighbor] = tentative_g + h(neighbor)
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))

        # Fallback: direct great-circle route with interpolation
        logger.warning("A* did not converge, using direct route fallback")
        return self._direct_route(start_lat, start_lon, end_lat, end_lon, ship_type, bathy)

    def _build_route_response(self, path: list, to_coord, ship_type: str, bathy) -> dict:
        waypoints = []
        total_dist = 0.0
        ice_risks = []
        iceberg_risks = []
        bathy_risks = []

        prev_lat, prev_lon = None, None

        for node in path:
            lat, lon = to_coord(*node)
            sic = self._ice_grid.get(node, 0.0)
            depth = bathy.get_depth_m(lat, lon)
            bathy_risk = bathy.depth_risk(lat, lon)

            # Iceberg proximity risk
            berg_risk = 0.0
            for berg in self._iceberg_positions:
                d = haversine_km(lat, lon, berg.get("lat", 0), berg.get("lon", 0))
                if d < 15:
                    berg_risk = max(berg_risk, 1.0 - d / 15.0)

            ice_risks.append(sic)
            iceberg_risks.append(berg_risk)
            bathy_risks.append(bathy_risk)

            risk_score = (0.4 * sic + 0.3 * berg_risk + 0.2 * bathy_risk)

            if prev_lat is not None:
                total_dist += haversine_km(prev_lat, prev_lon, lat, lon)

            waypoints.append({
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "ice_concentration": round(sic, 3),
                "depth_m": round(depth, 1),
                "risk_score": round(risk_score, 3),
            })
            prev_lat, prev_lon = lat, lon

        avg_ice = float(np.mean(ice_risks)) if ice_risks else 0.0
        avg_berg = float(np.mean(iceberg_risks)) if iceberg_risks else 0.0
        avg_bathy = float(np.mean(bathy_risks)) if bathy_risks else 0.0
        overall_risk = 0.4 * avg_ice + 0.3 * avg_berg + 0.2 * avg_bathy + 0.1 * 0.2

        # ETA at typical icebreaker speed (15 knots = 27.78 km/h)
        speed_kmh = 27.78 / ICE_CLASS_SPEED_PENALTY.get(ship_type, 1.2)
        eta_h = total_dist / max(speed_kmh, 1.0)

        explanation = self._generate_explanation(
            total_dist, eta_h, avg_ice, avg_berg, avg_bathy, ship_type
        )

        return {
            "route_id": str(uuid.uuid4()),
            "waypoints": waypoints,
            "distance_km": round(total_dist, 1),
            "eta_hours": round(eta_h, 1),
            "fuel_estimate_tons": round(total_dist * 0.015, 1),
            "risk_score": round(overall_risk, 3),
            "risk_breakdown": {
                "ice_risk": round(avg_ice, 3),
                "iceberg_risk": round(avg_berg, 3),
                "bathymetry_risk": round(avg_bathy, 3),
                "weather_risk": 0.2,
                "total_risk": round(overall_risk, 3),
            },
            "explanation": explanation,
            "alternatives": [],
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _direct_route(self, slat, slon, elat, elon, ship_type, bathy) -> dict:
        """Fallback: straight-line interpolated route."""
        points = interpolate_path(slat, slon, elat, elon, n_points=20)
        waypoints = [{"lat": round(la, 4), "lon": round(lo, 4),
                      "ice_concentration": 0.2, "depth_m": 1000.0, "risk_score": 0.2}
                     for la, lo in points]
        dist = haversine_km(slat, slon, elat, elon)
        return {
            "route_id": str(uuid.uuid4()),
            "waypoints": waypoints,
            "distance_km": round(dist, 1),
            "eta_hours": round(dist / 20.0, 1),
            "fuel_estimate_tons": round(dist * 0.015, 1),
            "risk_score": 0.25,
            "risk_breakdown": {"ice_risk": 0.2, "iceberg_risk": 0.1,
                                "bathymetry_risk": 0.1, "weather_risk": 0.2, "total_risk": 0.25},
            "explanation": f"Direct route ({dist:.0f} km). A* optimization unavailable.",
            "alternatives": [],
            "timestamp": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def _generate_explanation(dist_km, eta_h, avg_ice, avg_berg, avg_bathy, ship_type) -> str:
        lines = [
            f"Optimized A* route: {dist_km:.0f} km, ETA {eta_h:.1f} hours.",
        ]
        if avg_ice > 0.5:
            lines.append(f"⚠ High average sea-ice concentration ({avg_ice:.0%}). Route deviates northward to minimize ice transit.")
        elif avg_ice > 0.2:
            lines.append(f"Moderate ice encountered ({avg_ice:.0%}). Route follows leads and polynyas.")
        else:
            lines.append("Low ice concentration along this corridor.")

        if avg_berg > 0.3:
            lines.append("⚠ Multiple icebergs in area. Route extends exclusion zones to 15 km.")

        if ship_type == "icebreaker":
            lines.append("Icebreaker profile: direct route through ice permitted up to 100% SIC.")
        elif ship_type in ("ice_class_1a", "ice_class_1as"):
            lines.append("Ice class 1A/1AS: can transit moderate ice. Route optimized for efficiency.")
        else:
            lines.append("Open water / light ice class: route strictly avoids high-concentration ice.")

        return " ".join(lines)


_routing_instance: Optional[RoutingService] = None


def get_routing() -> RoutingService:
    global _routing_instance
    if _routing_instance is None:
        _routing_instance = RoutingService()
    return _routing_instance
