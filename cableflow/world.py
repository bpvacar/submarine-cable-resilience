"""Question 3: rank every region in the data by min cut to the United States.

    python -m cableflow.world            # writes results/world_ranking.{csv,md}

The measure is the same as in the ten-country ranking (cables that must fail,
active cables only, sink = contiguous US). For comparison, each row also has
the min cut when the failing elements are landing stations or sites (stations
within 25 km of each other), computed with `cableflow.cuts`.
"""

import csv
from pathlib import Path

from .analysis import SINK, analyze
from .cuts import load_data, min_cut
from .graph import US_REGIONS, load_network

RESULTS = Path(__file__).resolve().parent.parent / "results"
TOP = 20

# Region names in cableflow.graph -> names in cableflow.cuts.models
CUTS_NAME = {
    "United States (Alaska)": "US-Alaska",
    "United States (Hawaii)": "US-Hawaii",
    "Puerto Rico": "US-Puerto Rico",
    "Virgin Islands (U.S.)": "US-Virgin Islands",
}


def regions(net):
    return sorted({r for lands in net.landings.values() for r in lands} - {SINK})


def rank():
    active, planned = load_network(), load_network(include_planned=True)
    cables, lp = load_data()
    rows = []
    for c in regions(active):
        try:
            r = analyze(c, SINK, net=active)
        except ValueError:
            continue  # only domestic cables
        if r.value == 0:
            continue  # no submarine route to the US at all (e.g. Caspian Sea)
        name = CUTS_NAME.get(c, c)
        rows.append({
            "country": c,
            "min_cut": r.value,
            "min_cut_with_planned": analyze(c, SINK, net=planned).value,
            "cables_landing": len(r.source_cables),
            "cut_is_unique": r.source_cut == r.sink_cut,
            "stations": min_cut(lp, cables, name, "us", "stations", 25.0, False, with_routes=False).value,
            "sites_25km": min_cut(lp, cables, name, "us", "sites", 25.0, False, with_routes=False).value,
        })
    rows.sort(key=lambda x: (-x["min_cut"], -x["min_cut_with_planned"], x["country"]))
    for row in rows:
        row["rank"] = 1 + sum(o["min_cut"] > row["min_cut"] for o in rows)
    return rows


def main():
    rows = rank()
    RESULTS.mkdir(exist_ok=True)
    cols = ["rank", "country", "min_cut", "min_cut_with_planned", "cables_landing",
            "cut_is_unique", "stations", "sites_25km"]
    with open(RESULTS / "world_ranking.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows({k: row[k] for k in cols} for row in rows)

    lines = [
        "| Rank | Country | Min cut (cables) | With planned | Cables landing | Unique cut | Stations | Sites ≤ 25 km |",
        "|---:|---|---:|---:|---:|---|---:|---:|",
    ]
    for r in rows[:TOP]:
        lines.append(
            f"| {r['rank']} | {r['country']} | {r['min_cut']} | {r['min_cut_with_planned']} "
            f"| {r['cables_landing']} | {'yes' if r['cut_is_unique'] else 'no'} "
            f"| {r['stations']} | {r['sites_25km']} |"
        )
    table = "\n".join(lines)
    (RESULTS / "world_ranking.md").write_text(table + "\n", encoding="utf-8")
    print(table)
    print(f"\n{len(rows)} regions with a submarine route to the contiguous US.")


if __name__ == "__main__":
    main()
