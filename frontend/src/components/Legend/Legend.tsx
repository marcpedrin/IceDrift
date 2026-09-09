import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export const Legend: React.FC = () => {
  const [visible, setVisible] = useState(true);

  return (
    <div className="absolute bottom-4 right-4 z-10">
      <button
        onClick={() => setVisible(!visible)}
        className="btn-ghost text-xs mb-1 ml-auto flex"
        id="legend-toggle-btn"
      >
        {visible ? '▼ Legend' : '▲ Legend'}
      </button>

      <AnimatePresence>
        {visible && (
          <motion.div
            className="glass rounded-xl px-4 py-3 w-52"
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.95 }}
            transition={{ duration: 0.2 }}
          >
            <div className="text-xs font-semibold mb-3 tracking-wider" style={{ color: 'var(--cyan)' }}>
              LEGEND
            </div>

            {/* Sea Ice */}
            <div className="mb-3">
              <div className="text-xs mb-1.5 font-medium" style={{ color: 'var(--text-secondary)' }}>
                Sea Ice Concentration
              </div>
              <div className="flex items-center gap-1.5">
                <div className="flex-1 h-3 rounded" style={{
                  background: 'linear-gradient(to right, rgba(20,40,100,0.3), #40a5f5, #82c4ff, #dbeeff, white)'
                }} />
              </div>
              <div className="flex justify-between text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                <span>0%</span><span>50%</span><span>100%</span>
              </div>
            </div>

            {/* Icebergs */}
            <div className="mb-3">
              <div className="text-xs mb-1.5 font-medium" style={{ color: 'var(--text-secondary)' }}>
                Icebergs
              </div>
              <div className="space-y-1">
                {[
                  { label: 'Small (<100 km²)', r: 5, color: '#00e5ff' },
                  { label: 'Medium (100–500 km²)', r: 8, color: '#00e5ff' },
                  { label: 'Large (>500 km²)', r: 12, color: '#00e5ff' },
                ].map(({ label, r, color }) => (
                  <div key={label} className="flex items-center gap-2">
                    <div className="flex items-center justify-center" style={{ width: 20 }}>
                      <div className="rounded-full" style={{ width: r, height: r, background: color, opacity: 0.9 }} />
                    </div>
                    <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{label}</span>
                  </div>
                ))}
                <div className="flex items-center gap-2">
                  <div className="w-5 flex items-center">
                    <div className="w-4 h-0.5 rounded" style={{ background: 'linear-gradient(to right, #00e5ff, transparent)' }} />
                  </div>
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Trajectory (72h)</span>
                </div>
              </div>
            </div>

            {/* Ships */}
            <div className="mb-3">
              <div className="text-xs mb-1.5 font-medium" style={{ color: 'var(--text-secondary)' }}>Ships</div>
              <div className="space-y-1">
                {[
                  { label: 'Research', color: '#7fff00' },
                  { label: 'Icebreaker', color: '#00e5ff' },
                  { label: 'Cargo', color: '#ff9800' },
                  { label: 'Passenger', color: '#ff69b4' },
                  { label: 'Supply', color: '#dda0dd' },
                ].map(({ label, color }) => (
                  <div key={label} className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: color }} />
                    <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{label}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Routes */}
            <div>
              <div className="text-xs mb-1.5 font-medium" style={{ color: 'var(--text-secondary)' }}>Routes</div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <div className="w-5 h-0.5 rounded" style={{ background: '#00e676' }} />
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Optimal route</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-5 h-px" style={{ background: 'rgba(180,180,180,0.5)', borderTop: '1px dashed rgba(180,180,180,0.5)' }} />
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Alternative route</span>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
