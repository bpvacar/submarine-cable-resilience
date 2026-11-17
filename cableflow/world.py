"""Question 3: the most resilient country in the world, under two sinks.

    python -m cableflow.world

* ``world``: min cut between a country and **every other country** (one
  super-sink joined to all other countries with capacity INF). Countries are
  TeleGeography's, so Alaska, Hawaii and Puerto Rico are part of the US.
  Writes results/world_ranking_all.{csv,md}.
* ``us``: min cut to the contiguous US, the measure of questions 1 and 2, for
  every region. Writes results/world_ranking_us.{csv,md}.

Each row also has the min cut when the failing elements are landing stations
or sites (stations within 25 km of each other), computed with
`cableflow.cuts`.
"""

import csv
from pathlib import Path

from .analysis import SINK, analyze
from .cuts import load_data, min_cut
from .graph import INF, build_flow_graph, load_network, region
from .maxflow import max_flow, source_side_cut

RESULTS = Path(__file__).resolve().parent.parent / "results"
TOP = 20
SUPER_SINK = ("sink",)

# Region names in cableflow.graph -> names in cableflow.cuts.models
CUTS_NAME = {
    "United States (Alaska)": "US-Alaska",
    "United States (Hawaii)": "US-Hawaii",
    "Puerto Rico": "US-Puerto Rico",
    "Virgin Islands (U.S.)": "US-Virgin Islands",
}


def regions(net):
    return sorted({r for lands in net.landings.values() for r in lands})


def cut_to_world(net, country):
    """Min cut between `country` and all other countries, and whether it is
    exactly the set of international cables that land in `country`."""
    cap = build_flow_graph(net)
    for r in regions(net):
        if r != country and region(r) in cap:
            cap[region(r)][SUPER_SINK] = INF
    value, _, residual = max_flow(cap, region(country), SUPER_SINK)
    own = {c for c, lands in net.landings.items() if country in lands and len(lands) > 1}
    cut = {u[1] for u, v in source_side_cut(cap, residual, region(country)) if u[0] == "in"}
    return value, len(own), cut == own


def rank_world():
    active, planned = load_network(split_us=False), load_network(include_planned=True, split_us=False)
    cables, lp = load_data()
    lp["region"] = lp["country"]  # same countries as `active`: US not split
    rows = []
    for c in regions(active):
        value, international, cut_is_own = cut_to_world(active, c)
        if value == 0:
            continue  # only domestic cables
        rows.append({
            "country": c,
            "min_cut": value,
            "min_cut_with_planned": cut_to_world(planned, c)[0],
            "international_cables": international,
            "cut_is_own_cables": cut_is_own,
            "stations": min_cut(lp, cables, c, "world", "stations", 25.0, False, with_routes=False).value,
            "sites_25km": min_cut(lp, cables, c, "world", "sites", 25.0, False, with_routes=False).value,
        })
    return finish(rows)


def rank_us():
    active, planned = load_network(), load_network(include_planned=True)
    cables, lp = load_data()
    rows = []
    for c in regions(active):
        if c == SINK:
            continue
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
    return finish(rows)


def finish(rows):
    rows.sort(key=lambda x: (-x["min_cut"], -x["min_cut_with_planned"], x["country"]))
    for row in rows:
        row["rank"] = 1 + sum(o["min_cut"] > row["min_cut"] for o in rows)
    return [{"rank": r.pop("rank"), **r} for r in rows]


def write(rows, stem):
    RESULTS.mkdir(exist_ok=True)
    cols = list(rows[0])
    with open(RESULTS / f"{stem}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    fmt = lambda v: "yes" if v is True else "no" if v is False else str(v)
    lines = ["| " + " | ".join(cols) + " |",
             "|" + "|".join("---" if c == "country" else "---:" for c in cols) + "|"]
    lines += ["| " + " | ".join(fmt(r[c]) for c in cols) + " |" for r in rows[:TOP]]
    table = "\n".join(lines)
    (RESULTS / f"{stem}.md").write_text(table + "\n", encoding="utf-8")
    return table


def main():
    for title, rows, stem in (("To every other country", rank_world(), "world_ranking_all"),
                              ("To the contiguous US", rank_us(), "world_ranking_us")):
        print(f"## {title} ({len(rows)} countries)\n")
        print(write(rows, stem), "\n")


if __name__ == "__main__":
    main()
