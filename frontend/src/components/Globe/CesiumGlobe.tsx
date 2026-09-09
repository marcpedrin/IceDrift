import React, { useEffect, useRef, useCallback } from 'react';
import * as Cesium from 'cesium';
import type { IceCell, Iceberg, Ship, Route, LayerState } from '@/types';
import { IceHeatmapLayer } from './IceHeatmapLayer';
import { IcebergLayer } from './IcebergLayer';
import { ShipLayer } from './ShipLayer';
import { RouteLayer } from './RouteLayer';

interface CesiumGlobeProps {
  iceCells: IceCell[];
  iceOpacity: number;
  icebergs: Iceberg[];
  ships: Ship[];
  route: Route | null;
  layers: LayerState;
  onIcebergClick: (iceberg: Iceberg) => void;
  onShipClick: (ship: Ship) => void;
  onRouteClick: (route: Route) => void;
  onGlobeClick?: (lat: number, lon: number) => void;
  viewerRef: React.MutableRefObject<Cesium.Viewer | null>;
}

export const CesiumGlobe: React.FC<CesiumGlobeProps> = ({
  iceCells,
  iceOpacity,
  icebergs,
  ships,
  route,
  layers,
  onIcebergClick,
  onShipClick,
  onRouteClick,
  onGlobeClick,
  viewerRef,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const localViewerRef = useRef<Cesium.Viewer | null>(null);

  useEffect(() => {
    if (!containerRef.current || localViewerRef.current) return;

    // Create Cesium Viewer
    const viewer = new Cesium.Viewer(containerRef.current, {
      // Use Cesium Ion token (set in main.tsx)
      imageryProvider: new Cesium.IonImageryProvider({ assetId: 3 }), // Cesium World Imagery
      terrainProvider: Cesium.createWorldTerrainAsync ? undefined : new Cesium.EllipsoidTerrainProvider(),
      baseLayerPicker: false,
      geocoder: false,
      homeButton: false,
      sceneModePicker: false,
      navigationHelpButton: false,
      animation: false,
      timeline: false,
      fullscreenButton: false,
      vrButton: false,
      selectionIndicator: false,
      infoBox: false,
      shouldAnimate: true,
      requestRenderMode: false,
      maximumRenderTimeChange: Infinity,
    });

    // Configure scene
    viewer.scene.globe.enableLighting = true;
    viewer.scene.globe.showGroundAtmosphere = true;
    viewer.scene.fog.enabled = true;
    viewer.scene.fog.density = 0.0001;
    viewer.scene.sky = new Cesium.SkyBox({
      sources: {
        positiveX: undefined, negativeX: undefined,
        positiveY: undefined, negativeY: undefined,
        positiveZ: undefined, negativeZ: undefined,
      } as any,
    });

    // Dark ocean appearance
    viewer.scene.globe.baseColor = new Cesium.Color(0.04, 0.08, 0.15, 1.0);

    // Fly to Antarctic view on startup
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(0, -70, 12_000_000),
      orientation: {
        heading: 0,
        pitch: Cesium.Math.toRadians(-90),
        roll: 0,
      },
      duration: 2,
    });

    localViewerRef.current = viewer;
    viewerRef.current = viewer;

    // Click handler
    const handler = new Cesium.ScreenSpaceEventHandler(viewer.canvas);
    handler.setInputAction((click: Cesium.ScreenSpaceEventHandler.PositionedEvent) => {
      const picked = viewer.scene.pick(click.position);
      if (!Cesium.defined(picked) && onGlobeClick) {
        const ray = viewer.camera.getPickRay(click.position);
        if (ray) {
          const pos = viewer.scene.globe.pick(ray, viewer.scene);
          if (pos) {
            const carto = Cesium.Ellipsoid.WGS84.cartesianToCartographic(pos);
            onGlobeClick(
              Cesium.Math.toDegrees(carto.latitude),
              Cesium.Math.toDegrees(carto.longitude)
            );
          }
        }
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

    return () => {
      handler.destroy();
      viewer.destroy();
      localViewerRef.current = null;
      viewerRef.current = null;
    };
  }, []); // eslint-disable-line

  return (
    <div className="absolute inset-0">
      <div ref={containerRef} className="w-full h-full" id="cesium-globe" />

      {/* Render layers via imperative Cesium APIs once viewer is ready */}
      {localViewerRef.current && (
        <>
          {layers.iceHeatmap && (
            <IceHeatmapLayer
              viewer={localViewerRef.current}
              cells={iceCells}
              opacity={iceOpacity}
            />
          )}
          {layers.icebergs && (
            <IcebergLayer
              viewer={localViewerRef.current}
              icebergs={icebergs}
              showTrajectories={layers.trajectories}
              showUncertainty={layers.uncertainty}
              onIcebergClick={onIcebergClick}
            />
          )}
          {layers.ships && (
            <ShipLayer
              viewer={localViewerRef.current}
              ships={ships}
              onShipClick={onShipClick}
            />
          )}
          {layers.routes && route && (
            <RouteLayer
              viewer={localViewerRef.current}
              route={route}
              onRouteClick={onRouteClick}
            />
          )}
        </>
      )}
    </div>
  );
};
