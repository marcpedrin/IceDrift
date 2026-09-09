import { useEffect, useRef } from 'react';
import * as Cesium from 'cesium';
import type { IceCell } from '@/types';

interface IceHeatmapLayerProps {
  viewer: Cesium.Viewer;
  cells: IceCell[];
  opacity: number;
}

// Color ramp: blue (0% SIC) → cyan → white (100% SIC)
function sicToColor(concentration: number, opacity: number): Cesium.Color {
  const t = Math.max(0, Math.min(1, concentration));
  if (t < 0.1) return new Cesium.Color(0.05, 0.15, 0.4, 0);
  if (t < 0.3) {
    const s = (t - 0.1) / 0.2;
    return new Cesium.Color(0.1 * (1 - s) + 0.1 * s, 0.3 * (1 - s) + 0.55 * s, 0.7 * (1 - s) + 0.85 * s, 0.25 * s * opacity);
  }
  if (t < 0.6) {
    const s = (t - 0.3) / 0.3;
    return new Cesium.Color(0.4 * s, 0.7 * (1 - s) + 0.85 * s, 0.9 * (1 - s) + 0.95 * s, (0.4 + 0.2 * s) * opacity);
  }
  if (t < 0.85) {
    const s = (t - 0.6) / 0.25;
    return new Cesium.Color(0.6 + 0.4 * s, 0.9 * (1 - s) + s, 0.95, (0.6 + 0.2 * s) * opacity);
  }
  // High concentration: near-white
  const s = (t - 0.85) / 0.15;
  return new Cesium.Color(0.9 + 0.1 * s, 0.95 + 0.05 * s, 1.0, (0.8 + 0.15 * s) * opacity);
}

export function IceHeatmapLayer({ viewer, cells, opacity }: IceHeatmapLayerProps) {
  const dsRef = useRef<Cesium.CustomDataSource | null>(null);

  useEffect(() => {
    if (!viewer || cells.length === 0) return;

    // Remove previous
    if (dsRef.current) {
      viewer.dataSources.remove(dsRef.current);
    }

    const ds = new Cesium.CustomDataSource('ice-heatmap');
    const STEP = 0.5; // degrees per cell

    // Batch all cells
    for (const cell of cells) {
      if (cell.concentration < 0.05) continue; // skip near-zero cells for performance

      const color = sicToColor(cell.concentration, opacity);
      ds.entities.add({
        rectangle: {
          coordinates: Cesium.Rectangle.fromDegrees(
            cell.lon - STEP / 2,
            cell.lat - STEP / 2,
            cell.lon + STEP / 2,
            cell.lat + STEP / 2
          ),
          material: color,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
          classificationType: Cesium.ClassificationType.BOTH,
        },
      });
    }

    viewer.dataSources.add(ds);
    dsRef.current = ds;

    return () => {
      if (dsRef.current) {
        viewer.dataSources.remove(dsRef.current, true);
        dsRef.current = null;
      }
    };
  }, [viewer, cells, opacity]);

  return null;
}
