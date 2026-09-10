#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GRIB2 to Cesium Wind Layer JSON Converter (Phase 1)
===================================================
Converts a NOAA GFS GRIB2 file containing 10m U and V wind components
into the precise JSON array format required by `cesium-wind-layer`.
"""

import sys
import json
import numpy as np
import xarray as xr
from pathlib import Path

def parse_grib_to_cesium_json(grib_path: str, json_path: str):
    """
    Reads GRIB2 file, extracts 10u and 10v, and writes cesium-wind-layer JSON.
    """
    input_path = Path(grib_path)
    if not input_path.exists():
        print(f"Error: GRIB2 file {grib_path} not found.")
        sys.exit(1)
        
    print(f"Opening GRIB2 file: {grib_path}")
    try:
        # Require cfgrib (and eccodes) to process GRIB2
        ds = xr.open_dataset(input_path, engine='cfgrib')
    except Exception as e:
        print(f"Error opening GRIB2: {e}")
        print("Note: Ensure 'cfgrib' and 'eccodes' C-library are installed.")
        sys.exit(1)

    # NOAA GFS variables for 10m wind are usually 'u10' and 'v10'
    if 'u10' not in ds or 'v10' not in ds:
        print("Error: Variables 'u10' or 'v10' not found in dataset.")
        print(f"Available variables: {list(ds.data_vars)}")
        sys.exit(1)

    u_da = ds['u10']
    v_da = ds['v10']

    # Extract coordinates
    lats = u_da.latitude.values
    lons = u_da.longitude.values

    # Determine grid properties
    nx = len(lons)
    ny = len(lats)
    la1 = float(lats[0])
    la2 = float(lats[-1])
    lo1 = float(lons[0])
    lo2 = float(lons[-1])
    dx = float(abs(lons[1] - lons[0])) if nx > 1 else 1.0
    dy = float(abs(lats[1] - lats[0])) if ny > 1 else 1.0

    # Ensure longitude is in [0, 360] or [-180, 180] appropriately.
    # cesium-wind-layer typically expects longitudes in 0 to 360 if lo1=0.
    
    # Extract flat arrays, replacing NaNs with 0.0 or a fill value
    u_data = np.nan_to_num(u_da.values.flatten(), nan=0.0).tolist()
    v_data = np.nan_to_num(v_da.values.flatten(), nan=0.0).tolist()

    # Format specified by cesium-wind-layer (earth.nullschool.net format)
    # U component
    u_entry = {
        "header": {
            "parameterCategory": 2,
            "parameterNumber": 2,
            "surface1Type": 103,
            "surface1Value": 10,
            "nx": nx,
            "ny": ny,
            "lo1": lo1,
            "lo2": lo2,
            "la1": la1,
            "la2": la2,
            "dx": dx,
            "dy": dy,
            "refTime": str(u_da.time.values) if 'time' in u_da.coords else "2024-01-01T00:00:00Z"
        },
        "data": u_data
    }

    # V component
    v_entry = {
        "header": {
            "parameterCategory": 2,
            "parameterNumber": 3,
            "surface1Type": 103,
            "surface1Value": 10,
            "nx": nx,
            "ny": ny,
            "lo1": lo1,
            "lo2": lo2,
            "la1": la1,
            "la2": la2,
            "dx": dx,
            "dy": dy,
            "refTime": str(v_da.time.values) if 'time' in v_da.coords else "2024-01-01T00:00:00Z"
        },
        "data": v_data
    }

    output_json = [u_entry, v_entry]

    output_path = Path(json_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print("Writing JSON file...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_json, f, separators=(',', ':'))

    print(f"Successfully wrote {json_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Convert GRIB2 wind data to Cesium Wind Layer JSON")
    parser.add_argument("--input", type=str, required=True, help="Path to input NOAA GFS GRIB2 file")
    parser.add_argument("--output", type=str, required=True, help="Path to output JSON file")
    
    args = parser.parse_args()
    parse_grib_to_cesium_json(args.input, args.output)
