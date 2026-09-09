import { useEffect, useRef } from 'react';
import * as Cesium from 'cesium';
import type { Iceberg } from '@/types';

interface IcebergLayerProps {
  viewer: Cesium.Viewer;
  icebergs: Iceberg[];
  showTrajectories: boolean;
  showUncertainty: boolean;
  onIcebergClick: (iceberg: Iceberg) => void;
}

// Size → pixel radius
function sizeToPixels(sizeKm2: number): number {
  if (sizeKm2 > 2000) return 18;
  if (sizeKm2 > 500) return 14;
  if (sizeKm2 > 100) return 10;
  return 7;
}

export function IcebergLayer({
  viewer,
  icebergs,
  showTrajectories,
  showUncertainty,
  onIcebergClick,
}: IcebergLayerProps) {
  const dsRef = useRef<Cesium.CustomDataSource | null>(null);
  const handlerRef = useRef<Cesium.ScreenSpaceEventHandler | null>(null);
  const icebergMapRef = useRef<Map<string, Iceberg>>(new Map());

  useEffect(() => {
    if (!viewer || viewer.isDestroyed()) return;

    // Clean up previous
    if (dsRef.current) {
      viewer.dataSources.remove(dsRef.current, true);
      dsRef.current = null;
    }
    if (handlerRef.current) {
      if (!handlerRef.current.isDestroyed()) handlerRef.current.destroy();
      handlerRef.current = null;
    }

    const ds = new Cesium.CustomDataSource('icebergs');
    icebergMapRef.current = new Map();

    for (const berg of icebergs) {
      const pixelSize = sizeToPixels(berg.size_km2);
      icebergMapRef.current.set(berg.id, berg);

      // Main point
      const entity = ds.entities.add({
        id: `iceberg-${berg.id}`,
        position: Cesium.Cartesian3.fromDegrees(berg.lon, berg.lat),
        point: {
          pixelSize,
          color: Cesium.Color.CYAN,
          outlineColor: Cesium.Color.WHITE,
          outlineWidth: 1.5,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
          scaleByDistance: new Cesium.NearFarScalar(1e5, 2.0, 8e6, 0.5),
          translucencyByDistance: new Cesium.NearFarScalar(1e5, 1.0, 1e7, 0.6),
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        },
        label: {
          text: berg.id,
          font: '11px Inter, sans-serif',
          fillColor: Cesium.Color.CYAN,
          style: Cesium.LabelStyle.FILL,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          pixelOffset: new Cesium.Cartesian2(0, -(pixelSize + 4)),
          translucencyByDistance: new Cesium.NearFarScalar(1e5, 1.0, 3e6, 0.0),
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        },
      });

      // Trajectory polyline
      if (showTrajectories && berg.trajectory.length > 1) {
        const positions = berg.trajectory.map((pt) =>
          Cesium.Cartesian3.fromDegrees(pt.lon, pt.lat)
        );

        ds.entities.add({
          id: `trajectory-${berg.id}`,
          polyline: {
            positions,
            width: 1.5,
            material: new Cesium.PolylineGlowMaterialProperty({
              glowPower: 0.2,
              color: new Cesium.Color(0, 0.9, 1, 0.7),
            }),
            clampToGround: true,
            shadows: Cesium.ShadowMode.DISABLED,
          },
        });
      }

      // Uncertainty cone ellipses
      if (showUncertainty && berg.uncertainty_cone.length > 0) {
        // Show every 2nd cone point to reduce entity count
        for (let i = 2; i < berg.uncertainty_cone.length; i += 2) {
          const cone = berg.uncertainty_cone[i];
          const alpha = Math.max(0.05, 0.25 - i * 0.02);
          ds.entities.add({
            id: `cone-${berg.id}-${i}`,
            position: Cesium.Cartesian3.fromDegrees(cone.center_lon, cone.center_lat),
            ellipse: {
              semiMajorAxis: cone.radius_km * 1000,
              semiMinorAxis: cone.radius_km * 1000,
              material: new Cesium.Color(0, 0.9, 1, alpha),
              outline: true,
              outlineColor: new Cesium.Color(0, 0.9, 1, alpha * 2),
              outlineWidth: 1,
              heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
            },
          });
        }
      }
    }

    viewer.dataSources.add(ds);
    dsRef.current = ds;

    // Click handler
    const handler = new Cesium.ScreenSpaceEventHandler(viewer.canvas);
    handler.setInputAction((click: Cesium.ScreenSpaceEventHandler.PositionedEvent) => {
      const picked = viewer.scene.pick(click.position);
      if (Cesium.defined(picked) && picked.id) {
        const entityId: string = typeof picked.id === 'string' ? picked.id : picked.id?.id || '';
        if (entityId.startsWith('iceberg-')) {
          const bergId = entityId.replace('iceberg-', '');
          const berg = icebergMapRef.current.get(bergId);
          if (berg) onIcebergClick(berg);
        }
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

    handlerRef.current = handler;

    return () => {
      if (dsRef.current && !viewer.isDestroyed()) {
        viewer.dataSources.remove(dsRef.current, true);
        dsRef.current = null;
      }
      if (handlerRef.current) {
        if (!handlerRef.current.isDestroyed()) handlerRef.current.destroy();
        handlerRef.current = null;
      }
    };
  }, [viewer, icebergs, showTrajectories, showUncertainty]); // eslint-disable-line

  return null;
}
