import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { Ship, ShipType } from '@/types';

interface ShipPopupProps {
  ship: Ship | null;
  onClose: () => void;
}

const SHIP_TYPE_ICONS: Record<ShipType, string> = {
  cargo: '📦',
  tanker: '🛢',
  passenger: '🚢',
  icebreaker: '🧊',
  research: '🔬',
  supply: '📫',
  unknown: '🚤',
};

const SHIP_TYPE_COLORS: Record<ShipType, string> = {
  cargo: '#ff9800',
  tanker: '#ffeb3b',
  passenger: '#ff69b4',
  icebreaker: '#00e5ff',
  research: '#7fff00',
  supply: '#dda0dd',
  unknown: '#808080',
};

function formatSpeed(knots: number) {
  return `${knots.toFixed(1)} kn (${(knots * 1.852).toFixed(1)} km/h)`;
}

function formatCourse(deg: number) {
  const dirs = ['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW'];
  return `${deg.toFixed(0)}° ${dirs[Math.round(deg / 22.5) % 16]}`;
}

export const ShipPopup: React.FC<ShipPopupProps> = ({ ship, onClose }) => {
  const color = ship ? (SHIP_TYPE_COLORS[ship.ship_type] ?? '#808080') : '#808080';
  const icon = ship ? (SHIP_TYPE_ICONS[ship.ship_type] ?? '🚤') : '🚤';

  return (
    <AnimatePresence>
      {ship && (
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
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center text-xl"
                     style={{ background: `${color}22`, border: `1px solid ${color}44` }}>
                  {icon}
                </div>
                <div>
                  <h2 className="font-bold text-base" style={{ color }}>{ship.name}</h2>
                  <p className="text-xs capitalize" style={{ color: 'var(--text-muted)' }}>
                    {ship.ship_type.replace('_', ' ')} {ship.flag ? `· 🏴 ${ship.flag}` : ''}
                    {ship.mmsi ? ` · MMSI ${ship.mmsi}` : ''}
                  </p>
                </div>
              </div>
              <button onClick={onClose} className="btn-ghost p-1 text-lg" id="ship-popup-close">×</button>
            </div>

            {/* Details */}
            <div className="px-5 py-4 grid grid-cols-2 gap-3">
              <Stat label="Position" value={`${ship.lat.toFixed(4)}°, ${ship.lon.toFixed(4)}°`} />
              <Stat label="Speed" value={formatSpeed(ship.speed_knots)} />
              <Stat label="Course" value={formatCourse(ship.course_deg)} />
              {ship.length_m && <Stat label="Length" value={`${ship.length_m} m`} />}
              {ship.destination && (
                <div className="col-span-2">
                  <div className="label">Destination</div>
                  <div className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                    {ship.destination}
                  </div>
                </div>
              )}
              <div className="col-span-2">
                <Stat label="Last AIS Update" value={new Date(ship.last_updated).toLocaleString()} />
              </div>
            </div>

            {/* History indicator */}
            {ship.history.length > 0 && (
              <div className="px-5 pb-4">
                <div className="section-title text-xs">24h Track</div>
                <div className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--text-muted)' }}>
                  <div className="flex-1 h-1 rounded" style={{
                    background: `linear-gradient(to right, transparent, ${color})`
                  }} />
                  <span>{ship.history.length} position records</span>
                </div>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

const Stat: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div>
    <div className="label">{label}</div>
    <div className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{value}</div>
  </div>
);
