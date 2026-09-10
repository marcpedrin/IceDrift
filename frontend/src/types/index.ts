// All TypeScript type definitions for IceNavigator frontend

export interface IceCell {
  lat: number;
  lon: number;
  concentration: number; // 0–1
  uncertainty: number;   // 0–1
}

export interface IceForecast {
  timestamp: string;
  lead_day: number;
  cells: IceCell[];
  model_version: string;
  source: string;
}

export type ShipType = 'cargo' | 'tanker' | 'passenger' | 'icebreaker' | 'research' | 'supply' | 'unknown';
export type IceClass = 'open_water' | 'ice_class_1c' | 'ice_class_1b' | 'ice_class_1a' | 'ice_class_1as' | 'icebreaker';

export interface TrajectoryPoint {
  lat: number;
  lon: number;
  timestamp: string;
  uncertainty_radius_km: number;
}

export interface UncertaintyConePoint {
  timestamp: string;
  center_lat: number;
  center_lon: number;
  radius_km: number;
  sigma_lat: number;
  sigma_lon: number;
}

export interface Iceberg {
  id: string;
  lat: number;
  lon: number;
  size_km2: number;
  length_km: number;
  width_km: number;
  velocity_ms: number;
  heading_deg: number;
  first_seen: string;
  last_updated: string;
  trajectory: TrajectoryPoint[];
  uncertainty_cone: UncertaintyConePoint[];
  satellite_image_url?: string;
  source: string;
}

export interface IcebergList {
  count: number;
  icebergs: Iceberg[];
  timestamp: string;
}

export interface ShipPosition {
  lat: number;
  lon: number;
  timestamp: string;
}

export interface Ship {
  mmsi: string;
  name: string;
  ship_type: ShipType;
  lat: number;
  lon: number;
  speed_knots: number;
  course_deg: number;
  destination?: string;
  flag?: string;
  length_m?: number;
  history: ShipPosition[];
  last_updated: string;
}

export interface ShipList {
  count: number;
  ships: Ship[];
  timestamp: string;
}

export interface RouteWaypoint {
  lat: number;
  lon: number;
  ice_concentration: number;
  depth_m?: number;
  risk_score: number;
}

export interface RiskBreakdown {
  ice_risk: number;
  iceberg_risk: number;
  bathymetry_risk: number;
  weather_risk: number;
  total_risk: number;
}

export interface Route {
  route_id: string;
  waypoints: RouteWaypoint[];
  distance_km: number;
  eta_hours: number;
  fuel_estimate_tons?: number;
  risk_score: number;
  risk_breakdown: RiskBreakdown;
  explanation: string;
  alternatives: RouteWaypoint[][];
  timestamp: string;
}

export interface RouteRequest {
  start_lat: number;
  start_lon: number;
  end_lat: number;
  end_lon: number;
  ship_type: IceClass;
  avoid_icebergs?: boolean;
  max_ice_concentration?: number;
}

// UI state types
export interface LayerState {
  iceHeatmap: boolean;
  icebergs: boolean;
  trajectories: boolean;
  ships: boolean;
  routes: boolean;
  uncertainty: boolean;
  wind: boolean;
  currents: boolean;
}

export interface AppState {
  layers: LayerState;
  selectedIceberg: Iceberg | null;
  selectedShip: Ship | null;
  selectedRoute: Route | null;
  currentRoute: Route | null;
  iceOpacity: number;
  forecastLeadDay: number;
  shipProfile: IceClass;
  startPoint: { lat: number; lon: number } | null;
  endPoint: { lat: number; lon: number } | null;
  isRoutePlanning: boolean;
  isLoadingRoute: boolean;
}

export interface HealthStatus {
  status: string;
  version: string;
  timestamp: string;
  services: Record<string, string>;
  models: Record<string, string>;
}
