import React, { useEffect, useRef, useState } from 'react';
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
  const [viewerReady, setViewerReady] = useState(false);

  useEffect(() => {
    if (!containerRef.current || localViewerRef.current) return;

    // ── Set Ion token if available ─────────────────────────────────────────
    const cesiumToken = import.meta.env.VITE_CESIUM_TOKEN;
    const hasValidToken =
      cesiumToken &&
      cesiumToken !== 'your_cesium_ion_access_token' &&
      cesiumToken.length > 20;

    if (hasValidToken) {
      Cesium.Ion.defaultAccessToken = cesiumToken;
    }

    // ── Create Viewer (no baseLayer option – we manage imagery manually) ───
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
      maximumRenderTimeChange: Infinity,
      // ── FREE terrain: flat ellipsoid, no Ion token required ────────────
      // Without this, Cesium defaults to CesiumWorldTerrain which
      // requires a valid Ion token and throws auth errors without one.
      terrainProvider: new Cesium.EllipsoidTerrainProvider(),
    });

    // ── Replace default imagery with a free provider ───────────────────────
    // Remove all default layers (Bing Maps requires API key — skip it)
    viewer.imageryLayers.removeAll();

    if (hasValidToken) {
      // Cesium Ion World Imagery – free tier, high quality
      Cesium.createWorldImageryAsync()
        .then((provider) => {
          if (!viewer.isDestroyed()) {
            viewer.imageryLayers.addImageryProvider(provider);
          }
        })
        .catch(() => {
          console.warn('[Polaris] Ion imagery failed, falling back to OpenStreetMap');
          if (!viewer.isDestroyed()) {
            addOsmLayer(viewer);
          }
        });
    } else {
      // Free fallback: OpenStreetMap (no key needed)
      addOsmLayer(viewer);
    }

    // ── Scene config ──────────────────────────────────────────────────────
    viewer.scene.globe.enableLighting = false;
    viewer.scene.globe.showGroundAtmosphere = true;
    viewer.scene.fog.enabled = true;
    viewer.scene.fog.density = 0.0001;

    // Dark ocean/polar tint
    viewer.scene.globe.baseColor = new Cesium.Color(0.04, 0.08, 0.15, 1.0);

    // ── Fly to Antarctic overview ─────────────────────────────────────────
    viewer.camera.setView({
      destination: Cesium.Cartesian3.fromDegrees(0, -70, 14_000_000),
      orientation: {
        heading: 0,
        pitch: Cesium.Math.toRadians(-90),
        roll: 0,
      },
    });

    // Animate in after a brief delay
    setTimeout(() => {
      if (!viewer.isDestroyed()) {
        viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(0, -70, 10_000_000),
          orientation: {
            heading: 0,
            pitch: Cesium.Math.toRadians(-90),
            roll: 0,
          },
          duration: 2.5,
        });
      }
    }, 500);

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
      if (!viewer.isDestroyed()) {
        viewer.destroy();
      }
      localViewerRef.current = null;
      viewerRef.current = null;
      // Do NOT call setViewerReady(false) here – setting state on an
      // unmounting component causes React reconciler errors.
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="absolute inset-0">
      <div ref={containerRef} className="w-full h-full" id="cesium-globe" />

      {viewerReady && localViewerRef.current && (
        <div style={{ display: 'none' }}>
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
        </div>
      )}
    </div>
  );
};

// ── Helper: add OSM free imagery ────────────────────────────────────────────
function addOsmLayer(viewer: Cesium.Viewer) {
  try {
    // UrlTemplateImageryProvider works in all modern Cesium versions
    viewer.imageryLayers.addImageryProvider(
      new Cesium.UrlTemplateImageryProvider({
        url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        subdomains: ['a', 'b', 'c'],
        credit: new Cesium.Credit('© OpenStreetMap contributors', true),
        maximumLevel: 19,
      })
    );
  } catch {
    // Last resort: use Cesium's built-in NaturalEarth imagery (offline, no network)
    try {
      Cesium.TileMapServiceImageryProvider.fromUrl(
        Cesium.buildModuleUrl('Assets/Textures/NaturalEarthII')
      ).then((provider) => {
        if (!viewer.isDestroyed()) {
          viewer.imageryLayers.addImageryProvider(provider);
        }
      });
    } catch {
      console.warn('[Polaris] All imagery providers failed – globe will show terrain only');
    }
  }
}
