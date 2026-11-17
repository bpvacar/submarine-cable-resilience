#!/usr/bin/env python3
"""Download TeleGeography's submarine cable database and flatten it to CSV.

Outputs (in --out-dir):
  cables.csv                  one row per cable
  cable_landing_points.csv    one row per (cable, landing point), with coordinates

Data: TeleGeography Submarine Cable Map (https://www.submarinecablemap.com),
CC BY-SA 4.0 (as cited by the course assignment). Attribute TeleGeography.
"""

import argparse
import csv
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

API = "https://www.submarinecablemap.com/api/v3"
UA = "submarine-cable-csv/1.0"


def get_json(path, retries=3):
    req = urllib.request.Request(f"{API}/{path}", headers={"User-Agent": UA})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)


def parse_length_km(s):
    """'45,000 km' -> 45000.0; anything else -> None."""
    if not s:
        return None
    try:
        return float(s.lower().replace("km", "").replace(",", "").strip())
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", type=Path, default=Path(__file__).resolve().parent.parent / "data")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    index = get_json("cable/all.json")
    print(f"{len(index)} cables in index; fetching details...")

    with ThreadPoolExecutor(args.workers) as pool:
        cables = list(pool.map(lambda c: get_json(f"cable/{c['id']}.json"), index))

    # Landing point coordinates (GeoJSON Point: [lon, lat])
    lp_geo = get_json("landing-point/landing-point-geo.json")
    coords = {
        f["properties"]["id"]: f["geometry"]["coordinates"]
        for f in lp_geo["features"]
        if f.get("geometry")
    }

    cable_cols = [
        "id", "name", "length_km", "length_raw", "rfs", "rfs_year", "is_planned",
        "owners", "suppliers", "n_landing_points", "n_countries", "countries",
        "url", "notes",
    ]
    lp_cols = [
        "cable_id", "cable_name", "landing_point_id", "landing_point_name",
        "country", "latitude", "longitude", "is_tbd",
    ]

    lp_rows = []
    with open(args.out_dir / "cables.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cable_cols)
        w.writeheader()
        for c in sorted(cables, key=lambda c: c["name"].lower()):
            lps = c.get("landing_points") or []
            countries = sorted({lp["country"] for lp in lps if lp.get("country")})
            w.writerow({
                "id": c["id"],
                "name": c["name"],
                "length_km": parse_length_km(c.get("length")),
                "length_raw": c.get("length"),
                "rfs": c.get("rfs"),
                "rfs_year": c.get("rfs_year"),
                "is_planned": c.get("is_planned"),
                "owners": c.get("owners"),
                "suppliers": c.get("suppliers"),
                "n_landing_points": len(lps),
                "n_countries": len(countries),
                "countries": "; ".join(countries),
                "url": c.get("url"),
                "notes": c.get("notes"),
            })
            for lp in lps:
                lon, lat = coords.get(lp["id"], (None, None))
                lp_rows.append({
                    "cable_id": c["id"],
                    "cable_name": c["name"],
                    "landing_point_id": lp["id"],
                    "landing_point_name": lp["name"],
                    "country": lp.get("country"),
                    "latitude": lat,
                    "longitude": lon,
                    "is_tbd": lp.get("is_tbd"),
                })

    with open(args.out_dir / "cable_landing_points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=lp_cols)
        w.writeheader()
        w.writerows(lp_rows)

    print(f"Wrote {len(cables)} cables and {len(lp_rows)} cable-landing rows "
          f"to {args.out_dir} ({date.today()}).")


if __name__ == "__main__":
    main()
