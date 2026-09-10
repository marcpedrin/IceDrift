import React, { useEffect, useRef, useState } from 'react';
import * as Cesium from 'cesium';
import type { IceCell, Iceberg, Ship, Route, LayerState } from '@/types';
import { IceHeatmapLayer } from './IceHeatmapLayer';
import { IcebergLayer } from './IcebergLayer';
import { ShipLayer } from './ShipLayer';
import { RouteLayer } from './RouteLayer';
import { WindLayerResium } from './WindLayerResium';
import { ShippingLanesResium } from './ShippingLanesResium';

interface CesiumGlobeProps {
  iceCells: IceCell[];
  iceOpacity: number;
  icebergs: Iceberg[];
  ships: Ship[];
  windData: any;
  currentsData: any;
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
  windData,
  currentsData,
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
  const [viewerReady, setViewerReady] = useState(false);

  useEffect(() => {
    if (!containerRef.current || localViewerRef.current) return;

    // ── Optional Ion token ─────────────────────────────────────────────────
    const cesiumToken = import.meta.env.VITE_CESIUM_TOKEN;
    const hasValidToken =
      cesiumToken &&
      cesiumToken !== 'your_cesium_ion_access_token' &&
      cesiumToken.length > 20;

    if (hasValidToken) {
      Cesium.Ion.defaultAccessToken = cesiumToken;
    }

    // ── Viewer: no base layer (we add our own satellite imagery below) ─────
    const viewer = new Cesium.Viewer(containerRef.current, {
      baseLayerPicker: false,
      geocoder: false,
      homeButton: false,
      sceneModePicker: false,
      navigationHelpButton: false,
      animation: false,
      timeline: false,
      fullscreenButton: false,
      selectionIndicator: false,
      infoBox: false,
      shouldAnimate: true,
      requestRenderMode: false,
      // Flat terrain — no Ion token needed, no auth errors
      terrainProvider: new Cesium.EllipsoidTerrainProvider(),
    });

    // ── Remove any auto-added default imagery ─────────────────────────────
    viewer.imageryLayers.removeAll();

    // ── ESRI World Imagery — real satellite, completely FREE, no API key ──
    // This is the same high-res satellite used by ArcGIS/ESRI online maps.
    viewer.imageryLayers.addImageryProvider(
      new Cesium.UrlTemplateImageryProvider({
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        credit: new Cesium.Credit('Esri, Maxar, Earthstar Geographics, and the GIS User Community', true),
        maximumLevel: 19,
      })
    );

    // ── Optional labels overlay (place names) ─────────────────────────────
    // ESRI Reference overlay is transparent — shows borders/labels on top
    viewer.imageryLayers.addImageryProvider(
      new Cesium.UrlTemplateImageryProvider({
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
        credit: new Cesium.Credit('Esri', false),
        maximumLevel: 19,
        // Set alpha low so labels don't overpower satellite
      })
    );
    // Dim the labels layer
    viewer.imageryLayers.get(1).alpha = 0.35;

    // ── Scene tweaks ──────────────────────────────────────────────────────
    viewer.scene.globe.enableLighting = false;
    viewer.scene.globe.showGroundAtmosphere = true;
    viewer.scene.fog.enabled = true;
    viewer.scene.fog.density = 0.00012;
    // Dark sky
    viewer.scene.backgroundColor = new Cesium.Color(0.02, 0.04, 0.08, 1.0);

    // ── Fly to Antarctic overview ─────────────────────────────────────────
    viewer.camera.setView({
      destination: Cesium.Cartesian3.fromDegrees(0, -70, 16_000_000),
      orientation: {
        heading: 0,
        pitch: Cesium.Math.toRadians(-90),
        roll: 0,
      },
    });

    // Animate in
    setTimeout(() => {
      if (!viewer.isDestroyed()) {
        viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(0, -75, 11_000_000),
          orientation: {
            heading: 0,
            pitch: Cesium.Math.toRadians(-90),
            roll: 0,
          },
          duration: 2.5,
          easingFunction: Cesium.EasingFunction.SINUSOIDAL_IN_OUT,
        });
      }
    }, 400);

    localViewerRef.current = viewer;
    viewerRef.current = viewer;
    setViewerReady(true);

    // ── Globe click handler ───────────────────────────────────────────────
    const handler = new Cesium.ScreenSpaceEventHandler(viewer.canvas);
    handler.setInputAction(
      (click: Cesium.ScreenSpaceEventHandler.PositionedEvent) => {
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
      },
      Cesium.ScreenSpaceEventType.LEFT_CLICK
    );

    return () => {
      handler.destroy();
      if (!viewer.isDestroyed()) viewer.destroy();
      localViewerRef.current = null;
      viewerRef.current = null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="absolute inset-0">
      <div ref={containerRef} className="w-full h-full" id="cesium-globe" />

      {/* Layer renderers — rendered as React portals into Cesium's scene.
          Must be mounted AFTER viewer is ready. Hidden div is fine — these
          components add entities/primitives directly to the Cesium viewer. */}
      {viewerReady && localViewerRef.current && (
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
          {layers.routes && (
            <ShippingLanesResium
              viewer={localViewerRef.current}
              url={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/routes/geojson`}
              show={layers.routes}
            />
          )}
          {layers.wind && (
            <WindLayerResium
              viewer={localViewerRef.current}
              data={windData}
              show={layers.wind}
            />
          )}
          {layers.currents && (
            <WindLayerResium
              viewer={localViewerRef.current}
              data={currentsData}
              show={layers.currents}
              options={{
                windOptions: {
                  colorScale: [
                    'rgb(0, 50, 100)',
                    'rgb(0, 100, 150)',
                    'rgb(0, 150, 200)',
                    'rgb(50, 200, 250)',
                    'rgb(100, 250, 255)'
                  ],
                  velocityScale: 0.05,
                  lineWidth: 3,
                }
              }}
            />
          )}
        </>
      )}
    </div>
  );
};
