import { useEffect, useRef } from 'react';
import * as Cesium from 'cesium';
import type { IceCell } from '@/types';

interface IceHeatmapLayerProps {
  viewer: Cesium.Viewer;
  cells: IceCell[];
  opacity: number;
}

// Science-accurate SIC → color ramp
// 0–5% (trace/open ocean): transparent
// 5–30% (young ice): translucent pale-blue
// 30–60% (first-year ice): medium blue-cyan
// 60–85% (MYI): bright cyan-white
// 85–100% (consolidated pack): pure white
function sicToColor(concentration: number, opacity: number): Cesium.Color {
  const t = Math.max(0, Math.min(1, concentration));
  if (t < 0.05) return Cesium.Color.TRANSPARENT;

  let r: number, g: number, b: number, a: number;

  if (t < 0.3) {
    const s = (t - 0.05) / 0.25;
    r = 0.05 + 0.05 * s;
    g = 0.25 + 0.35 * s;
    b = 0.60 + 0.30 * s;
    a = 0.15 + 0.25 * s;
  } else if (t < 0.6) {
    const s = (t - 0.3) / 0.3;
    r = 0.10 + 0.30 * s;
    g = 0.60 + 0.30 * s;
    b = 0.90 + 0.08 * s;
    a = 0.40 + 0.20 * s;
  } else if (t < 0.85) {
    const s = (t - 0.6) / 0.25;
    r = 0.40 + 0.50 * s;
    g = 0.90 + 0.08 * s;
    b = 0.98;
    a = 0.60 + 0.20 * s;
  } else {
    const s = (t - 0.85) / 0.15;
    r = 0.90 + 0.10 * s;
    g = 0.98 + 0.02 * s;
    b = 1.0;
    a = 0.80 + 0.18 * s;
  }

  return new Cesium.Color(r, g, b, a * opacity);
}

export function IceHeatmapLayer({ viewer, cells, opacity }: IceHeatmapLayerProps) {
  const primitiveRef = useRef<Cesium.PrimitiveCollection | null>(null);

  useEffect(() => {
    if (!viewer || viewer.isDestroyed() || cells.length === 0) return;

    // Remove previous primitive collection
    if (primitiveRef.current && !viewer.scene.primitives.contains(primitiveRef.current)) {
      primitiveRef.current = null;
    }
    if (primitiveRef.current) {
      viewer.scene.primitives.remove(primitiveRef.current);
      primitiveRef.current = null;
    }

    const collection = new Cesium.PrimitiveCollection();
    const STEP = 0.51; // degrees, slightly > 0.5 to overlap and hide gaps

    // Batch cells into geometry instances for performance (single draw call per material shade)
    // Group by concentration bucket → 10 buckets
    const buckets = new Map<number, Cesium.GeometryInstance[]>();

    for (const cell of cells) {
      if (cell.concentration < 0.05) continue;

      const bucket = Math.floor(cell.concentration * 10); // 0–10
      if (!buckets.has(bucket)) buckets.set(bucket, []);

      buckets.get(bucket)!.push(
        new Cesium.GeometryInstance({
          geometry: new Cesium.RectangleGeometry({
            rectangle: Cesium.Rectangle.fromDegrees(
              cell.lon - STEP / 2,
              cell.lat - STEP / 2,
              cell.lon + STEP / 2,
              cell.lat + STEP / 2
            ),
            vertexFormat: Cesium.EllipsoidSurfaceAppearance.VERTEX_FORMAT,
          }),
        })
      );
    }

    // Add one primitive per bucket (single material color per group)
    buckets.forEach((instances, bucket) => {
      if (instances.length === 0) return;
      const sic = (bucket + 0.5) / 10;
      const color = sicToColor(sic, opacity);
      if (color.alpha < 0.01) return;

      try {
        const primitive = new Cesium.Primitive({
          geometryInstances: instances,
          appearance: new Cesium.EllipsoidSurfaceAppearance({
            material: Cesium.Material.fromType('Color', { color }),
            aboveGround: false,
          }),
          asynchronous: true,
          releaseGeometryInstances: true,
          compressVertices: true,
        });
        collection.add(primitive);
      } catch {
        // Silently skip any geometry errors per bucket
      }
    });

    viewer.scene.primitives.add(collection);
    primitiveRef.current = collection;

    return () => {
      if (primitiveRef.current && !viewer.isDestroyed()) {
        viewer.scene.primitives.remove(primitiveRef.current);
        primitiveRef.current = null;
      }
    };
  }, [viewer, cells, opacity]);

  return null;
}
