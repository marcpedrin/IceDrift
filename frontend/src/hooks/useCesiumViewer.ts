import { useRef, useCallback } from 'react';
import * as Cesium from 'cesium';

export interface CesiumViewerRef {
  viewer: Cesium.Viewer | null;
}

export function useCesiumViewer() {
  const viewerRef = useRef<Cesium.Viewer | null>(null);

  const setViewer = useCallback((viewer: Cesium.Viewer) => {
    viewerRef.current = viewer;
  }, []);

  const flyToAntarctic = useCallback(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(0, -70, 8_000_000),
      orientation: { heading: 0, pitch: Cesium.Math.toRadians(-90), roll: 0 },
      duration: 2,
    });
  }, []);

  const flyToPosition = useCallback(
    (lat: number, lon: number, altitudeM = 500_000, duration = 2) => {
      const viewer = viewerRef.current;
      if (!viewer) return;
      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(lon, lat, altitudeM),
        duration,
      });
    },
    []
  );

  const zoomToIceberg = useCallback((lat: number, lon: number) => {
    flyToPosition(lat, lon, 50_000, 1.5);
  }, [flyToPosition]);

  const zoomToRoute = useCallback((waypoints: { lat: number; lon: number }[]) => {
    const viewer = viewerRef.current;
    if (!viewer || waypoints.length === 0) return;

    const positions = waypoints.map((wp) =>
      Cesium.Cartesian3.fromDegrees(wp.lon, wp.lat)
    );

    const bs = Cesium.BoundingSphere.fromPoints(positions);
    viewer.camera.flyToBoundingSphere(bs, {
      duration: 2,
      offset: new Cesium.HeadingPitchRange(0, Cesium.Math.toRadians(-60), bs.radius * 3),
    });
  }, []);

  const screenToLatLon = useCallback(
    (x: number, y: number): { lat: number; lon: number } | null => {
      const viewer = viewerRef.current;
      if (!viewer) return null;
      const ray = viewer.camera.getPickRay(new Cesium.Cartesian2(x, y));
      if (!ray) return null;
      const pos = viewer.scene.globe.pick(ray, viewer.scene);
      if (!pos) return null;
      const carto = Cesium.Ellipsoid.WGS84.cartesianToCartographic(pos);
      return {
        lat: Cesium.Math.toDegrees(carto.latitude),
        lon: Cesium.Math.toDegrees(carto.longitude),
      };
    },
    []
  );

  return {
    viewerRef,
    setViewer,
    flyToAntarctic,
    flyToPosition,
    zoomToIceberg,
    zoomToRoute,
    screenToLatLon,
  };
}
