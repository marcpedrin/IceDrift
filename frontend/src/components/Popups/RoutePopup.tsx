import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import type { Route } from '@/types';

interface RoutePopupProps {
  route: Route | null;
  onClose: () => void;
}

export const RoutePopup: React.FC<RoutePopupProps> = ({ route, onClose }) => {
  if (!route) return null;

  const riskData = [
    { name: 'Ice', value: Math.round(route.risk_breakdown.ice_risk * 100), color: '#40a5f5' },
    { name: 'Iceberg', value: Math.round(route.risk_breakdown.iceberg_risk * 100), color: '#00e5ff' },
    { name: 'Bathymetry', value: Math.round(route.risk_breakdown.bathymetry_risk * 100), color: '#7fb3ff' },
    { name: 'Weather', value: Math.round(route.risk_breakdown.weather_risk * 100), color: '#ff9800' },
  ];

  const totalRisk = route.risk_score;
  const riskClass = totalRisk < 0.3 ? 'risk-low' : totalRisk < 0.6 ? 'risk-medium' : 'risk-high';

  return (
    <AnimatePresence>
      {route && (
        <motion.div
          className="popup-overlay"
          onClick={(e) => e.target === e.currentTarget && onClose()}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            className="popup-modal"
            initial={{ scale: 0.9, y: 20, opacity: 0 }}
            animate={{ scale: 1, y: 0, opacity: 1 }}
            exit={{ scale: 0.9, y: 20, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 400, damping: 30 }}
          >
            {/* Header */}
            <div className="px-5 py-4 flex items-start justify-between"
                 style={{ borderBottom: '1px solid rgba(0,229,255,0.15)' }}>
              <div>
                <h2 className="font-bold text-base glow-green" style={{ color: '#00e676' }}>
                  🗺 Optimized Route
                </h2>
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  ID: {route.route_id.slice(0, 8)}… · {new Date(route.timestamp).toLocaleString()}
                </p>
              </div>
              <button onClick={onClose} className="btn-ghost p-1 text-lg" id="route-popup-close">×</button>
            </div>

            <div className="px-5 py-4 space-y-4">
              {/* Key metrics */}
              <div className="grid grid-cols-3 gap-3">
                <MetricCard label="Distance" value={`${route.distance_km.toFixed(0)} km`} color="#00e676" />
                <MetricCard label="ETA" value={`${route.eta_hours.toFixed(1)} h`} color="#00e5ff" />
                <MetricCard label="Risk" value={`${(totalRisk * 100).toFixed(0)}%`} color={
                  totalRisk < 0.3 ? '#00e676' : totalRisk < 0.6 ? '#ffaa00' : '#ff4444'
                } badge={riskClass} />
              </div>

              {route.fuel_estimate_tons && (
                <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--text-secondary)' }}>
                  ⛽ Fuel estimate: <span className="font-mono" style={{ color: '#ffaa00' }}>
                    {route.fuel_estimate_tons.toFixed(1)} tonnes
                  </span>
                </div>
              )}

              {/* Risk breakdown chart */}
              <div>
                <div className="section-title text-xs">Risk Breakdown</div>
                <div style={{ height: 110 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={riskData} layout="vertical" margin={{ left: 0, right: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" horizontal={false} />
                      <XAxis type="number" domain={[0, 100]} tick={{ fill: '#4a6880', fontSize: 10 }} unit="%" />
                      <YAxis type="category" dataKey="name" tick={{ fill: '#8ab4cc', fontSize: 11 }} width={70} />
                      <Tooltip
                        contentStyle={{ background: '#070d1a', border: '1px solid rgba(0,229,255,0.2)', borderRadius: 8 }}
                        formatter={(v: number) => [`${v}%`, 'Risk']}
                        labelStyle={{ color: '#00e5ff' }}
                      />
                      <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                        {riskData.map((entry, idx) => (
                          <rect key={idx} fill={entry.color} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Natural language explanation */}
              <div>
                <div className="section-title text-xs">Route Explanation</div>
                <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                  {route.explanation}
                </p>
              </div>

              {/* Waypoints summary */}
              <div>
                <div className="section-title text-xs">Waypoints ({route.waypoints.length})</div>
                <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  {route.waypoints[0] && (
                    <>Start: {route.waypoints[0].lat.toFixed(2)}°, {route.waypoints[0].lon.toFixed(2)}°</>
                  )}
                  {' → '}
                  {route.waypoints[route.waypoints.length - 1] && (
                    <>End: {route.waypoints[route.waypoints.length - 1].lat.toFixed(2)}°,{' '}
                    {route.waypoints[route.waypoints.length - 1].lon.toFixed(2)}°</>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

const MetricCard: React.FC<{ label: string; value: string; color: string; badge?: string }> = ({
  label, value, color, badge,
}) => (
  <div className="rounded-lg p-3 text-center"
       style={{ background: `${color}11`, border: `1px solid ${color}33` }}>
    <div className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>{label}</div>
    <div className="font-bold text-sm font-mono" style={{ color }}>{value}</div>
  </div>
);
