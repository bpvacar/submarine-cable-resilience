import random

import networkx as nx
import pytest

from cableflow.graph import CableNetwork, build_flow_graph, load_network, region
from cableflow.maxflow import decompose_paths, max_flow, sink_side_cut, source_side_cut


def toy(cables):
    """cables: {name: [regions]} -> (capacity map, names)."""
    net = CableNetwork({c: c for c in cables}, {c: set(r) for c, r in cables.items()})
    return build_flow_graph(net), net.names


def cut_names(cut):
    return {u[1] for u, v in cut if u[0] == "in"}


def test_bottleneck_away_from_source():
    # Ecuador has 3 cables, but A and E both end in Panama and only C leaves it.
    cap, _ = toy({"A": ["EC", "PA"], "E": ["EC", "PA"], "C": ["PA", "US"], "B": ["EC", "US"]})
    s, t = region("EC"), region("US")
    value, flow, residual = max_flow(cap, s, t)
    assert value == 2
    assert cut_names(sink_side_cut(cap, residual, t)) == {"B", "C"}
    assert len(decompose_paths(flow, s, t)) == 2


def test_multi_landing_cable_counts_once():
    # D lands in three regions; as plain edges it would be counted twice.
    cap, _ = toy({"D": ["EC", "PA", "US"], "B": ["EC", "US"]})
    value, _, residual = max_flow(cap, region("EC"), region("US"))
    assert value == 2
    assert cut_names(source_side_cut(cap, residual, region("EC"))) == {"B", "D"}


def test_cables_are_bidirectional():
    cap, _ = toy({"A": ["X", "Y"], "B": ["Y", "Z"]})
    assert max_flow(cap, region("X"), region("Z"))[0] == 1
    assert max_flow(cap, region("Z"), region("X"))[0] == 1


def test_disconnected():
    cap, _ = toy({"A": ["X", "Y"], "B": ["Z", "W"]})
    assert max_flow(cap, region("X"), region("W"))[0] == 0


@pytest.mark.parametrize("seed", range(30))
def test_matches_networkx_on_random_graphs(seed):
    rng = random.Random(seed)
    n = rng.randint(4, 12)
    cap = {}
    for u in range(n):
        for v in range(u + 1, n):  # u < v only: no antiparallel arcs
            if rng.random() < 0.35:
                a, b = (u, v) if rng.random() < 0.5 else (v, u)
                cap.setdefault(a, {})[b] = rng.randint(1, 9)
    s, t = 0, n - 1
    value, flow, residual = max_flow(cap, s, t)

    g = nx.DiGraph()
    g.add_nodes_from(range(n))
    for u, nbrs in cap.items():
        for v, c in nbrs.items():
            g.add_edge(u, v, capacity=c)
    assert value == nx.maximum_flow_value(g, s, t)

    for cut in (source_side_cut(cap, residual, s), sink_side_cut(cap, residual, t)):
        assert sum(cap[u][v] for u, v in cut) == value
    assert sum(m for m, _ in decompose_paths(flow, s, t)) == value


def real_graph():
    cap = build_flow_graph(load_network())
    g = nx.DiGraph()
    for u, nbrs in cap.items():
        for v, c in nbrs.items():
            g.add_edge(u, v, capacity=c)
    return cap, g


@pytest.mark.parametrize(
    "country",
    ["Ecuador", "Colombia", "Peru", "Chile", "Argentina", "Uruguay", "Brazil", "Venezuela", "Panama", "Mexico"],
)
def test_real_data_matches_networkx(country):
    cap, g = real_graph()
    s, t = region(country), region("United States")
    value, _, residual = max_flow(cap, s, t)
    assert value == nx.maximum_flow_value(g, s, t)

    # Removing the cut cables really disconnects s from t.
    cut = source_side_cut(cap, residual, s)
    assert len(cut) == value
    h = g.copy()
    h.remove_edges_from(cut)
    assert not nx.has_path(h, s, t)
