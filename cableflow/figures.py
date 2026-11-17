"""Draw each country's flow hypergraph with Graphviz.

    python -m cableflow.figures              # all ten countries
    python -m cableflow.figures Ecuador      # just one
    python -m cableflow.figures --world "United States"   # against every other country

Writes figures/<country>.{dot,svg,png,pdf}. Requires the Graphviz `dot`
binary (brew install graphviz / apt install graphviz).

A cable is a hyperedge: it joins every country it lands in. It is drawn as its
incidence (star) graph: one box per cable, linked to each drawn country it
touches. Countries shown are the source, the sink and every country on a
cable-disjoint route. Cables shown are those landing in the source, those on a
route and those in the minimum cut. "+k" counts landings in countries that are
not drawn.
"""

import subprocess
import sys
from pathlib import Path

from .analysis import COUNTRIES, SINK, analyze
from .graph import INF, build_flow_graph, load_network, region
from .maxflow import decompose_paths, max_flow
from .ranking import short_name
from .world import SUPER_SINK

FIGURES = Path(__file__).resolve().parent.parent / "figures"

# Palette (works on white backgrounds)
COUNTRY_FILL, ENDPOINT_FILL = "#E6F1FB", "#CECBF6"
CABLE_FILL, CUT_FILL, CUT_LINE = "#F1EFE8", "#FCEBEB", "#A32D2D"
FLOW, OTHER = "#0F6E56", "#B4B2A9"


def q(s):
    return '"' + s.replace('"', '\\"') + '"'


def to_dot(r):
    cut = set(r.source_cut)
    countries = {r.source, r.sink}
    route_cables = set()
    flow_edges = set()  # (country, cable_id, "in"|"out") incidences that carry flow
    for path in r.paths:
        for a, b in zip(path, path[1:]):
            if a[0] == "region" and b[0] == "in":
                flow_edges.add((a[1], b[1], "in"))
            if a[0] == "out" and b[0] == "region":
                flow_edges.add((b[1], a[1], "out"))
        for kind, key in path:
            if kind == "region":
                countries.add(key)
            elif kind == "in":
                route_cables.add(key)
    cables = route_cables | cut | set(r.source_cables)

    out = [
        "graph G {",
        '  rankdir=LR; newrank=true; splines=true; nodesep=0.18; ranksep=0.9;',
        '  fontname="Helvetica"; labelloc=t; fontsize=18;',
        f'  label={q(f"{r.source} → {r.sink}: minimum cut = {r.value} cables")};',
        '  node [fontname="Helvetica", fontsize=12, penwidth=0.8];',
        '  edge [penwidth=0.8];',
    ]
    for c in sorted(countries):
        fill = ENDPOINT_FILL if c in (r.source, r.sink) else COUNTRY_FILL
        out.append(f'  {q("R:" + c)} [label={q(c)}, shape=box, style="rounded,filled,bold", '
                   f'fillcolor="{fill}", fontsize=14];')
    out.append(f'  {{ rank=min; {q("R:" + r.source)}; }}')
    out.append(f'  {{ rank=max; {q("R:" + r.sink)}; }}')

    for cid in sorted(cables):
        lands = r.net.landings[cid]
        hidden = len(lands - countries)
        label = short_name(r.name(cid)) + (f"\n+{hidden}" if hidden else "")
        if cid in cut:
            style = f'style="filled,bold", fillcolor="{CUT_FILL}", color="{CUT_LINE}", penwidth=1.6'
        else:
            style = f'style=filled, fillcolor="{CABLE_FILL}"'
        out.append(f'  {q("C:" + cid)} [label={q(label)}, shape=box, fontsize=10, '
                   f'margin="0.08,0.03", {style}];')

    for cid in sorted(cables):
        for c in sorted(r.net.landings[cid] & countries):
            C, R = q("C:" + cid), q("R:" + c)
            if (c, cid, "in") in flow_edges:
                out.append(f'  {R} -- {C} [color="{FLOW}", penwidth=2.4];')
            elif (c, cid, "out") in flow_edges:
                out.append(f'  {C} -- {R} [color="{FLOW}", penwidth=2.4];')
            elif c == r.source and cid not in route_cables:
                # Dead-end cable of the source: keep it next to the source.
                out.append(f'  {R} -- {C} [color="{OTHER}", style=dashed];')
            else:
                out.append(f'  {C} -- {R} [color="{OTHER}", style=dashed, constraint=false];')

    out.append(
        '  legend [shape=plaintext, fontsize=10, label=<'
        '<TABLE BORDER="0" CELLSPACING="2">'
        f'<TR><TD ALIGN="LEFT"><FONT COLOR="{FLOW}"><B>━━</B></FONT> route that carries one unit of flow</TD></TR>'
        f'<TR><TD ALIGN="LEFT"><FONT COLOR="{OTHER}">╍╍</FONT> other landing of the cable</TD></TR>'
        f'<TR><TD ALIGN="LEFT"><FONT COLOR="{CUT_LINE}"><B>▭</B></FONT> cable in the minimum cut</TD></TR>'
        '<TR><TD ALIGN="LEFT">+k  landings in countries not drawn</TD></TR>'
        '</TABLE>>];'
    )
    out.append(f'  {{ rank=max; legend; }}')
    out.append("}")
    return "\n".join(out)


def world_to_dot(country, net):
    """Hypergraph of `country` against every other country (question 3).

    Every international cable of `country` is in the minimum cut and carries
    one unit of flow to the first other country it reaches. Only those
    countries are drawn; "+k" counts the cable's other landings."""
    cap = build_flow_graph(net)
    for r in {r for lands in net.landings.values() for r in lands} - {country}:
        if region(r) in cap:
            cap[region(r)][SUPER_SINK] = INF
    value, flow, _ = max_flow(cap, region(country), SUPER_SINK)
    dest = {}  # cable id -> country its unit of flow goes to
    for _, path in decompose_paths(flow, region(country), SUPER_SINK):
        dest[path[1][1]] = path[3][1]  # region -> in -> out -> region -> sink
    countries = sorted(set(dest.values()))

    out = [
        "graph G {",
        '  rankdir=LR; newrank=true; splines=true; nodesep=0.08; ranksep=1.6;',
        '  fontname="Helvetica"; labelloc=t; fontsize=20;',
        f'  label={q(f"{country} → every other country: minimum cut = {value} cables")};',
        '  node [fontname="Helvetica", fontsize=12, penwidth=0.8];',
        f'  {q("R:" + country)} [label={q(country)}, shape=box, style="rounded,filled,bold", '
        f'fillcolor="{ENDPOINT_FILL}", fontsize=16];',
        f'  world [label="Rest of the world\\n(super-sink)", shape=box, style="rounded,filled,bold", '
        f'fillcolor="{ENDPOINT_FILL}", fontsize=16];',
        f'  {{ rank=min; {q("R:" + country)}; }}',
        '  { rank=max; world; }',
    ]
    for c in countries:
        out.append(f'  {q("R:" + c)} [label={q(c)}, shape=box, style="rounded,filled", '
                   f'fillcolor="{COUNTRY_FILL}", fontsize=11];')
        out.append(f'  {q("R:" + c)} -- world [color="{OTHER}", penwidth=0.6];')
    # Group cables by destination so the green lines do not cross.
    for cid in sorted(dest, key=lambda c: (dest[c], short_name(net.names[c]))):
        hidden = len(net.landings[cid]) - 2
        label = short_name(net.names[cid]) + (f"  +{hidden}" if hidden else "")
        C = q("C:" + cid)
        out.append(f'  {C} [label={q(label)}, shape=box, fontsize=9, margin="0.06,0.02", '
                   f'style="filled,bold", fillcolor="{CUT_FILL}", color="{CUT_LINE}", penwidth=1.2];')
        out.append(f'  {q("R:" + country)} -- {C} [color="{FLOW}", penwidth=1.4];')
        out.append(f'  {C} -- {q("R:" + dest[cid])} [color="{FLOW}", penwidth=1.4];')
    out.append(
        '  legend [shape=plaintext, fontsize=11, label=<'
        '<TABLE BORDER="0" CELLSPACING="2">'
        f'<TR><TD ALIGN="LEFT"><FONT COLOR="{FLOW}"><B>━━</B></FONT> route that carries one unit of flow</TD></TR>'
        f'<TR><TD ALIGN="LEFT"><FONT COLOR="{CUT_LINE}"><B>▭</B></FONT> cable in the minimum cut (all of them)</TD></TR>'
        '<TR><TD ALIGN="LEFT">+k  other landings of the cable, not drawn</TD></TR>'
        f'<TR><TD ALIGN="LEFT"><FONT COLOR="{OTHER}">━━</FONT> capacity ∞ to the super-sink</TD></TR>'
        '</TABLE>>];'
    )
    out.append('  { rank=max; legend; }')
    out.append("}")
    return "\n".join(out)


def write(stem, dot):
    stem.parent.mkdir(exist_ok=True)
    dot_path = stem.with_suffix(".dot")
    dot_path.write_text(dot, encoding="utf-8")
    for fmt, extra in (("svg", []), ("pdf", []), ("png", ["-Gdpi=150"])):
        subprocess.run(["dot", f"-T{fmt}", *extra, str(dot_path), "-o", str(stem.with_suffix("." + fmt))],
                       check=True)
    return stem


def render_world(country, out_dir=FIGURES):
    net = load_network(split_us=False)
    return write(out_dir / (country.lower().replace(" ", "_") + "_world"), world_to_dot(country, net))


def render(country, net, out_dir=FIGURES):
    r = analyze(country, SINK, net=net)
    return write(out_dir / country.lower().replace(" ", "_"), to_dot(r))


def main():
    args = sys.argv[1:]
    if args[:1] == ["--world"]:
        for country in args[1:] or ["United States"]:
            print(render_world(country).with_suffix(".png"))
        return
    net = load_network()
    for country in args or COUNTRIES:
        print(render(country, net).with_suffix(".png"))


if __name__ == "__main__":
    main()
