import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import type { Iceberg } from '@/types';

interface IcebergPopupProps {
  iceberg: Iceberg | null;
  onClose: () => void;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}

function getRiskClass(sizeKm2: number) {
  if (sizeKm2 > 2000) return 'risk-high';
  if (sizeKm2 > 300) return 'risk-medium';
  return 'risk-low';
}

export const IcebergPopup: React.FC<IcebergPopupProps> = ({ iceberg, onClose }) => {
  // Prepare trajectory chart data
  const chartData = iceberg ? iceberg.trajectory.slice(0, 12).map((pt, i) => ({
    step: `+${i * 6}h`,
    lat: pt.lat.toFixed(2),
    lon: pt.lon.toFixed(2),
    uncertainty: pt.uncertainty_radius_km,
  })) : [];

  return (
    <AnimatePresence>
      {iceberg && (
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
                <div className="flex items-center gap-2">
                  <span className="text-2xl">🗻</span>
                  <div>
                    <h2 className="font-bold text-lg glow-cyan" style={{ color: 'var(--cyan)' }}>
                      Iceberg {iceberg.id}
                    </h2>
                    <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                      {iceberg.source} · First seen {formatDate(iceberg.first_seen)}
                    </p>
                  </div>
                </div>
              </div>
              <button onClick={onClose} className="btn-ghost p-1 text-lg leading-none" id="iceberg-popup-close">×</button>
            </div>

            {/* Satellite imagery */}
            {iceberg.satellite_image_url && (
              <div className="relative" style={{ height: 180, background: '#040810' }}>
                <img
                  src={iceberg.satellite_image_url}
                  alt={`Satellite view of iceberg ${iceberg.id}`}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = 'none';
                  }}
                />
                <div className="absolute bottom-1 right-2 text-xs px-1 rounded"
                     style={{ background: 'rgba(0,0,0,0.7)', color: 'var(--text-muted)' }}>
                  Sentinel-2 / NASA GIBS
                </div>
              </div>
            )}

            {/* Stats grid */}
            <div className="px-5 py-4 grid grid-cols-2 gap-3">
              <Stat label="Position" value={`${iceberg.lat.toFixed(3)}°, ${iceberg.lon.toFixed(3)}°`} />
              <Stat label="Size" value={`${iceberg.size_km2.toFixed(0)} km²`} badge={getRiskClass(iceberg.size_km2)} />
              <Stat label="Dimensions" value={`${iceberg.length_km.toFixed(1)} × ${iceberg.width_km.toFixed(1)} km`} />
              <Stat label="Speed" value={`${(iceberg.velocity_ms * 1.944).toFixed(2)} kn`} />
              <Stat label="Heading" value={`${iceberg.heading_deg.toFixed(0)}°`} />
              <Stat label="Updated" value={new Date(iceberg.last_updated).toLocaleTimeString()} />
            </div>

            {/* Trajectory chart */}
            {chartData.length > 1 && (
              <div className="px-5 pb-4">
                <div className="section-title text-xs">Predicted Trajectory (72h)</div>
                <div style={{ height: 120 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                      <XAxis dataKey="step" tick={{ fill: '#4a6880', fontSize: 10 }} />
                      <YAxis tick={{ fill: '#4a6880', fontSize: 10 }} />
                      <Tooltip
                        contentStyle={{ background: '#070d1a', border: '1px solid rgba(0,229,255,0.2)', borderRadius: 8 }}
                        labelStyle={{ color: '#00e5ff' }}
                        itemStyle={{ color: '#8ab4cc' }}
                      />
                      <Line
                        type="monotone" dataKey="uncertainty"
                        stroke="#00e5ff" strokeWidth={2} dot={false}
                        name="Uncertainty (km)"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

const Stat: React.FC<{ label: string; value: string; badge?: string }> = ({ label, value, badge }) => (
  <div>
    <div className="label">{label}</div>
    <div className="flex items-center gap-1.5">
      <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{value}</span>
      {badge && <span className={`risk-badge ${badge} text-xs`}>{badge === 'risk-high' ? 'LARGE' : badge === 'risk-medium' ? 'MED' : 'SMALL'}</span>}
    </div>
  </div>
);
