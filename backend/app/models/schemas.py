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


# ─────────────────────────── Health ───────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    services: dict[str, str]
    models: dict[str, str]
