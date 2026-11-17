"""Tabla comparativa de cortes mínimos para varios países (o todos).

    python scripts/compare_countries.py Ecuador Israel
    python scripts/compare_countries.py --all --sink us --top 25

Escribe results/summary_<...>.csv y .md.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cableflow.cuts import external_bottleneck, load_data, min_cut  # noqa: E402
from cableflow.cuts.models import US_CONTIGUOUS  # noqa: E402


def row_for(country, lp, cables, sink, km, planned):
    row = {"country": country, "planned": planned}
    for mode in ("cables", "stations", "sites"):
        r = min_cut(lp, cables, country, sink, mode, km, planned, with_routes=False)
        row[mode] = r.value
        row[f"{mode}_unique"] = r.unique
        if mode == "stations":
            row["stations_cut"] = "; ".join(r.details[e]["stations"][0] for e in r.cut)
    ext = external_bottleneck(lp, cables, country, sink, planned)
    row["external"] = ext.value  # None = sin corte externo finito
    row["gap_cables_minus_sites"] = row["cables"] - row["sites"]
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("countries", nargs="*", default=["Ecuador", "Israel"])
    ap.add_argument("--all", action="store_true", help="todos los países con cables")
    ap.add_argument("--sink", default="us")
    ap.add_argument("--cluster-km", type=float, default=25.0)
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--out", default="results")
    a = ap.parse_args()

    rows = []
    for planned in (False, True):
        cables, lp = load_data(include_planned=planned)
        countries = a.countries
        if a.all:
            countries = sorted(set(lp.region) - {US_CONTIGUOUS} - (
                {a.sink.split(":", 1)[1]} if a.sink.startswith("country:") else set()))
        for c in countries:
            try:
                rows.append(row_for(c, lp, cables, a.sink, a.cluster_km, planned))
            except ValueError as e:
                print(f"[skip] {c}: {e}", file=sys.stderr)
    df = pd.DataFrame(rows)
    tag = "all" if a.all else "_".join(a.countries)
    out = Path(a.out); out.mkdir(exist_ok=True)
    df.to_csv(out / f"summary_{tag}_{a.sink.replace(':', '-')}.csv", index=False)

    view = df[["country", "planned", "cables", "stations", "sites", "external", "stations_cut"]]
    if a.all:  # ranking: países donde agrupar por sitio reduce más el corte
        base = df[~df.planned & (df.cables > 0)]  # 0 = sin ruta submarina al sumidero (p. ej. mar Caspio)
        view = (base.sort_values(["sites", "gap_cables_minus_sites"], ascending=[True, False])
                [["country", "cables", "stations", "sites", "gap_cables_minus_sites"]].head(a.top))
    md = view.to_markdown(index=False)
    (out / f"summary_{tag}_{a.sink.replace(':', '-')}.md").write_text(md + "\n", encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
