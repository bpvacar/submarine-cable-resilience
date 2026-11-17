"""Minimum number of submarine cables whose failure cuts every route from a
source region to a sink region.

    python -m cableflow Ecuador
    python -m cableflow Chile --sink "United States" --include-planned
"""

import argparse

from .analysis import SINK, analyze


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("source")
    ap.add_argument("--sink", default=SINK)
    ap.add_argument("--include-planned", action="store_true")
    args = ap.parse_args()

    try:
        r = analyze(args.source, args.sink, args.include_planned)
    except ValueError as e:
        raise SystemExit(str(e))
    names = lambda ids: sorted(r.name(c) for c in ids)

    print(f"{r.source} -> {r.sink}")
    print(f"Cables landing in {r.source}: {len(r.source_cables)}")
    for name in names(r.source_cables):
        print(f"  {name}")
    print(f"\nMax flow = min cut = {r.value}")
    print("\nCable-disjoint routes (one flow decomposition):")
    for i, route in enumerate(r.routes(), 1):
        print(f"  {i}. {route}")
    print("\nMinimum cut closest to the source:")
    for name in names(r.source_cut):
        print(f"  {name}")
    if r.sink_cut != r.source_cut:
        print("\nMinimum cut closest to the sink (the cut is not unique):")
        for name in names(r.sink_cut):
            print(f"  {name}")


if __name__ == "__main__":
    main()
