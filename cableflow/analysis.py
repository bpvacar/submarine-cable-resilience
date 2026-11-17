"""Run the max-flow / min-cut analysis for one source region."""

from dataclasses import dataclass

from .graph import CableNetwork, build_flow_graph, load_network, region
from .maxflow import decompose_paths, max_flow, sink_side_cut, source_side_cut

COUNTRIES = [
    "Ecuador", "Colombia", "Peru", "Chile", "Argentina",
    "Uruguay", "Brazil", "Venezuela", "Panama", "Mexico",
]
SINK = "United States"


@dataclass
class Result:
    source: str
    sink: str
    value: int
    source_cut: list[str]  # cable ids, minimum cut closest to the source
    sink_cut: list[str]  # cable ids, minimum cut closest to the sink
    paths: list[list]  # cable-disjoint routes, as lists of graph nodes
    source_cables: list[str]  # cable ids that land in the source and leave it
    net: CableNetwork

    def name(self, cable_id):
        return self.net.names[cable_id]

    def routes(self):
        """Routes as readable strings: 'Ecuador -> [PCCS] -> United States'."""
        out = []
        for path in self.paths:
            parts = []
            for kind, key in path:
                if kind == "region":
                    parts.append(key)
                elif kind == "in":
                    parts.append(f"[{self.name(key)}]")
            out.append(" -> ".join(parts))
        return out


def _cut_cables(cut):
    # Only ("in", c) -> ("out", c) arcs can be in a minimum cut; INF arcs never are.
    return sorted(u[1] for u, v in cut if u[0] == "in" and v == ("out", u[1]))


def analyze(source, sink=SINK, include_planned=False, net=None):
    net = net or load_network(include_planned=include_planned)
    cap = build_flow_graph(net)
    s, t = region(source), region(sink)
    for node, label in ((s, source), (t, sink)):
        if node not in cap:
            raise ValueError(f"No cable lands in region {label!r}.")
    value, flow, residual = max_flow(cap, s, t)
    return Result(
        source=source,
        sink=sink,
        value=value,
        source_cut=_cut_cables(source_side_cut(cap, residual, s)),
        sink_cut=_cut_cables(sink_side_cut(cap, residual, t)),
        paths=[p for _, p in decompose_paths(flow, s, t)],
        source_cables=sorted(
            c for c, regs in net.landings.items() if source in regs and len(regs) > 1
        ),
        net=net,
    )
