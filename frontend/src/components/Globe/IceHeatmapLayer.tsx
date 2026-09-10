import { useEffect, useRef } from 'react';
import * as Cesium from 'cesium';
import type { IceCell } from '@/types';

interface IceHeatmapLayerProps {
  viewer: Cesium.Viewer;
  cells: IceCell[];
  opacity: number;
}


// Convert concentration (0-1) to an rgba CSS string
function getSicColorString(concentration: number, opacity: number): string {
  const t = Math.max(0, Math.min(1, concentration));
  if (t < 0.05) return `rgba(0,0,0,0)`;

  let r, g, b, a;
  if (t < 0.3) {
    const s = (t - 0.05) / 0.25;
    r = Math.floor((0.05 + 0.05 * s) * 255);
    g = Math.floor((0.25 + 0.35 * s) * 255);
    b = Math.floor((0.60 + 0.30 * s) * 255);
    a = 0.15 + 0.25 * s;
  } else if (t < 0.6) {
    const s = (t - 0.3) / 0.3;
    r = Math.floor((0.10 + 0.30 * s) * 255);
    g = Math.floor((0.60 + 0.30 * s) * 255);
    b = Math.floor((0.90 + 0.08 * s) * 255);
    a = 0.40 + 0.20 * s;
  } else if (t < 0.85) {
    const s = (t - 0.6) / 0.25;
    r = Math.floor((0.40 + 0.50 * s) * 255);
    g = Math.floor((0.90 + 0.08 * s) * 255);
    b = Math.floor(0.98 * 255);
    a = 0.60 + 0.20 * s;
  } else {
    const s = (t - 0.85) / 0.15;
    r = Math.floor((0.90 + 0.10 * s) * 255);
    g = Math.floor((0.98 + 0.02 * s) * 255);
    b = 255;
    a = 0.80 + 0.18 * s;
  }
  return `rgba(${r},${g},${b},${a * opacity})`;
}

export function IceHeatmapLayer({ viewer, cells, opacity }: IceHeatmapLayerProps) {
  const layerRef = useRef<Cesium.ImageryLayer | null>(null);

  useEffect(() => {
    if (!viewer || viewer.isDestroyed() || cells.length === 0) return;

    if (layerRef.current) {
      viewer.imageryLayers.remove(layerRef.current);
      layerRef.current = null;
    }

    // Grid bounds
    const lonMin = -180;
    const lonMax = 180;
    const latMin = -90;
    const latMax = -55;
    const res = 0.5;

    const width = Math.round((lonMax - lonMin) / res);
    const height = Math.round((latMax - latMin) / res);

    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Draw cells
    for (const cell of cells) {
      if (cell.concentration < 0.05) continue;
      
      // X maps from lonMin to lonMax
      const x = Math.round((cell.lon - lonMin) / res);
      // Y maps from latMax (top, 0) to latMin (bottom, height)
      const y = Math.round((latMax - cell.lat) / res);

      ctx.fillStyle = getSicColorString(cell.concentration, opacity);
      ctx.fillRect(x, y, Math.ceil(1.2), Math.ceil(1.2)); // Slight overlap to prevent grid lines
    }

    Cesium.SingleTileImageryProvider.fromUrl(canvas.toDataURL(), {
      rectangle: Cesium.Rectangle.fromDegrees(lonMin, latMin, lonMax, latMax),
    }).then(provider => {
      if (viewer.isDestroyed() || !layerRef) return;
      const layer = new Cesium.ImageryLayer(provider, {
        alpha: 1.0, // Opacity is baked into the canvas pixels
      });
      viewer.imageryLayers.add(layer);
      layerRef.current = layer;
    });

    return () => {
      if (layerRef.current && !viewer.isDestroyed()) {
        viewer.imageryLayers.remove(layerRef.current);
        layerRef.current = null;
      }
    };
  }, [viewer, cells, opacity]);

  return null;
}
