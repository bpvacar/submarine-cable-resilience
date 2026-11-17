"""Mapa esquemático del corte mínimo (lon/lat, sin mapa base).

    python scripts/plot_cut_map.py Ecuador --mode stations
    python scripts/plot_cut_map.py Israel --mode sites --cluster-km 25

Gris: todas las estaciones del snapshot. Color: estaciones/cables del corte.
Las líneas de cada cable unen el aterrizaje en el país con los demás aterrizajes
(el CSV no trae el orden de la ruta, así que el trazo es esquemático).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cableflow.cuts import load_data, min_cut  # noqa: E402

CUT = "#eb6834"
OTHER = "#2a78d6"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("country")
    ap.add_argument("--mode", default="stations", choices=["cables", "stations", "sites"])
    ap.add_argument("--sink", default="us")
    ap.add_argument("--cluster-km", type=float, default=25)
    ap.add_argument("--include-planned", action="store_true")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()

    cables, lp = load_data(include_planned=a.include_planned)
    r = min_cut(lp, cables, a.country, a.sink, a.mode, a.cluster_km, a.include_planned,
                with_routes=False)
    cut_cables = sorted({c for d in r.details.values() for c in d["cables"]})
    cut_stations = sorted({s for d in r.details.values() for s in d["stations"]}) if a.mode != "cables" else []

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, (ax, axz) = plt.subplots(1, 2, figsize=(12, 4.8), dpi=150,
                                  gridspec_kw={"width_ratios": [2.2, 1]})
    fig.patch.set_facecolor("#fcfcfb")
    own = lp[lp.region == a.country]
    for axis in (ax, axz):
        axis.set_facecolor("#fcfcfb")
        allp = lp.drop_duplicates("landing_point_id")
        axis.scatter(allp.longitude, allp.latitude, s=3, color="#c3c2b7", lw=0, zorder=1)
        for name in cut_cables:
            g = lp[lp.cable_name == name]
            home = g[g.region == a.country]
            if home.empty:
                continue
            h = home.iloc[0]
            for _, p in g[g.region != a.country].iterrows():
                axis.plot([h.longitude, p.longitude], [h.latitude, p.latitude],
                          color=OTHER, lw=0.8, alpha=0.5, zorder=2)
        hit = own[own.landing_point_name.isin(cut_stations)] if cut_stations else own
        axis.scatter(hit.longitude, hit.latitude, s=60, color=CUT, edgecolor="#fcfcfb",
                     lw=2, zorder=4)
        for s in axis.spines.values():
            s.set_visible(False)
        axis.tick_params(colors="#52514e", labelsize=8)
    # zoom al país
    pad = 1.0
    axz.set_xlim(own.longitude.min() - pad, own.longitude.max() + pad)
    axz.set_ylim(own.latitude.min() - pad, own.latitude.max() + pad)
    for _, p in own.drop_duplicates("landing_point_id").iterrows():
        axz.annotate(p.landing_point_name.split(",")[0], (p.longitude, p.latitude),
                     xytext=(6, 4), textcoords="offset points", fontsize=8, color="#0b0b0b")
    unit = {"cables": "cables", "stations": "estaciones", "sites": f"sitios (≤{a.cluster_km:g} km)"}[a.mode]
    ax.set_title(f"{a.country} → {a.sink}: corte mínimo = {r.value} {unit}", loc="left",
                 fontsize=11, color="#0b0b0b")
    axz.set_title("Detalle del país (naranja = en el corte)", loc="left", fontsize=9, color="#52514e")
    fig.text(0.01, 0.01, "Azul: cables que pasan por el corte (trazo esquemático). "
             "Datos: TeleGeography, CC BY-SA 4.0", fontsize=7, color="#52514e")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    out = Path(a.out); out.mkdir(exist_ok=True)
    path = out / f"map_{a.country}_{a.mode}{'_planned' if a.include_planned else ''}.png"
    fig.savefig(path)
    print(path)


if __name__ == "__main__":
    main()
