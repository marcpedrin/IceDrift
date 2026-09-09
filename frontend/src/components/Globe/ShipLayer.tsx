import { useEffect, useRef } from 'react';
import * as Cesium from 'cesium';
import type { Ship, ShipType } from '@/types';

const SHIP_COLORS: Record<ShipType, Cesium.Color> = {
  cargo: Cesium.Color.ORANGE,
  tanker: Cesium.Color.YELLOW,
  passenger: Cesium.Color.fromCssColorString('#ff69b4'),
  icebreaker: Cesium.Color.fromCssColorString('#00e5ff'),
  research: Cesium.Color.fromCssColorString('#7fff00'),
  supply: Cesium.Color.fromCssColorString('#dda0dd'),
  unknown: Cesium.Color.GRAY,
};

interface ShipLayerProps {
  viewer: Cesium.Viewer;
  ships: Ship[];
  onShipClick: (ship: Ship) => void;
}

export function ShipLayer({ viewer, ships, onShipClick }: ShipLayerProps) {
  const dsRef = useRef<Cesium.CustomDataSource | null>(null);
  const handlerRef = useRef<Cesium.ScreenSpaceEventHandler | null>(null);
  const shipMapRef = useRef<Map<string, Ship>>(new Map());

  useEffect(() => {
    if (!viewer || viewer.isDestroyed()) return;

    if (dsRef.current) {
      viewer.dataSources.remove(dsRef.current, true);
      dsRef.current = null;
    }
    if (handlerRef.current) {
      if (!handlerRef.current.isDestroyed()) handlerRef.current.destroy();
      handlerRef.current = null;
    }

    const ds = new Cesium.CustomDataSource('ships');
    shipMapRef.current = new Map();

    for (const ship of ships) {
      shipMapRef.current.set(ship.mmsi, ship);
      const color = SHIP_COLORS[ship.ship_type] ?? Cesium.Color.GRAY;

      // Ship point
      ds.entities.add({
        id: `ship-${ship.mmsi}`,
        position: Cesium.Cartesian3.fromDegrees(ship.lon, ship.lat),
        point: {
          pixelSize: ship.ship_type === 'icebreaker' ? 10 : 8,
          color,
          outlineColor: Cesium.Color.WHITE.withAlpha(0.8),
          outlineWidth: 1.5,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
          scaleByDistance: new Cesium.NearFarScalar(1e5, 2.5, 8e6, 0.6),
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        },
        label: {
          text: ship.name,
          font: '10px Inter, sans-serif',
          fillColor: color,
          style: Cesium.LabelStyle.FILL,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          pixelOffset: new Cesium.Cartesian2(0, -14),
          translucencyByDistance: new Cesium.NearFarScalar(1e5, 1.0, 2e6, 0.0),
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        },
      });

      // Speed/heading arrow (billboard simulation using tiny polyline)
      if (ship.speed_knots > 0.5) {
        const headingRad = (ship.course_deg * Math.PI) / 180;
        const arrowDist = 0.02; // degrees
        const arrLon = ship.lon + arrowDist * Math.sin(headingRad);
        const arrLat = ship.lat + arrowDist * Math.cos(headingRad);
        ds.entities.add({
          id: `ship-heading-${ship.mmsi}`,
          polyline: {
            positions: [
              Cesium.Cartesian3.fromDegrees(ship.lon, ship.lat),
              Cesium.Cartesian3.fromDegrees(arrLon, arrLat),
            ],
            width: 2,
            material: color.withAlpha(0.7),
            clampToGround: true,
          },
        });
      }

      // 24h history trail
      if (ship.history.length > 1) {
        const histPositions = ship.history.map((h) =>
          Cesium.Cartesian3.fromDegrees(h.lon, h.lat)
        );
        histPositions.push(Cesium.Cartesian3.fromDegrees(ship.lon, ship.lat));

        ds.entities.add({
          id: `ship-trail-${ship.mmsi}`,
          polyline: {
            positions: histPositions,
            width: 1,
            material: new Cesium.PolylineDashMaterialProperty({
              color: color.withAlpha(0.35),
              dashLength: 8,
            }),
            clampToGround: true,
          },
        });
      }
    }

    viewer.dataSources.add(ds);
    dsRef.current = ds;

    const handler = new Cesium.ScreenSpaceEventHandler(viewer.canvas);
    handler.setInputAction((click: Cesium.ScreenSpaceEventHandler.PositionedEvent) => {
      const picked = viewer.scene.pick(click.position);
      if (Cesium.defined(picked) && picked.id) {
        const entityId: string = typeof picked.id === 'string' ? picked.id : picked.id?.id || '';
        if (entityId.startsWith('ship-') && !entityId.includes('heading') && !entityId.includes('trail')) {
          const mmsi = entityId.replace('ship-', '');
          const ship = shipMapRef.current.get(mmsi);
          if (ship) onShipClick(ship);
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
  }, [viewer, ships]); // eslint-disable-line

  return null;
}
