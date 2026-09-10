"""Pydantic schemas for all IceNavigator API request/response models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ─────────────────────────── Enums ────────────────────────────────────────────

class ShipType(str, Enum):
    CARGO = "cargo"
    TANKER = "tanker"
    PASSENGER = "passenger"
    ICEBREAKER = "icebreaker"
    RESEARCH = "research"
    SUPPLY = "supply"
    UNKNOWN = "unknown"


class IceClass(str, Enum):
    OPEN_WATER = "open_water"
    ICE_CLASS_1C = "ice_class_1c"
    ICE_CLASS_1B = "ice_class_1b"
    ICE_CLASS_1A = "ice_class_1a"
    ICE_CLASS_1AS = "ice_class_1as"
    ICEBREAKER = "icebreaker"


class RiskLevel(str, Enum):
    SAFE = "safe"          # Green  — SIC < 20%, no icebergs nearby
    MODERATE = "moderate"  # Yellow — SIC 20-60% or iceberg >50km
    HIGH = "high"          # Red    — SIC > 60% or iceberg < 50km or bathymetry risk


# ─────────────────────────── Ice Forecast ─────────────────────────────────────

class IceCellResponse(BaseModel):
    lat: float
    lon: float
    concentration: float = Field(..., ge=0.0, le=1.0, description="Sea ice concentration 0–1")
    uncertainty: float = Field(0.0, ge=0.0, le=1.0)


class IceForecastResponse(BaseModel):
    timestamp: datetime
    lead_day: int = Field(0, ge=0, le=7)
    cells: list[IceCellResponse]
    model_version: str = "icenet-v2"
    source: str = "IceNet pretrained"


# ─────────────────────────── Wind Field ───────────────────────────────────────

class WindCell(BaseModel):
    lat: float
    lon: float
    u10: float = Field(..., description="Eastward wind component m/s")
    v10: float = Field(..., description="Northward wind component m/s")
    speed_ms: float = Field(..., ge=0.0, description="Wind speed magnitude m/s")
    direction_deg: float = Field(..., ge=0.0, le=360.0, description="Meteorological wind direction")
    source: str = "Open-Meteo ERA5"


class WindFieldResponse(BaseModel):
    timestamp: datetime
    source: str
    resolution_deg: float = 1.0
    cells: list[WindCell]
    bbox: dict[str, float]


# ─────────────────────────── Icebergs ─────────────────────────────────────────

class TrajectoryPoint(BaseModel):
    lat: float
    lon: float
    timestamp: datetime
    uncertainty_radius_km: float = 0.0


class IcebergResponse(BaseModel):
    id: str
    lat: float
    lon: float
    size_km2: float
    length_km: float
    width_km: float
    velocity_ms: float
    heading_deg: float
    first_seen: datetime
    last_updated: datetime
    trajectory: list[TrajectoryPoint] = []
    uncertainty_cone: list[dict[str, Any]] = []
    satellite_image_url: Optional[str] = None
    source: str = "BYU/NSIDC"


class IcebergListResponse(BaseModel):
    count: int
    icebergs: list[IcebergResponse]
    timestamp: datetime


# ─────────────────────────── Ships ────────────────────────────────────────────

class ShipPosition(BaseModel):
    lat: float
    lon: float
    timestamp: datetime


class ShipResponse(BaseModel):
    mmsi: str
    name: str
    ship_type: ShipType
    lat: float
    lon: float
    speed_knots: float
    course_deg: float
    destination: Optional[str] = None
    flag: Optional[str] = None
    length_m: Optional[float] = None
    history: list[ShipPosition] = []
    last_updated: datetime


class ShipListResponse(BaseModel):
    count: int
    ships: list[ShipResponse]
    timestamp: datetime


# ─────────────────────────── Polar Routes ────────────────────────────────────

class RouteSegmentRisk(BaseModel):
    """Risk assessment for a single 50km segment of a polar route corridor."""
    seg_id: str
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    center_lat: float
    center_lon: float
    length_km: float
    risk_level: RiskLevel = RiskLevel.SAFE
    risk_score: float = Field(0.0, ge=0.0, le=1.0, description="Composite risk 0–1")
    ice_concentration: float = Field(0.0, ge=0.0, le=1.0)
    iceberg_proximity_km: Optional[float] = None
    depth_m: Optional[float] = None
    notes: str = ""


class PolarRouteResponse(BaseModel):
    """A named Antarctic supply corridor with per-segment danger coding."""
    route_id: str
    name: str
    route_type: str
    distance_km: float
    typical_vessel: str
    overall_risk: RiskLevel = RiskLevel.SAFE
    overall_risk_score: float = 0.0
    segments: list[RouteSegmentRisk]
    waypoints: list[dict[str, float]]   # [{"lat": ..., "lon": ...}]
    timestamp: datetime


class PolarRoutesResponse(BaseModel):
    count: int
    routes: list[PolarRouteResponse]
    timestamp: datetime
    ice_forecast_age_hours: Optional[float] = None


# ─────────────────────────── Navigation ───────────────────────────────────────

class RouteRequest(BaseModel):
    start_lat: float = Field(..., ge=-90, le=90)
    start_lon: float = Field(..., ge=-180, le=180)
    end_lat: float = Field(..., ge=-90, le=90)
    end_lon: float = Field(..., ge=-180, le=180)
    ship_type: IceClass = IceClass.ICE_CLASS_1A
    departure_time: Optional[datetime] = None
    avoid_icebergs: bool = True
    max_ice_concentration: float = Field(0.8, ge=0.0, le=1.0)
    min_depth_m: float = Field(20.0, ge=0.0)


class RouteWaypoint(BaseModel):
    lat: float
    lon: float
    ice_concentration: float = 0.0
    depth_m: Optional[float] = None
    risk_score: float = 0.0


class RiskBreakdown(BaseModel):
    ice_risk: float
    iceberg_risk: float
    bathymetry_risk: float
    weather_risk: float
    total_risk: float


class RouteResponse(BaseModel):
    route_id: str
    waypoints: list[RouteWaypoint]
    distance_km: float
    eta_hours: float
    fuel_estimate_tons: Optional[float] = None
    risk_score: float
    risk_breakdown: RiskBreakdown
    explanation: str
    alternatives: list[list[RouteWaypoint]] = []
    timestamp: datetime


class ReplanRequest(BaseModel):
    route_id: str
    current_lat: float
    current_lon: float
    end_lat: float
    end_lon: float
    ship_type: IceClass = IceClass.ICE_CLASS_1A


# ─────────────────────────── Health & Ingestion Status ────────────────────────

class IngestionStatus(BaseModel):
    last_run: Optional[datetime] = None
    icebergs_loaded: int = 0
    sic_cells_loaded: int = 0
    wind_cells_loaded: int = 0
    routes_loaded: int = 0
    gebco_available: bool = False
    data_age_hours: Optional[float] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    services: dict[str, str]
    models: dict[str, str]
    ingestion: Optional[IngestionStatus] = None
