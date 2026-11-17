"""Construcción de las redes de flujo para los tres modelos de falla.

Convenciones (las mismas del repo original):
  * Cada país es un nodo (se asume que el backbone terrestre doméstico no falla).
  * EE.UU. se parte: Alaska, Hawái, Puerto Rico e Islas Vírgenes son nodos aparte;
    el sumidero por defecto es EE.UU. contiguo.
  * No hay enlaces terrestres entre países.

Modelos:
  cables   : cada cable es un par Cin→Cout de capacidad 1 (lo que se corta son cables)
  stations : cada estación de aterrizaje es un par Sin→Sout de capacidad 1;
             los cables son infinitos (lo que se corta son estaciones)
  sites    : como stations, pero las estaciones del mismo país a ≤ cluster_km
             se fusionan en un "sitio" (falla correlacionada por zona)

Sumideros:
  "us"            : EE.UU. contiguo
  "world"         : todos los demás países juntos
  "country:<X>"   : un país concreto (p. ej. desconectar Ecuador de Israel)
"""
import math
from dataclasses import dataclass, field

import pandas as pd

from .maxflow_ek import INF, FlowNetwork

US_SPLIT = {"AK": "US-Alaska", "HI": "US-Hawaii", "PR": "US-Puerto Rico", "VI": "US-Virgin Islands"}
US_CONTIGUOUS = "US-Contiguous"
SOURCE, SINK = ("S",), ("T",)
MODES = ("cables", "stations", "sites")


# ---------------------------------------------------------------- datos
def region_of(country, landing_point_name):
    if country == "Virgin Islands (U.S.)":
        return "US-Virgin Islands"
    if country == "United States":
        parts = str(landing_point_name).split(", ")
        state = parts[-2] if len(parts) >= 2 else ""
        return US_SPLIT.get(state, US_CONTIGUOUS)
    return country


def load_data(cables_csv="data/cables.csv", lp_csv="data/cable_landing_points.csv",
              include_planned=False):
    cables = pd.read_csv(cables_csv)
    lp = pd.read_csv(lp_csv).dropna(subset=["country"])
    keep = set(cables.id) if include_planned else set(cables.loc[~cables.is_planned.astype(bool), "id"])
    lp = lp[lp.cable_id.isin(keep)].copy()
    lp["region"] = [region_of(c, n) for c, n in zip(lp.country, lp.landing_point_name)]
    return cables.set_index("id"), lp.reset_index(drop=True)


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def cluster_sites(lp, km):
    """Single-linkage dentro de cada país: estación -> id del sitio (union-find)."""
    pts = lp.drop_duplicates("landing_point_id")[["landing_point_id", "region", "latitude", "longitude"]]
    parent = {p: p for p in pts.landing_point_id}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    if km > 0:
        for _, g in pts.groupby("region"):
            rows = list(g.itertuples(index=False))
            for i in range(len(rows)):
                for j in range(i + 1, len(rows)):
                    a, b = rows[i], rows[j]
                    if haversine_km(a.latitude, a.longitude, b.latitude, b.longitude) <= km:
                        ra, rb = find(a.landing_point_id), find(b.landing_point_id)
                        if ra != rb:
                            parent[ra] = rb
    return {p: find(p) for p in parent}


# ---------------------------------------------------------------- red
@dataclass
class CutModel:
    net: FlowNetwork
    mode: str
    source: str
    sink_regions: set
    # arcos cortables: (u, v) -> id del elemento (cable o estación/sitio)
    cuttable: dict = field(default_factory=dict)
    # id de sitio -> estaciones que agrupa (solo modo sites/stations)
    members: dict = field(default_factory=dict)


def sink_regions_for(lp, source, sink):
    regions = set(lp.region.unique())
    if sink == "us":
        out = {US_CONTIGUOUS}
    elif sink == "world":
        out = regions - {source}
    elif sink.startswith("country:"):
        out = {sink.split(":", 1)[1]}
    else:
        raise ValueError(f"sumidero desconocido: {sink}")
    missing = out - regions
    if missing:
        raise ValueError(f"sin cables en los datos: {sorted(missing)}")
    if source not in regions:
        raise ValueError(f"'{source}' no aparece en los datos")
    return out - {source}


def build_model(lp, mode="cables", source="Ecuador", sink="us", cluster_km=25.0,
                protected=()):
    """Arma la red. `protected` = ids de elementos que no se pueden cortar (capacidad INF)."""
    if mode not in MODES:
        raise ValueError(f"modo desconocido: {mode}")
    sinks = sink_regions_for(lp, source, sink)
    net = FlowNetwork()
    m = CutModel(net, mode, source, sinks)
    protected = set(protected)

    def reg(r):
        if r == source:
            return SOURCE
        if r in sinks:
            return SINK
        return ("R", r)

    net.add_node(SOURCE)
    net.add_node(SINK)

    if mode == "cables":
        for cid, g in lp.groupby("cable_id"):
            cin, cout = ("Cin", cid), ("Cout", cid)
            net.add_edge(cin, cout, INF if cid in protected else 1)
            m.cuttable[(cin, cout)] = cid
            for r in g.region.unique():
                net.add_edge(reg(r), cin, INF)
                net.add_edge(cout, reg(r), INF)
        return m

    site_of = cluster_sites(lp, cluster_km if mode == "sites" else 0)
    seen_station, seen_link = set(), set()
    for row in lp.itertuples(index=False):
        st = site_of[row.landing_point_id]
        m.members.setdefault(st, set()).add(row.landing_point_id)
        sin, sout = ("Sin", st), ("Sout", st)
        if st not in seen_station:
            seen_station.add(st)
            net.add_edge(sin, sout, INF if st in protected else 1)
            m.cuttable[(sin, sout)] = st
            r = reg(row.region)
            net.add_edge(r, sin, INF)
            net.add_edge(sout, r, INF)
        if (row.cable_id, st) in seen_link:
            continue
        seen_link.add((row.cable_id, st))
        cnode = ("C", row.cable_id)
        net.add_edge(cnode, sin, INF)
        net.add_edge(sout, cnode, INF)
    return m
