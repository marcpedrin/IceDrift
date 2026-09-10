import React from 'react';
import { PointPrimitiveCollection, PointPrimitive } from 'resium';
import * as Cesium from 'cesium';
import type { Iceberg } from '@/types';

interface IcebergsResiumProps {
  icebergs: Iceberg[];
  show: boolean;
  onIcebergClick?: (iceberg: Iceberg) => void;
}

/**
 * Resium component to render a large dataset of Icebergs as PointPrimitives.
 * PointPrimitiveCollection is highly optimized for performance.
 */
export const IcebergsResium: React.FC<IcebergsResiumProps> = ({ icebergs, show, onIcebergClick }) => {
  if (!show || icebergs.length === 0) return null;

  return (
    <PointPrimitiveCollection show={show}>
      {icebergs.map((iceberg) => (
        <PointPrimitive
          key={iceberg.id}
          position={Cesium.Cartesian3.fromDegrees(iceberg.lon, iceberg.lat)}
          color={Cesium.Color.fromCssColorString('#00e5ff')}
          outlineColor={Cesium.Color.WHITE}
          outlineWidth={1}
          pixelSize={8}
          // Store the iceberg data in the primitive's id field so it can be 
          // retrieved during interaction/picking events
          id={iceberg}
        />
      ))}
    </PointPrimitiveCollection>
  );
};
