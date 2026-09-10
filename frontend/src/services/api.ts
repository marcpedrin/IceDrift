import axios from 'axios';
import type {
  IceForecast,
  IcebergList,
  Iceberg,
  ShipList,
  Route,
  RouteRequest,
  HealthStatus,
} from '@/types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Interceptors ──────────────────────────────────────────────────────────────
client.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error('[API Error]', err.message, err.response?.data);
    return Promise.reject(err);
  }
);

// ── Ice Forecast ──────────────────────────────────────────────────────────────

export async function fetchIceForecast(leadDay = 0, date?: string): Promise<IceForecast> {
  const params: Record<string, string | number> = { lead_day: leadDay };
  if (date) params.date = date;
  const { data } = await client.get<IceForecast>('/ice/forecast', { params });
  return data;
}

// ── Icebergs ──────────────────────────────────────────────────────────────────

export async function fetchIcebergs(forecastHours = 72): Promise<IcebergList> {
  const { data } = await client.get<IcebergList>('/icebergs/all', {
    params: { include_trajectories: true, forecast_hours: forecastHours },
  });
  return data;
}

export async function fetchIceberg(id: string): Promise<Iceberg> {
  const { data } = await client.get<Iceberg>(`/icebergs/${id}`);
  return data;
}

// ── Ships ─────────────────────────────────────────────────────────────────────

export async function fetchNearbyShips(lat = -65.0, lon = 0.0, radiusNm = 2000): Promise<ShipList> {
  const { data } = await client.get<ShipList>('/ships/nearby', {
    params: { lat, lon, radius_nm: radiusNm },
  });
  return data;
}

// ── Weather / Wind ────────────────────────────────────────────────────────────

export async function fetchWindField(): Promise<any> {
  const { data } = await client.get<any>('/wind/field');
  return data;
}

export async function fetchOceanCurrents(): Promise<any> {
  const { data } = await client.get<any>('/ocean/currents');
  return data;
}

// ── Navigation ────────────────────────────────────────────────────────────────

export async function planRoute(req: RouteRequest): Promise<Route> {
  const { data } = await client.post<Route>('/navigation/route', req);
  return data;
}

export async function replanRoute(params: {
  route_id: string;
  current_lat: number;
  current_lon: number;
  end_lat: number;
  end_lon: number;
  ship_type: string;
}): Promise<Route> {
  const { data } = await client.post<Route>('/navigation/replan', params);
  return data;
}

// ── Health ────────────────────────────────────────────────────────────────────

export async function fetchHealth(): Promise<HealthStatus> {
  const { data } = await client.get<HealthStatus>('/health');
  return data;
}

// ── WebSocket URL ─────────────────────────────────────────────────────────────

export function getShipsWebSocketUrl(): string {
  const wsBase = (import.meta.env.VITE_WS_URL || API_BASE)
    .replace('http://', 'ws://')
    .replace('https://', 'wss://');
  return `${wsBase}/ws/ships`;
}
