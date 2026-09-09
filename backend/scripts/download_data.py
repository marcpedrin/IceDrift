#!/usr/bin/env python3
"""
Download IceNavigator datasets.

Usage:
    python download_data.py --all
    python download_data.py --byu-icebergs
    python download_data.py --gebco
    python download_data.py --era5
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


DATA_DIR = Path("./data")
DATA_DIR.mkdir(parents=True, exist_ok=True)


def download_byu_icebergs():
    """Download BYU/NSIDC Antarctic iceberg tracking data."""
    import urllib.request
    print("Downloading BYU Antarctic iceberg track database...")
    # BYU Southern Ocean iceberg tracks (public)
    url = "https://www.scp.byu.edu/data/iceberg/IcebergTracks.csv"
    out = DATA_DIR / "iceberg_tracks.csv"
    try:
        urllib.request.urlretrieve(url, out)
        print(f"  ✓ Saved to {out}")
    except Exception as exc:
        print(f"  ✗ Download failed: {exc}")
        print("  Creating mock CSV for development...")
        _create_mock_byu_csv(out)


def _create_mock_byu_csv(path: Path):
    import csv
    import random
    rows = [["iceberg_id","lat","lon","area_km2","length_km","width_km","velocity_ms","heading_deg","date"]]
    icebergs = [
        ("A23A", -75.2, -25.1, 3900, 90, 40, 0.08, 15),
        ("A76A", -63.5, -55.2, 4320, 135, 26, 0.12, 30),
        ("B22A", -68.1, -10.3, 1150, 45, 18, 0.15, 45),
        ("C28B", -61.8, 5.7,   280,  20, 10, 0.22, 70),
        ("D15A", -66.5, 40.2,  650,  30, 15, 0.18, 120),
    ]
    for berg in icebergs:
        rows.append(list(berg) + ["2024-09-01"])
    with open(path, "w", newline="") as f:
        csv.writer(f).writerows(rows)
    print(f"  ✓ Mock CSV created at {path}")


def download_gebco():
    """Download GEBCO 2023 bathymetry (tile for Southern Ocean)."""
    print("GEBCO bathymetry download requires registration at https://download.gebco.net/")
    print("Manual steps:")
    print("  1. Go to https://download.gebco.net/")
    print("  2. Select region: lat -90 to -55, lon -180 to 180")
    print("  3. Download netCDF format")
    print(f"  4. Save as {DATA_DIR / 'gebco.nc'}")


def download_era5():
    """Download ERA5 wind data via CDS API."""
    api_key = os.getenv("CDSAPI_KEY", "")
    if not api_key:
        print("Set CDSAPI_KEY in .env to download ERA5 data")
        print("Register at https://cds.climate.copernicus.eu/")
        return

    try:
        import cdsapi
        c = cdsapi.Client()
        out = DATA_DIR / "era5_winds.nc"
        print(f"Downloading ERA5 winds → {out}")
        c.retrieve(
            "reanalysis-era5-pressure-levels",
            {
                "product_type": "reanalysis",
                "variable": ["u_component_of_wind", "v_component_of_wind"],
                "pressure_level": "1000",
                "year": "2024",
                "month": "09",
                "day": [f"{d:02d}" for d in range(1, 8)],
                "time": "00:00",
                "area": [-55, -180, -90, 180],
                "format": "netcdf",
            },
            str(out),
        )
        print(f"  ✓ ERA5 winds saved to {out}")
    except Exception as exc:
        print(f"  ✗ ERA5 download failed: {exc}")


def main():
    parser = argparse.ArgumentParser(description="IceNavigator data downloader")
    parser.add_argument("--all", action="store_true", help="Download all datasets")
    parser.add_argument("--byu-icebergs", action="store_true")
    parser.add_argument("--gebco", action="store_true")
    parser.add_argument("--era5", action="store_true")
    args = parser.parse_args()

    if args.all or args.byu_icebergs:
        download_byu_icebergs()
    if args.all or args.gebco:
        download_gebco()
    if args.all or args.era5:
        download_era5()

    if not any([args.all, args.byu_icebergs, args.gebco, args.era5]):
        parser.print_help()


if __name__ == "__main__":
    main()
