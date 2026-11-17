"""Build the region/cable flow network from the TeleGeography CSVs.

Model
-----
* One node per **region**. All landing points of a country are merged into one
  node: we assume each country has a domestic terrestrial backbone, so moving
  between two of its landing points never fails.
* The United States is the exception. Alaska, Hawaii, Puerto Rico and the
  U.S. Virgin Islands are not connected to the mainland by land, so each one is
  its own region and "United States" means the contiguous states.
* Each cable ``c`` becomes two nodes, ``("in", c) -> ("out", c)``, joined by an
  arc of capacity 1. That arc *is* the cable: cutting it means "cable c failed",
  and it costs 1 no matter how many regions the cable touches.
* For every region ``r`` the cable lands in: ``r -> ("in", c)`` and
  ``("out", c) -> r``, both with capacity INF. They only record where the cable
  lands, so a minimum cut never uses them. Having one arc in and one arc out
  per region makes the cable bidirectional.
* Countries are **not** joined to each other by land: the question asks for
  submarine routes only.
"""

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Larger than any possible cut (there are < 1000 cables), so it never gets cut.
INF = 10**9

US_REGIONS = {
    "AK": "United States (Alaska)",
    "HI": "United States (Hawaii)",
    "PR": "Puerto Rico",
    "VI": "Virgin Islands (U.S.)",
}


def region_of(country: str, landing_point_name: str) -> str:
    """Region node a landing point belongs to (see module docstring)."""
    if country == "United States":
        # Names look like "Miami, FL, United States".
        parts = [p.strip() for p in landing_point_name.split(",")]
        if len(parts) >= 3 and parts[-2] in US_REGIONS:
            return US_REGIONS[parts[-2]]
    return country


@dataclass
class CableNetwork:
    names: dict[str, str]  # cable id -> cable name
    landings: dict[str, set[str]]  # cable id -> regions it lands in


def load_network(data_dir: Path = DATA_DIR, include_planned: bool = False) -> CableNetwork:
    names = {}
    with open(data_dir / "cables.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if include_planned or row["is_planned"] != "True":
                names[row["id"]] = row["name"]

    landings = defaultdict(set)
    with open(data_dir / "cable_landing_points.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["cable_id"] in names:
                landings[row["cable_id"]].add(
                    region_of(row["country"], row["landing_point_name"])
                )
    return CableNetwork(names, dict(landings))


def region(name: str):
    return ("region", name)


def build_flow_graph(net: CableNetwork) -> dict:
    """Capacity map ``cap[u][v]``. Nodes are ``("region", name)``,
    ``("in", cable_id)`` and ``("out", cable_id)``."""
    cap = defaultdict(dict)
    for cable_id, regions in net.landings.items():
        if len(regions) < 2:
            continue  # stays inside one region: cannot carry traffic between regions
        c_in, c_out = ("in", cable_id), ("out", cable_id)
        cap[c_in][c_out] = 1
        for r in regions:
            cap[region(r)][c_in] = INF
            cap[c_out][region(r)] = INF
    return dict(cap)
