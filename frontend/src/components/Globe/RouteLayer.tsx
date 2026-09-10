import { useEffect, useRef } from 'react';
import * as Cesium from 'cesium';
import type { Route } from '@/types';

interface RouteLayerProps {
  viewer: Cesium.Viewer;
  route: Route;
  onRouteClick: (route: Route) => void;
}

function riskToColor(risk: number): Cesium.Color {
  if (risk < 0.3) return new Cesium.Color(0, 0.9, 0.42, 0.9); // green
  if (risk < 0.6) return new Cesium.Color(1, 0.67, 0, 0.9);    // orange
  return new Cesium.Color(1, 0.27, 0.27, 0.9);                  // red
}

export function RouteLayer({ viewer, route, onRouteClick }: RouteLayerProps) {
  const dsRef = useRef<Cesium.CustomDataSource | null>(null);

  useEffect(() => {
    if (!viewer || viewer.isDestroyed() || !route) return;
    if (dsRef.current && !viewer.isDestroyed()) {
      viewer.dataSources.remove(dsRef.current, true);
      dsRef.current = null;
    }

    const ds = new Cesium.CustomDataSource('routes');

    // Primary route – thick glowing green line
    const positions = route.waypoints.map((wp) =>
      Cesium.Cartesian3.fromDegrees(wp.lon, wp.lat)
    );

    if (positions.length > 1) {
      // Glow outline
      ds.entities.add({
        id: 'route-glow',
        polyline: {
          positions,
          width: 8,
          material: new Cesium.PolylineGlowMaterialProperty({
            glowPower: 0.3,
            color: new Cesium.Color(0, 1, 0.42, 0.2),
          }),
          clampToGround: true,
        },
      });
      // Main line (solid)
      ds.entities.add({
        id: 'route-main',
        polyline: {
          positions,
          width: 3,
          material: new Cesium.Color(0, 0.9, 0.42, 1),
          clampToGround: true,
        },
      });
    }

    // Waypoint circles
    for (let i = 0; i < route.waypoints.length; i++) {
      const wp = route.waypoints[i];
      const isStart = i === 0;
      const isEnd = i === route.waypoints.length - 1;
      const isEndpoint = isStart || isEnd;
      
      let fillColor;
      let outlineColor = Cesium.Color.WHITE;
      
      if (isStart) {
        fillColor = new Cesium.Color(0, 0.9, 0.42, 1); // Green
      } else if (isEnd) {
        fillColor = new Cesium.Color(1, 0.27, 0.27, 1); // Red
      } else {
        fillColor = riskToColor(wp.risk_score);
        outlineColor = Cesium.Color.WHITE.withAlpha(0.5);
      }

      ds.entities.add({
        id: `waypoint-${i}`,
        position: Cesium.Cartesian3.fromDegrees(wp.lon, wp.lat),
        point: {
          pixelSize: isEndpoint ? 16 : 5,
          color: fillColor,
          outlineColor: outlineColor,
          outlineWidth: isEndpoint ? 3 : 1,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
          scaleByDistance: new Cesium.NearFarScalar(1e4, 2.0, 8e6, 0.4),
        },
      });
    }

    // Alternative routes (dashed gray)
    for (let a = 0; a < route.alternatives.length; a++) {
      const altPositions = route.alternatives[a].map((wp) =>
        Cesium.Cartesian3.fromDegrees(wp.lon, wp.lat)
      );
      if (altPositions.length > 1) {
        ds.entities.add({
          id: `alt-route-${a}`,
          polyline: {
            positions: altPositions,
            width: 1.5,
            material: new Cesium.PolylineDashMaterialProperty({
              color: Cesium.Color.GRAY.withAlpha(0.5),
              dashLength: 16,
            }),
            clampToGround: true,
          },
        });
      }
    }

    viewer.dataSources.add(ds);
    dsRef.current = ds;

    return () => {
      if (dsRef.current && !viewer.isDestroyed()) {
        viewer.dataSources.remove(dsRef.current, true);
        dsRef.current = null;
      }
    };
  }, [viewer, route]); // eslint-disable-line

  return null;
}
