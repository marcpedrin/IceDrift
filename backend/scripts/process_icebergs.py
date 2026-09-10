#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Iceberg Processing Script (Phase 1)
===================================
Reads raw historical iceberg tracking data (CSV) containing iceberg_id, lat, lon, timestamp.
Calculates the drift heading (degrees) and speed (m/s) using the Haversine and Bearing formulas.
Outputs a processed CSV ready for Cesium PointPrimitive rendering.
"""

import csv
import math
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# Earth radius in meters
R_EARTH = 6371000.0

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points in meters."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R_EARTH * c

def initial_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the initial bearing (heading) from point 1 to point 2 in degrees."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    lambda1 = math.radians(lon1)
    lambda2 = math.radians(lon2)
    delta_lambda = lambda2 - lambda1

    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - \
        math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    
    theta = math.atan2(y, x)
    # Convert to degrees and normalize to 0-360
    return (math.degrees(theta) + 360.0) % 360.0

def process_icebergs(input_csv: str, output_csv: str):
    """
    Reads raw USNIC CSV, sorts by time per iceberg, computes speed & heading, 
    and writes to the output CSV.
    Expected input headers: iceberg_id, lat, lon, timestamp
    """
    input_path = Path(input_csv)
    if not input_path.exists():
        print(f"Error: Input file {input_csv} not found.")
        return

    # 1. Read and group data
    tracks = defaultdict(list)
    with open(input_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            iceberg_id = row['iceberg_id'].strip()
            lat = float(row['lat'])
            lon = float(row['lon'])
            # Assuming ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ
            timestamp_str = row['timestamp'].strip()
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            try:
                dt = datetime.fromisoformat(timestamp_str)
            except ValueError:
                # Fallback format parsing
                dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            
            tracks[iceberg_id].append({
                'lat': lat,
                'lon': lon,
                'dt': dt,
                'timestamp': row['timestamp']
            })

    processed_rows = []

    # 2. Process each track
    for iceberg_id, points in tracks.items():
        # Sort chronologically
        points.sort(key=lambda p: p['dt'])
        
        for i in range(len(points)):
            current = points[i]
            
            if i < len(points) - 1:
                # Calculate vector to the NEXT point
                next_pt = points[i + 1]
                distance_m = haversine_distance(current['lat'], current['lon'], next_pt['lat'], next_pt['lon'])
                time_diff_s = (next_pt['dt'] - current['dt']).total_seconds()
                
                speed_ms = distance_m / time_diff_s if time_diff_s > 0 else 0.0
                heading_deg = initial_bearing(current['lat'], current['lon'], next_pt['lat'], next_pt['lon'])
            else:
                # Last point: inherit velocity and heading from the previous segment, or 0 if only one point
                if i > 0:
                    speed_ms = processed_rows[-1]['velocity_ms']
                    heading_deg = processed_rows[-1]['heading_deg']
                else:
                    speed_ms = 0.0
                    heading_deg = 0.0
            
            processed_rows.append({
                'iceberg_id': iceberg_id,
                'lat': current['lat'],
                'lon': current['lon'],
                'timestamp': current['timestamp'],
                'velocity_ms': round(speed_ms, 3),
                'heading_deg': round(heading_deg, 1)
            })

    # 3. Write output
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, mode='w', newline='', encoding='utf-8') as f:
        fieldnames = ['iceberg_id', 'lat', 'lon', 'timestamp', 'velocity_ms', 'heading_deg']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(processed_rows)

    print(f"Successfully processed {len(processed_rows)} points for {len(tracks)} icebergs.")
    print(f"Output saved to {output_csv}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Calculate iceberg drift vectors")
    parser.add_argument("--input", type=str, required=True, help="Path to raw CSV (iceberg_id, lat, lon, timestamp)")
    parser.add_argument("--output", type=str, required=True, help="Path to output processed CSV")
    
    args = parser.parse_args()
    process_icebergs(args.input, args.output)
