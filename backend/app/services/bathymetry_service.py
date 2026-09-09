"""GEBCO bathymetry service – loads NetCDF and queries depth at any point."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

import numpy as np
from loguru import logger


class BathymetryService:
    """
    Wraps GEBCO NetCDF bathymetry data.
    Falls back to a simple parameterized depth model if file is missing.
    """

    def __init__(self, gebco_path: str):
        self.gebco_path = Path(gebco_path)
        self._lats: Optional[np.ndarray] = None
        self._lons: Optional[np.ndarray] = None
        self._elevation: Optional[np.ndarray] = None  # positive = above sea level
        self._loaded = False

    def load(self) -> None:
        """Load GEBCO NetCDF. Silently degrades to physics model if missing."""
        if not self.gebco_path.exists():
            logger.warning("GEBCO file not found at {}. Using parameterized depth model.", self.gebco_path)
            return
        try:
            import xarray as xr
            ds = xr.open_dataset(self.gebco_path)
            # GEBCO variable names
            self._lats = ds["lat"].values
            self._lons = ds["lon"].values
            self._elevation = ds["elevation"].values  # shape (nlat, nlon)
            self._loaded = True
            logger.info("GEBCO bathymetry loaded: {}×{} grid", len(self._lats), len(self._lons))
        except Exception as exc:
            logger.error("Failed to load GEBCO: {}. Using parameterized model.", exc)

    def get_depth_m(self, lat: float, lon: float) -> float:
        """
        Returns depth in metres (positive = depth below surface, negative = land).
        """
        if self._loaded and self._elevation is not None:
            return float(-self._nearest_elevation(lat, lon))
        return self._parameterized_depth(lat, lon)

    def is_navigable(self, lat: float, lon: float, min_depth_m: float = 20.0) -> bool:
        """True if depth >= min_depth_m (i.e., not too shallow or land)."""
        depth = self.get_depth_m(lat, lon)
        return depth >= min_depth_m

    def depth_risk(self, lat: float, lon: float, min_depth_m: float = 20.0) -> float:
        """
        Risk score 0–1: 0 = deep, safe; 1 = too shallow / land.
        Ships avoid grounding.
        """
        depth = self.get_depth_m(lat, lon)
        if depth < 0:
            return 1.0  # land
        if depth < min_depth_m:
            return 1.0  # too shallow
        if depth < 100:
            return 1.0 - (depth - min_depth_m) / (100 - min_depth_m)
        return 0.0

    # ── Internal ───────────────────────────────────────────────────────────────

    def _nearest_elevation(self, lat: float, lon: float) -> float:
        lat_idx = int(np.argmin(np.abs(self._lats - lat)))
        lon_idx = int(np.argmin(np.abs(self._lons - lon)))
        return float(self._elevation[lat_idx, lon_idx])

    @staticmethod
    def _parameterized_depth(lat: float, lon: float) -> float:
        """
        Simple physics-based Southern Ocean depth model.
        Most of the Antarctic continental shelf is 400–500 m, open ocean 3000–5000 m.
        """
        abs_lat = abs(lat)
        if abs_lat > 90:
            return -1.0  # out of range
        if abs_lat >= 70:
            # Antarctic continent / ice shelf
            return -50.0  # mostly land/ice
        if abs_lat >= 65:
            # Continental shelf
            return 300.0 + 150.0 * math.sin(math.radians(abs_lat - 65) * 10)
        # Open Southern Ocean
        return 3500.0 + 1000.0 * math.sin(math.radians(abs_lat) * 2)


_bathymetry_instance: Optional[BathymetryService] = None


def get_bathymetry() -> BathymetryService:
    global _bathymetry_instance
    if _bathymetry_instance is None:
        from config import get_settings
        s = get_settings()
        _bathymetry_instance = BathymetryService(s.gebco_path)
        _bathymetry_instance.load()
    return _bathymetry_instance
