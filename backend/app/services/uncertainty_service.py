"""MC-Dropout uncertainty estimation for trajectory cones."""
from __future__ import annotations

import math
from typing import Any

import numpy as np


def compute_uncertainty_cone(
    trajectories: list[list[dict]],
    n_sigma: float = 2.0,
) -> list[dict]:
    """
    Given MC-Dropout ensemble trajectories, compute a Gaussian uncertainty cone.

    Args:
        trajectories: List of trajectory paths (each is list of {lat, lon, timestamp, ...})
        n_sigma: Number of standard deviations for cone width

    Returns:
        List of {timestamp, center_lat, center_lon, radius_km, sigma_lat, sigma_lon}
    """
    if not trajectories:
        return []

    n_steps = min(len(t) for t in trajectories)
    cone = []

    for step_idx in range(n_steps):
        lats = [t[step_idx]["lat"] for t in trajectories]
        lons = [t[step_idx]["lon"] for t in trajectories]

        mean_lat = float(np.mean(lats))
        mean_lon = float(np.mean(lons))
        std_lat = float(np.std(lats))
        std_lon = float(np.std(lons))

        # Convert std to km
        radius_km = n_sigma * math.sqrt(
            (std_lat * 111.32) ** 2 + (std_lon * 111.32 * math.cos(math.radians(mean_lat))) ** 2
        )

        cone.append({
            "timestamp": trajectories[0][step_idx]["timestamp"],
            "center_lat": round(mean_lat, 6),
            "center_lon": round(mean_lon, 6),
            "radius_km": round(radius_km, 2),
            "sigma_lat": round(std_lat, 6),
            "sigma_lon": round(std_lon, 6),
        })

    return cone


def ensemble_spread_to_color(radius_km: float, max_radius_km: float = 200.0) -> str:
    """Map uncertainty radius to a hex color (cyan → red)."""
    t = min(1.0, radius_km / max_radius_km)
    r = int(255 * t)
    g = int(255 * (1 - t))
    b = int(200 * (1 - t))
    return f"#{r:02x}{g:02x}{b:02x}"
