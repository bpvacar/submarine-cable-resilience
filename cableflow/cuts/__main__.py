import argparse
import json

from .analysis import external_bottleneck, min_cut
from .models import MODES, load_data


def format_result(r):
    extra = f", sitios a ≤{r.cluster_km:g} km" if r.mode == "sites" else ""
    head = (f"{r.source} → {r.sink} | modo={r.mode}{extra} | "
            f"{'con planificados' if r.include_planned else 'solo activos'}")
    if r.value is None:
        return f"{head}\n  {r.note}"
    lines = [head, f"  corte mínimo = {r.value} ({'único' if r.unique else 'NO único'})"]
    for eid in r.cut:
        d = r.details[eid]
        if r.mode in ("cables", "external"):
            countries = d["countries"] if len(d["countries"]) <= 8 else d["countries"][:8] + ["…"]
            lines.append(f"   - {d['cables'][0]}  ({', '.join(countries)})")
        else:
            lines.append(f"   - {', '.join(d['stations'])}  ⇒ cables: {', '.join(d['cables'])}")
    if r.routes:
        lines.append("  rutas disjuntas (Menger):")
        lines += [f"   {i}. {p}" for i, p in enumerate(r.routes, 1)]
    if r.note:
        lines.append(f"  nota: {r.note}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m cableflow.cuts")
    ap.add_argument("country")
    ap.add_argument("--mode", choices=MODES + ("all",), default="cables")
    ap.add_argument("--sink", default="us", help='"us", "world" o "country:<País>"')
    ap.add_argument("--cluster-km", type=float, default=25.0)
    ap.add_argument("--include-planned", action="store_true")
    ap.add_argument("--external", action="store_true",
                    help="buscar cuello de botella fuera del país (cables propios protegidos)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--cables", default="data/cables.csv")
    ap.add_argument("--landing-points", default="data/cable_landing_points.csv")
    a = ap.parse_args(argv)

    cables, lp = load_data(a.cables, a.landing_points, a.include_planned)
    modes = MODES if a.mode == "all" else (a.mode,)
    results = [min_cut(lp, cables, a.country, a.sink, m, a.cluster_km, a.include_planned)
               for m in modes]
    if a.external:
        results.append(external_bottleneck(lp, cables, a.country, a.sink, a.include_planned))
    if a.json:
        print(json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2))
    else:
        print("\n\n".join(format_result(r) for r in results))


if __name__ == "__main__":
    main()
