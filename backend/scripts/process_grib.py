#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GFS Wind Data to Cesium Wind Layer JSON Converter
===================================================
Downloads the latest NOAA GFS GRIB2 using Herbie, extracts 10m U and V,
and writes the cesium-wind-layer JSON array format.
"""

import sys
import json
import numpy as np
import xarray as xr
from pathlib import Path
from datetime import datetime, timedelta

def process_grib(output_json: str):
    """
    Downloads latest GFS, extracts 10u and 10v, and writes JSON.
    """
    try:
        from herbie import Herbie
    except ImportError:
        print("Herbie not installed. Run: pip install herbie-data")
        _generate_synthetic_wind(output_json)
        return

    output_path = Path(output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Try fetching the latest available GFS (typically 0, 6, 12, or 18z)
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    print(f"Fetching latest NOAA GFS for {date_str} using Herbie...")
    
    try:
        # Get the latest GFS run
        H = Herbie(date=date_str, model="gfs", product="pgrb2.0p25", fxx=0)
        # We only need U and V components of wind at 10m
        ds = H.xarray(":(?:U|V)GRD:10 m above ground:")
    except Exception as e:
        print(f"Failed to fetch GFS via Herbie: {e}")
        # Try yesterday if today's run isn't available yet
        try:
            yesterday_str = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
            H = Herbie(date=yesterday_str, model="gfs", product="pgrb2.0p25", fxx=0)
            ds = H.xarray(":(?:U|V)GRD:10 m above ground:")
        except Exception as e2:
            print(f"Failed to fetch fallback GFS: {e2}")
            _generate_synthetic_wind(output_json)
            return

    try:
        # Depending on eccodes/cfgrib versions, variable names might be 'u10'/'v10' or 'u10m'/'v10m'
        u_var = next((v for v in ['u10', 'u10m', '10u', 'UGRD'] if v in ds.variables), None)
        v_var = next((v for v in ['v10', 'v10m', '10v', 'VGRD'] if v in ds.variables), None)
        
        if not u_var or not v_var:
            print(f"Error: Wind variables not found. Available: {list(ds.variables)}")
            _generate_synthetic_wind(output_json)
            return

        u_da = ds[u_var]
        v_da = ds[v_var]

        # Extract coordinates
        lats = u_da.latitude.values
        lons = u_da.longitude.values

        nx = len(lons)
        ny = len(lats)
        la1 = float(lats[0])
        la2 = float(lats[-1])
        lo1 = float(lons[0])
        lo2 = float(lons[-1])
        dx = float(abs(lons[1] - lons[0])) if nx > 1 else 1.0
        dy = float(abs(lats[1] - lats[0])) if ny > 1 else 1.0
        
        u_data = np.nan_to_num(u_da.values.flatten(), nan=0.0).tolist()
        v_data = np.nan_to_num(v_da.values.flatten(), nan=0.0).tolist()

        ref_time = str(u_da.time.values) if 'time' in u_da.coords else "2024-01-01T00:00:00Z"

        u_entry = {
            "header": {
                "parameterCategory": 2, "parameterNumber": 2,
                "surface1Type": 103, "surface1Value": 10,
                "nx": nx, "ny": ny,
                "lo1": lo1, "lo2": lo2, "la1": la1, "la2": la2,
                "dx": dx, "dy": dy,
                "refTime": ref_time
            },
            "data": u_data
        }

        v_entry = {
            "header": {
                "parameterCategory": 2, "parameterNumber": 3,
                "surface1Type": 103, "surface1Value": 10,
                "nx": nx, "ny": ny,
                "lo1": lo1, "lo2": lo2, "la1": la1, "la2": la2,
                "dx": dx, "dy": dy,
                "refTime": ref_time
            },
            "data": v_data
        }

        output_data = [u_entry, v_entry]

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, separators=(',', ':'))

        print(f"Successfully processed GFS and wrote {json_path}")
        
    except Exception as e:
        print(f"Error processing Xarray dataset: {e}")
        _generate_synthetic_wind(output_json)


def _generate_synthetic_wind(output_json: str):
    print("Generating synthetic global wind fallback...")
    nx = 360
    ny = 181
    u_data = []
    v_data = []
    # Generate simple sine wave winds
    for lat_idx in range(ny):
        lat = 90.0 - lat_idx
        for lon_idx in range(nx):
            lon = float(lon_idx)
            u = 5.0 * np.sin(np.radians(lat * 3))
            v = 2.0 * np.cos(np.radians(lon * 2))
            u_data.append(u)
            v_data.append(v)
            
    header_base = {
        "surface1Type": 103, "surface1Value": 10,
        "nx": nx, "ny": ny,
        "lo1": 0.0, "lo2": 359.0, "la1": 90.0, "la2": -90.0,
        "dx": 1.0, "dy": 1.0,
        "refTime": "2024-01-01T00:00:00Z"
    }
    
    u_header = dict(header_base, parameterCategory=2, parameterNumber=2)
    v_header = dict(header_base, parameterCategory=2, parameterNumber=3)
    
    data = [
        {"header": u_header, "data": u_data},
        {"header": v_header, "data": v_data}
    ]
    
    Path(output_json).parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(data, f, separators=(',', ':'))
    print(f"Wrote synthetic wind to {output_json}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Download/Process GFS Wind to JSON")
    parser.add_argument("--output", type=str, required=True, help="Path to output JSON")
    args = parser.parse_args()
    process_grib(args.output)
