"""Rank countries by min cut to the United States (most resilient first).

    python -m cableflow.ranking            # writes results/ranking.{csv,md}

Primary key: min cut with active cables. Countries with the same min cut share
a rank (competition ranking: 1, 2, 3, 3, 5). Within a tie, rows are listed by
the min cut with planned cables included, which is shown but does not change
the rank.
"""

import csv
from pathlib import Path

from .analysis import COUNTRIES, SINK, analyze
from .graph import load_network

RESULTS = Path(__file__).resolve().parent.parent / "results"


def short_name(name: str) -> str:
    """'South America-1 (SAm-1)' -> 'SAm-1'; 'SPCS ... (SPCS)/Mistral' -> 'SPCS/Mistral'."""
    if "(" in name and ")" in name:
        inside = name[name.index("(") + 1 : name.index(")")]
        return inside + name[name.index(")") + 1 :]
    return name


def rank(countries=COUNTRIES, sink=SINK):
    active, planned = load_network(), load_network(include_planned=True)
    rows = []
    for c in countries:
        r = analyze(c, sink, net=active)
        rp = analyze(c, sink, net=planned)
        rows.append({
            "country": c,
            "min_cut": r.value,
            "min_cut_with_planned": rp.value,
            "cables_landing": len(r.source_cables),
            "cut_is_unique": r.source_cut == r.sink_cut,
            "cut_cables": "; ".join(sorted(short_name(r.name(x)) for x in r.source_cut)),
        })
    rows.sort(key=lambda x: (-x["min_cut"], -x["min_cut_with_planned"], x["country"]))
    for row in rows:
        row["rank"] = 1 + sum(o["min_cut"] > row["min_cut"] for o in rows)
    return rows


def main():
    rows = rank()
    RESULTS.mkdir(exist_ok=True)
    cols = ["rank", "country", "min_cut", "min_cut_with_planned",
            "cables_landing", "cut_is_unique", "cut_cables"]
    with open(RESULTS / "ranking.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    lines = [
        f"| Rank | Country | Min cut | With planned | Cables landing | Minimum cut (closest to source) |",
        "|---:|---|---:|---:|---:|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['rank']} | {r['country']} | {r['min_cut']} | {r['min_cut_with_planned']} "
            f"| {r['cables_landing']} | {r['cut_cables']} |"
        )
    table = "\n".join(lines)
    (RESULTS / "ranking.md").write_text(table + "\n", encoding="utf-8")
    print(table)
    if not all(r["cut_is_unique"] for r in rows):
        print("\nNote: some minimum cuts are not unique; see python -m cableflow <country>.")


if __name__ == "__main__":
    main()
