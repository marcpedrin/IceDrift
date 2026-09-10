import React from 'react';
import { GeoJsonDataSource } from 'resium';
import * as Cesium from 'cesium';

interface ShippingLanesProps {
  url: string;
  show: boolean;
}

/**
 * Resium component to load and render GeoJSON shipping lanes.
 * Renders static, glowing polylines across the oceans.
 */
export const ShippingLanesResium: React.FC<ShippingLanesProps> = ({ url, show }) => {
  // Custom styling function applied when the GeoJSON loads
  const handleLoad = (dataSource: Cesium.GeoJsonDataSource) => {
    const entities = dataSource.entities.values;
    for (let i = 0; i < entities.length; i++) {
      const entity = entities[i];
      if (entity.polyline) {
        // Create a glowing effect using PolylineGlowMaterialProperty
        entity.polyline.material = new Cesium.PolylineGlowMaterialProperty({
          glowPower: 0.25,
          taperPower: 1,
          color: Cesium.Color.fromCssColorString('#00ffcc').withAlpha(0.6),
        });
        entity.polyline.width = new Cesium.ConstantProperty(5.0);
        // Ensure lanes sit slightly above the surface to avoid depth fighting
        entity.polyline.clampToGround = new Cesium.ConstantProperty(true);
      }
    }
  };

  return (
    <GeoJsonDataSource
      data={url}
      show={show}
      onLoad={handleLoad}
      // Provide fallback generic styling (overridden by onLoad)
      stroke={Cesium.Color.fromCssColorString('#00ffcc')}
      strokeWidth={2}
    />
  );
};
