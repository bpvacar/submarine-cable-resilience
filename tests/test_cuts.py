"""Tests de la extensión cableflow.cuts (pytest)."""
import random

import networkx as nx
import pandas as pd
import pytest

from cableflow.cuts import build_model, cluster_sites, external_bottleneck, load_data, min_cut
from cableflow.cuts.maxflow_ek import INF, FlowNetwork, Unbounded
from cableflow.cuts.models import SINK, SOURCE

DATA = ("data/cables.csv", "data/cable_landing_points.csv")


# --------------------------------------------------------------- Edmonds–Karp
@pytest.mark.parametrize("seed", range(25))
def test_ek_igual_a_networkx(seed):
    rng = random.Random(seed)
    n = rng.randint(4, 14)
    G = nx.DiGraph()
    net = FlowNetwork()
    for _ in range(rng.randint(n, 4 * n)):
        u, v = rng.sample(range(n), 2)
        c = rng.randint(1, 9)
        G.add_edge(u, v, capacity=G.get_edge_data(u, v, {"capacity": 0})["capacity"] + c)
        net.add_edge(u, v, c)
    G.add_nodes_from([0, n - 1]); net.add_node(0); net.add_node(n - 1)
    assert net.max_flow(0, n - 1) == nx.maximum_flow_value(G, 0, n - 1)


def test_unbounded():
    net = FlowNetwork()
    net.add_edge("s", "a", INF); net.add_edge("a", "t", INF)
    with pytest.raises(Unbounded):
        net.max_flow("s", "t")


# --------------------------------------------------------------- juguete
def toy_lp():
    """País A con 2 cables que salen de la MISMA estación hacia B (sumidero)."""
    rows = [
        ("c1", "C1", "a1", "A1, A", "A", 0.0, 0.0),
        ("c1", "C1", "b1", "B1, B", "B", 0.0, 10.0),
        ("c2", "C2", "a1", "A1, A", "A", 0.0, 0.0),
        ("c2", "C2", "b2", "B2, B", "B", 1.0, 10.0),
        ("c3", "C3", "a2", "A2, A", "A", 0.05, 0.0),   # ~5.5 km de a1
        ("c3", "C3", "b3", "B3, B", "B", 5.0, 10.0),
    ]
    df = pd.DataFrame(rows, columns=["cable_id", "cable_name", "landing_point_id",
                                     "landing_point_name", "country", "latitude", "longitude"])
    df["region"] = df.country
    cables = pd.DataFrame({"name": ["C1", "C2", "C3"]}, index=["c1", "c2", "c3"])
    return cables, df


@pytest.mark.parametrize("mode,km,expected", [("cables", 0, 3), ("stations", 0, 2), ("sites", 10, 1)])
def test_juguete(mode, km, expected):
    cables, lp = toy_lp()
    r = min_cut(lp, cables, "A", "country:B", mode, km)
    assert r.value == expected
    assert len(r.routes) == expected


def test_cluster_radio_cero_no_agrupa():
    _, lp = toy_lp()
    s = cluster_sites(lp, 0)
    assert len(set(s.values())) == len(s)


# --------------------------------------------------------------- datos reales
@pytest.fixture(scope="module")
def activos():
    return load_data(*DATA, include_planned=False)


@pytest.fixture(scope="module")
def todos():
    return load_data(*DATA, include_planned=True)


@pytest.mark.parametrize("country,mode,expected", [
    ("Ecuador", "cables", 4), ("Ecuador", "stations", 3), ("Ecuador", "sites", 2),
    ("Israel", "cables", 4), ("Israel", "stations", 2), ("Israel", "sites", 2),
])
def test_valores_activos(activos, country, mode, expected):
    cables, lp = activos
    assert min_cut(lp, cables, country, "us", mode).value == expected


@pytest.mark.parametrize("country,mode,expected", [
    ("Ecuador", "cables", 5), ("Ecuador", "stations", 4), ("Ecuador", "sites", 2),
    ("Israel", "cables", 7), ("Israel", "stations", 5), ("Israel", "sites", 3),
])
def test_valores_con_planificados(todos, country, mode, expected):
    cables, lp = todos
    assert min_cut(lp, cables, country, "us", mode).value == expected


def test_ecuador_coincide_con_modelo_original(activos):
    """El modo cables debe reproducir el resultado del README original (4, único)."""
    cables, lp = activos
    r = min_cut(lp, cables, "Ecuador", "us", "cables")
    assert r.unique
    assert {cables.loc[c, "name"] for c in r.cut} == {
        "Pacific Caribbean Cable System (PCCS)", "PanAm South",
        "South America-1 (SAm-1)", "South Pacific Cable System (SPCS)/Mistral"}


def _connected_without(model, removed):
    """BFS en la red original sin los arcos cortados."""
    seen, stack = {SOURCE}, [SOURCE]
    while stack:
        u = stack.pop()
        for v, c in model.net.cap[u].items():
            if c > 0 and (u, v) not in removed and v not in seen:
                seen.add(v); stack.append(v)
    return SINK in seen


@pytest.mark.parametrize("country,mode", [("Ecuador", "stations"), ("Ecuador", "sites"),
                                          ("Israel", "stations"), ("Israel", "cables")])
def test_corte_es_certificado_minimal(activos, country, mode):
    cables, lp = activos
    r = min_cut(lp, cables, country, "us", mode)
    model = build_model(lp, mode, country, "us")
    arcs = {a for a, eid in model.cuttable.items() if eid in r.cut}
    assert len(arcs) == r.value
    assert not _connected_without(model, arcs)
    for a in arcs:                    # devolver cualquier elemento reconecta
        assert _connected_without(model, arcs - {a})
    assert len(r.routes) == r.value


def test_externo(activos):
    cables, lp = activos
    assert external_bottleneck(lp, cables, "Ecuador").value is None   # PCCS y SAm-1 llegan directo
    assert external_bottleneck(lp, cables, "Israel").value == 26


def test_ecuador_israel(activos):
    cables, lp = activos
    assert min_cut(lp, cables, "Ecuador", "country:Israel", "cables").value == 4
    assert min_cut(lp, cables, "Ecuador", "country:Israel", "stations").value == 2
