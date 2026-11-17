"""Sensibilidad del corte por sitios al radio de agrupación.

    python scripts/sweep_cluster_radius.py Ecuador Israel --max-km 150 --step 5

Escribe results/sweep_radius.csv y results/sweep_radius.png.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cableflow.cuts import load_data, min_cut  # noqa: E402

COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]  # orden categorical fijo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("countries", nargs="*", default=["Ecuador", "Israel"])
    ap.add_argument("--sink", default="us")
    ap.add_argument("--max-km", type=float, default=150)
    ap.add_argument("--step", type=float, default=5)
    ap.add_argument("--include-planned", action="store_true")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()

    cables, lp = load_data(include_planned=a.include_planned)
    radii = [i * a.step for i in range(int(a.max_km // a.step) + 1)]
    rows = [{"country": c, "km": km,
             "cut": min_cut(lp, cables, c, a.sink, "sites", km, with_routes=False).value}
            for c in a.countries for km in radii]
    df = pd.DataFrame(rows)
    out = Path(a.out); out.mkdir(exist_ok=True)
    suffix = "_planned" if a.include_planned else ""
    df.to_csv(out / f"sweep_radius{suffix}.csv", index=False)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 3.8), dpi=150)
    fig.patch.set_facecolor("#fcfcfb"); ax.set_facecolor("#fcfcfb")
    for i, c in enumerate(a.countries):
        d = df[df.country == c]
        # pequeño desfase vertical para que las líneas iguales no se tapen
        off = (i - (len(a.countries) - 1) / 2) * 0.04
        ax.step(d.km, d.cut + off, where="post", color=COLORS[i % 4], lw=2, label=c)
    ax.set_xlabel("Radio de agrupación de estaciones (km)", color="#52514e")
    ax.set_ylabel("Sitios a inutilizar", color="#52514e")
    ax.set_title(f"Corte mínimo por sitios vs. radio (sumidero: {a.sink})", loc="left",
                 color="#0b0b0b", fontsize=11)
    ax.yaxis.get_major_locator().set_params(integer=True)
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", color="#e6e5e0", lw=0.8); ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#c3c2b7")
    ax.tick_params(colors="#52514e")
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(out / f"sweep_radius{suffix}.png")
    print(df.pivot(index="km", columns="country", values="cut").to_string())


if __name__ == "__main__":
    main()
