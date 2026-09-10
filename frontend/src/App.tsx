import React, { useState, useCallback, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import * as Cesium from 'cesium';
import { motion } from 'framer-motion';

import { CesiumGlobe } from '@/components/Globe/CesiumGlobe';
import { Sidebar } from '@/components/Sidebar/Sidebar';
import { IcebergPopup } from '@/components/Popups/IcebergPopup';
import { ShipPopup } from '@/components/Popups/ShipPopup';
import { RoutePopup } from '@/components/Popups/RoutePopup';
import { Legend } from '@/components/Legend/Legend';

import { fetchIceForecast, fetchIcebergs, fetchWindField, fetchOceanCurrents, planRoute } from '@/services/api';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useCesiumViewer } from '@/hooks/useCesiumViewer';

import type {
  AppState, LayerState, IceClass,
  Iceberg, Ship, Route,
} from '@/types';

const DEFAULT_LAYERS: LayerState = {
  iceHeatmap: true,
  icebergs: true,
  trajectories: true,
  ships: true,
  routes: true,
  uncertainty: false,
  wind: false, // Turn wind off by default so they don't clash
  currents: true, // Turn currents on by default
};

function App() {
  const [state, setState] = useState<AppState>({
    layers: DEFAULT_LAYERS,
    selectedIceberg: null,
    selectedShip: null,
    selectedRoute: null,
    currentRoute: null,
    iceOpacity: 0.7,
    forecastLeadDay: 0,
    shipProfile: 'ice_class_1a',
    startPoint: null,
    endPoint: null,
    isRoutePlanning: false,
    isLoadingRoute: false,
  });

  // Single shared viewer ref passed to CesiumGlobe which populates it
  const viewerRef = useRef<Cesium.Viewer | null>(null);
  const { zoomToIceberg, zoomToRoute } = useCesiumViewer();

  // ── Data fetching ─────────────────────────────────────────────────────────

  const { data: iceData } = useQuery({
    queryKey: ['ice-forecast', state.forecastLeadDay],
    queryFn: () => fetchIceForecast(state.forecastLeadDay),
    refetchInterval: 6 * 60 * 60 * 1000, // 6 hours
    retry: 2,
  });

  const { data: icebergData } = useQuery({
    queryKey: ['icebergs'],
    queryFn: () => fetchIcebergs(72),
    refetchInterval: 12 * 60 * 60 * 1000, // 12 hours
    retry: 2,
  });

  const { data: windData } = useQuery({
    queryKey: ['windField'],
    queryFn: () => fetchWindField(),
    refetchInterval: 12 * 60 * 60 * 1000,
    retry: 2,
  });

  const { data: currentsData } = useQuery({
    queryKey: ['oceanCurrents'],
    queryFn: () => fetchOceanCurrents(),
    refetchInterval: 12 * 60 * 60 * 1000,
    retry: 2,
  });

  // Live ship data via WebSocket
  const { ships, lastUpdate, isConnected } = useWebSocket();

  // ── State mutators ────────────────────────────────────────────────────────

  const toggleLayer = useCallback((key: keyof LayerState) => {
    setState((s) => ({
      ...s,
      layers: { ...s.layers, [key]: !s.layers[key] },
    }));
  }, []);

  const handleIcebergClick = useCallback((iceberg: Iceberg) => {
    setState((s) => ({ ...s, selectedIceberg: iceberg }));
    zoomToIceberg(iceberg.lat, iceberg.lon);
  }, [zoomToIceberg]);

  const handleShipClick = useCallback((ship: Ship) => {
    setState((s) => ({ ...s, selectedShip: ship }));
  }, []);

  const handleRouteClick = useCallback((route: Route) => {
    setState((s) => ({ ...s, selectedRoute: route }));
  }, []);

  const handleFindRoute = useCallback(async (startLat?: number, startLon?: number, endLat?: number, endLon?: number) => {
    const sPt = (startLat !== undefined && startLon !== undefined) ? {lat: startLat, lon: startLon} : state.startPoint;
    const ePt = (endLat !== undefined && endLon !== undefined) ? {lat: endLat, lon: endLon} : state.endPoint;
    const { shipProfile } = state;
    
    if (!sPt || !ePt) return;

    setState((s) => ({ ...s, isLoadingRoute: true, startPoint: sPt, endPoint: ePt }));
    try {
      const route = await planRoute({
        start_lat: sPt.lat,
        start_lon: sPt.lon,
        end_lat: ePt.lat,
        end_lon: ePt.lon,
        ship_type: shipProfile,
        avoid_icebergs: true,
      });
      setState((s) => ({
        ...s,
        currentRoute: route,
        isLoadingRoute: false,
        layers: { ...s.layers, routes: true },
      }));
      zoomToRoute(route.waypoints);
    } catch (err) {
      console.error('Route planning failed:', err);
      setState((s) => ({ ...s, isLoadingRoute: false }));
    }
  }, [state.startPoint, state.endPoint, state.shipProfile, zoomToRoute]);

  const handleReplan = useCallback(() => {
    setState((s) => ({ ...s, currentRoute: null }));
    handleFindRoute();
  }, [handleFindRoute]);

  const handleStartChange = useCallback((lat: string, lon: string) => {
    const latNum = parseFloat(lat);
    const lonNum = parseFloat(lon);
    if (!isNaN(latNum) && !isNaN(lonNum)) {
      setState((s) => ({ ...s, startPoint: { lat: latNum, lon: lonNum } }));
    }
  }, []);

  const handleEndChange = useCallback((lat: string, lon: string) => {
    const latNum = parseFloat(lat);
    const lonNum = parseFloat(lon);
    if (!isNaN(latNum) && !isNaN(lonNum)) {
      setState((s) => ({ ...s, endPoint: { lat: latNum, lon: lonNum } }));
    }
  }, []);

  const handleGlobeClick = useCallback((lat: number, lon: number) => {
    // First click = start, second = end
    setState((s) => {
      if (!s.startPoint) {
        return { ...s, startPoint: { lat, lon } };
      } else if (!s.endPoint) {
        return { ...s, endPoint: { lat, lon } };
      }
      return s;
    });
  }, []);

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="relative w-full h-full overflow-hidden" style={{ background: '#040810' }}>
      {/* Cesium Globe – full screen */}
      <CesiumGlobe
        iceCells={iceData?.cells ?? []}
        iceOpacity={state.iceOpacity}
        icebergs={icebergData?.icebergs ?? []}
        ships={ships}
        windData={windData}
        currentsData={currentsData}
        route={state.currentRoute}
        layers={state.layers}
        onIcebergClick={handleIcebergClick}
        onShipClick={handleShipClick}
        onRouteClick={handleRouteClick}
        onGlobeClick={handleGlobeClick}
        viewerRef={viewerRef}
      />

      {/* Sidebar */}
      <Sidebar
        state={state}
        onLayerToggle={toggleLayer}
        onIceOpacityChange={(v) => setState((s) => ({ ...s, iceOpacity: v }))}
        onLeadDayChange={(v) => setState((s) => ({ ...s, forecastLeadDay: v }))}
        onShipProfileChange={(v: IceClass) => setState((s) => ({ ...s, shipProfile: v }))}
        onStartChange={handleStartChange}
        onEndChange={handleEndChange}
        onFindRoute={handleFindRoute}
        onReplan={handleReplan}
        isConnected={isConnected}
        lastShipUpdate={lastUpdate}
      />

      {/* Legend */}
      <Legend />

      {/* Top-right status bar */}
      <motion.div
        className="absolute top-3 right-3 glass rounded-lg px-3 py-2 flex items-center gap-3 z-10 text-xs"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
      >
        <span style={{ color: 'var(--text-muted)' }}>
          {iceData ? `${iceData.cells.length.toLocaleString()} ice cells` : 'Loading ice…'}
        </span>
        <span className="opacity-30">|</span>
        <span style={{ color: 'var(--text-muted)' }}>
          {icebergData ? `${icebergData.count} icebergs` : 'Loading…'}
        </span>
        <span className="opacity-30">|</span>
        <span style={{ color: 'var(--text-muted)' }}>
          {ships.length} ships
        </span>
        <span className="opacity-30">|</span>
        <span className="font-mono" style={{ color: 'var(--cyan)' }}>SIH 2026</span>
      </motion.div>

      {/* Click-to-place hint */}
      {!state.startPoint && (
        <motion.div
          className="absolute bottom-20 left-1/2 -translate-x-1/2 glass rounded-full px-4 py-2 text-xs pointer-events-none"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 2, duration: 1 }}
          style={{ color: 'var(--text-secondary)' }}
        >
          💡 Click globe to set start point, then end point for route planning
        </motion.div>
      )}

      {/* Popups */}
      <IcebergPopup
        iceberg={state.selectedIceberg}
        onClose={() => setState((s) => ({ ...s, selectedIceberg: null }))}
      />
      <ShipPopup
        ship={state.selectedShip}
        onClose={() => setState((s) => ({ ...s, selectedShip: null }))}
      />
      <RoutePopup
        route={state.selectedRoute}
        onClose={() => setState((s) => ({ ...s, selectedRoute: null }))}
      />
    </div>
  );
}

export default App;
