"""Minimum number of submarine cables whose failure cuts every route from a
source region to a sink region.

    python -m cableflow Ecuador
    python -m cableflow Chile --sink "United States" --include-planned
"""

import argparse

from .graph import build_flow_graph, load_network, region
from .maxflow import decompose_paths, max_flow, sink_side_cut, source_side_cut


def cut_cables(cut, names):
    # Only ("in", c) -> ("out", c) arcs can be in a minimum cut; INF arcs never are.
    return sorted(names[u[1]] for u, v in cut if u[0] == "in" and v == ("out", u[1]))


def describe_path(path, names):
    parts = []
    for node in path:
        kind, key = node
        if kind == "region":
            parts.append(key)
        elif kind == "in":
            parts.append(f"[{names[key]}]")
    return " -> ".join(parts)


def analyze(source, sink="United States", include_planned=False):
    net = load_network(include_planned=include_planned)
    cap = build_flow_graph(net)
    s, t = region(source), region(sink)
    for node, label in ((s, source), (t, sink)):
        if node not in cap:
            raise SystemExit(f"No cable lands in region {label!r}.")
    value, flow, residual = max_flow(cap, s, t)
    return {
        "value": value,
        "source_cut": cut_cables(source_side_cut(cap, residual, s), net.names),
        "sink_cut": cut_cables(sink_side_cut(cap, residual, t), net.names),
        "routes": [describe_path(p, net.names) for _, p in decompose_paths(flow, s, t)],
        "source_cables": sorted(
            net.names[c] for c, regs in net.landings.items() if source in regs and len(regs) > 1
        ),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("source")
    ap.add_argument("--sink", default="United States")
    ap.add_argument("--include-planned", action="store_true")
    args = ap.parse_args()

    r = analyze(args.source, args.sink, args.include_planned)
    print(f"{args.source} -> {args.sink}")
    print(f"Cables landing in {args.source}: {len(r['source_cables'])}")
    for name in r["source_cables"]:
        print(f"  {name}")
    print(f"\nMax flow = min cut = {r['value']}")
    print("\nCable-disjoint routes (one flow decomposition):")
    for i, route in enumerate(r["routes"], 1):
        print(f"  {i}. {route}")
    print("\nMinimum cut closest to the source:")
    for name in r["source_cut"]:
        print(f"  {name}")
    if r["sink_cut"] != r["source_cut"]:
        print("\nMinimum cut closest to the sink (the cut is not unique):")
        for name in r["sink_cut"]:
            print(f"  {name}")


if __name__ == "__main__":
    main()
