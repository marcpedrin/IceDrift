import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { LayerState, IceClass, AppState } from '@/types';

interface SidebarProps {
  state: AppState;
  onLayerToggle: (layer: keyof LayerState) => void;
  onIceOpacityChange: (v: number) => void;
  onLeadDayChange: (v: number) => void;
  onShipProfileChange: (v: IceClass) => void;
  onStartChange: (lat: string, lon: string) => void;
  onEndChange: (lat: string, lon: string) => void;
  onFindRoute: () => void;
  onReplan: () => void;
  isConnected: boolean;
  lastShipUpdate: string | null;
}

const LAYER_ITEMS: { key: keyof LayerState; label: string; color: string; icon: string }[] = [
  { key: 'iceHeatmap', label: 'Sea Ice Heatmap', color: '#40a5f5', icon: '❄️' },
  { key: 'icebergs', label: 'Iceberg Points', color: '#00e5ff', icon: '🗻' },
  { key: 'trajectories', label: 'Trajectories', color: '#00e5ff', icon: '↗' },
  { key: 'uncertainty', label: 'Uncertainty Cones', color: '#7fb3ff', icon: '◎' },
  { key: 'ships', label: 'Ship Tracking', color: '#00e676', icon: '⛴️' },
  { key: 'routes', label: 'Routes', color: '#00e676', icon: '🗺' },
];

const SHIP_PROFILES: { value: IceClass; label: string }[] = [
  { value: 'open_water', label: 'Open Water' },
  { value: 'ice_class_1c', label: 'Ice Class 1C' },
  { value: 'ice_class_1b', label: 'Ice Class 1B' },
  { value: 'ice_class_1a', label: 'Ice Class 1A' },
  { value: 'ice_class_1as', label: 'Ice Class 1AS' },
  { value: 'icebreaker', label: 'Icebreaker' },
];

export const Sidebar: React.FC<SidebarProps> = ({
  state,
  onLayerToggle,
  onIceOpacityChange,
  onLeadDayChange,
  onShipProfileChange,
  onStartChange,
  onEndChange,
  onFindRoute,
  onReplan,
  isConnected,
  lastShipUpdate,
}) => {
  const [startLat, setStartLat] = useState('-65.0');
  const [startLon, setStartLon] = useState('0.0');
  const [endLat, setEndLat] = useState('-60.0');
  const [endLon, setEndLon] = useState('30.0');
  const [collapsed, setCollapsed] = useState(false);

  const handleFindRoute = () => {
    onStartChange(startLat, startLon);
    onEndChange(endLat, endLon);
    onFindRoute();
  };

  return (
    <motion.div
      className="absolute left-0 top-0 h-full z-10 flex"
      initial={{ x: -320 }}
      animate={{ x: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
    >
      {/* Sidebar Panel */}
      <AnimatePresence>
        {!collapsed && (
          <motion.div
            className="glass-strong w-72 h-full flex flex-col overflow-hidden"
            style={{ borderRight: '1px solid rgba(0,229,255,0.15)' }}
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 288, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
          >
            {/* Header */}
            <div className="px-4 py-3 border-b border-cyan-900/30">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded flex items-center justify-center text-sm"
                     style={{ background: 'linear-gradient(135deg,#1a8adc,#00e5ff)' }}>
                  🧊
                </div>
                <div>
                  <h1 className="font-bold text-sm glow-cyan" style={{ color: 'var(--cyan)' }}>
                    IceNavigator
                  </h1>
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    Antarctic Navigation DSS
                  </p>
                </div>
              </div>

              {/* Live status */}
              <div className="flex items-center gap-1.5 mt-2">
                <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400 pulse-cyan' : 'bg-red-500'}`} />
                <span className="text-xs" style={{ color: isConnected ? '#00e676' : '#ff4444' }}>
                  {isConnected ? 'LIVE' : 'OFFLINE'}
                </span>
                {lastShipUpdate && (
                  <span className="text-xs ml-1" style={{ color: 'var(--text-muted)' }}>
                    · {new Date(lastShipUpdate).toLocaleTimeString()}
                  </span>
                )}
              </div>
            </div>

            {/* Scrollable content */}
            <div className="flex-1 overflow-y-auto px-4 py-3 space-y-5">

              {/* ── Layers ────────────────────────────────────────────── */}
              <section>
                <div className="section-title">Layers</div>
                <div className="space-y-1.5">
                  {LAYER_ITEMS.map(({ key, label, color, icon }) => (
                    <label
                      key={key}
                      className="flex items-center gap-2.5 px-2 py-1.5 rounded cursor-pointer transition-all hover:bg-white/5"
                    >
                      <input
                        type="checkbox"
                        checked={state.layers[key]}
                        onChange={() => onLayerToggle(key)}
                        className="w-3.5 h-3.5 rounded accent-cyan-400"
                        style={{ accentColor: color }}
                        id={`layer-${key}`}
                      />
                      <span className="text-sm" style={{ color }}>{icon}</span>
                      <span className="text-sm" style={{ color: 'var(--text-primary)' }}>{label}</span>
                    </label>
                  ))}
                </div>

                {/* Ice opacity */}
                {state.layers.iceHeatmap && (
                  <div className="mt-3 px-2">
                    <label className="label">Ice Opacity</label>
                    <div className="flex items-center gap-2">
                      <input
                        type="range" min={0} max={1} step={0.05}
                        value={state.iceOpacity}
                        onChange={(e) => onIceOpacityChange(Number(e.target.value))}
                        className="flex-1 h-1.5 rounded accent-blue-400"
                        id="ice-opacity-slider"
                        style={{ accentColor: '#40a5f5' }}
                      />
                      <span className="text-xs w-8 text-right" style={{ color: 'var(--text-muted)' }}>
                        {Math.round(state.iceOpacity * 100)}%
                      </span>
                    </div>
                  </div>
                )}
              </section>

              {/* ── Forecast ──────────────────────────────────────────── */}
              <section>
                <div className="section-title">Ice Forecast</div>
                <label className="label">Lead Day</label>
                <div className="flex items-center gap-2">
                  <input
                    type="range" min={0} max={7} step={1}
                    value={state.forecastLeadDay}
                    onChange={(e) => onLeadDayChange(Number(e.target.value))}
                    className="flex-1 h-1.5 rounded"
                    id="forecast-lead-slider"
                    style={{ accentColor: '#40a5f5' }}
                  />
                  <span className="text-xs w-14 text-right font-mono"
                        style={{ color: 'var(--ice-300)' }}>
                    +{state.forecastLeadDay}d
                  </span>
                </div>
                <div className="flex justify-between mt-1">
                  {[0,1,2,3,4,5,6,7].map(d => (
                    <button key={d}
                      onClick={() => onLeadDayChange(d)}
                      className={`text-xs px-1 py-0.5 rounded transition-colors ${
                        state.forecastLeadDay === d
                          ? 'bg-blue-500/30 text-blue-300'
                          : 'text-gray-500 hover:text-gray-300'
                      }`}
                    >
                      {d}
                    </button>
                  ))}
                </div>
              </section>

              {/* ── Ship Profile ──────────────────────────────────────── */}
              <section>
                <div className="section-title">Ship Profile</div>
                <select
                  value={state.shipProfile}
                  onChange={(e) => onShipProfileChange(e.target.value as IceClass)}
                  className="input-field text-sm"
                  id="ship-profile-select"
                >
                  {SHIP_PROFILES.map(({ value, label }) => (
                    <option key={value} value={value} style={{ background: '#0a1222' }}>
                      {label}
                    </option>
                  ))}
                </select>
              </section>

              {/* ── Route Planning ────────────────────────────────────── */}
              <section>
                <div className="section-title">Route Planning</div>

                <div className="space-y-2">
                  <div>
                    <label className="label">Start Point</label>
                    <div className="flex gap-1.5">
                      <input
                        className="input-field flex-1 text-xs"
                        placeholder="Lat" value={startLat}
                        onChange={(e) => setStartLat(e.target.value)}
                        id="start-lat-input"
                      />
                      <input
                        className="input-field flex-1 text-xs"
                        placeholder="Lon" value={startLon}
                        onChange={(e) => setStartLon(e.target.value)}
                        id="start-lon-input"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="label">End Point</label>
                    <div className="flex gap-1.5">
                      <input
                        className="input-field flex-1 text-xs"
                        placeholder="Lat" value={endLat}
                        onChange={(e) => setEndLat(e.target.value)}
                        id="end-lat-input"
                      />
                      <input
                        className="input-field flex-1 text-xs"
                        placeholder="Lon" value={endLon}
                        onChange={(e) => setEndLon(e.target.value)}
                        id="end-lon-input"
                      />
                    </div>
                  </div>

                  <button
                    onClick={handleFindRoute}
                    disabled={state.isLoadingRoute}
                    className="btn-primary w-full text-sm mt-1"
                    id="find-route-btn"
                  >
                    {state.isLoadingRoute ? (
                      <><div className="spinner" /> Computing Route…</>
                    ) : (
                      <><span>🗺</span> Find Route</>
                    )}
                  </button>

                  {state.currentRoute && (
                    <button
                      onClick={onReplan}
                      className="btn-ghost w-full text-xs"
                      id="replan-btn"
                    >
                      ↺ Replan with new data
                    </button>
                  )}
                </div>
              </section>

              {/* ── Route Summary ─────────────────────────────────────── */}
              {state.currentRoute && (
                <motion.section
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  <div className="section-title">Route Summary</div>
                  <div className="rounded-lg p-3 space-y-2"
                       style={{ background: 'rgba(0,230,118,0.05)', border: '1px solid rgba(0,230,118,0.2)' }}>
                    <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
                      <div style={{ color: 'var(--text-muted)' }}>Distance</div>
                      <div className="font-mono" style={{ color: '#00e676' }}>
                        {state.currentRoute.distance_km.toFixed(0)} km
                      </div>
                      <div style={{ color: 'var(--text-muted)' }}>ETA</div>
                      <div className="font-mono" style={{ color: '#00e676' }}>
                        {state.currentRoute.eta_hours.toFixed(1)} h
                      </div>
                      {state.currentRoute.fuel_estimate_tons && (
                        <>
                          <div style={{ color: 'var(--text-muted)' }}>Fuel</div>
                          <div className="font-mono" style={{ color: '#00e676' }}>
                            {state.currentRoute.fuel_estimate_tons.toFixed(1)} t
                          </div>
                        </>
                      )}
                      <div style={{ color: 'var(--text-muted)' }}>Risk</div>
                      <div>
                        <span className={`risk-badge ${
                          state.currentRoute.risk_score < 0.3 ? 'risk-low'
                          : state.currentRoute.risk_score < 0.6 ? 'risk-medium'
                          : 'risk-high'
                        }`}>
                          {(state.currentRoute.risk_score * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>

                    <div className="text-xs italic leading-relaxed pt-1"
                         style={{ color: 'var(--text-secondary)', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                      {state.currentRoute.explanation}
                    </div>
                  </div>
                </motion.section>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Toggle button */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="self-center ml-1 w-6 h-12 rounded-r glass flex items-center justify-center text-xs transition-all hover:bg-white/10"
        style={{ color: 'var(--cyan)' }}
        id="sidebar-toggle-btn"
      >
        {collapsed ? '›' : '‹'}
      </button>
    </motion.div>
  );
};
