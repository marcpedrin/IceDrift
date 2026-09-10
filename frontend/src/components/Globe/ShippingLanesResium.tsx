import React, { useEffect, useRef } from 'react';
import * as Cesium from 'cesium';
import type { Viewer } from 'cesium';

interface ShippingLanesProps {
  viewer: Viewer;
  url: string;
  show: boolean;
}

/**
 * Component to load and render GeoJSON shipping lanes.
 * Renders static, glowing polylines across the oceans.
 */
export const ShippingLanesResium: React.FC<ShippingLanesProps> = ({ viewer, url, show }) => {
  const dataSourceRef = useRef<Cesium.GeoJsonDataSource | null>(null);

  useEffect(() => {
    if (!viewer) return;

    let isMounted = true;
    const dataSource = new Cesium.GeoJsonDataSource('shipping-lanes');

    Cesium.GeoJsonDataSource.load(url).then((ds) => {
      if (!isMounted) return;
      
      const entities = ds.entities.values;
      for (let i = 0; i < entities.length; i++) {
        const entity = entities[i];
        if (entity.polyline) {
          entity.polyline.material = new Cesium.PolylineGlowMaterialProperty({
            glowPower: 0.25,
            taperPower: 1,
            color: Cesium.Color.fromCssColorString('#00ffcc').withAlpha(0.6),
          });
          entity.polyline.width = new Cesium.ConstantProperty(5.0);
          entity.polyline.clampToGround = new Cesium.ConstantProperty(true);
        }
      }
      
      dataSourceRef.current = ds;
      viewer.dataSources.add(ds);
      ds.show = show;
    }).catch(err => {
      console.error("Failed to load shipping lanes GeoJSON:", err);
    });

    return () => {
      isMounted = false;
      if (dataSourceRef.current && !viewer.isDestroyed()) {
        viewer.dataSources.remove(dataSourceRef.current);
        dataSourceRef.current = null;
      }
    };
  }, [viewer, url]); // Only re-run if viewer or URL changes

  useEffect(() => {
    if (dataSourceRef.current) {
      dataSourceRef.current.show = show;
    }
  }, [show]);

  return null;
};
