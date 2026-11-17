"""Corte mínimo, unicidad, rutas disjuntas y cuello de botella externo."""
from dataclasses import dataclass, field

from .maxflow_ek import Unbounded
from .models import SINK, SOURCE, build_model


@dataclass
class CutResult:
    source: str
    sink: str
    mode: str
    include_planned: bool
    cluster_km: float
    value: int | None            # None = no hay corte finito
    cut: list = field(default_factory=list)          # ids de elementos cortados (lado fuente)
    unique: bool | None = None
    routes: list = field(default_factory=list)       # rutas disjuntas (Menger)
    details: dict = field(default_factory=dict)      # id -> {"stations": [...], "cables": [...]}
    note: str = ""

    def to_dict(self):
        return self.__dict__.copy()


def _cut_from_side(model, side):
    return sorted({eid for (u, v), eid in model.cuttable.items() if u in side and v not in side})


def _label(node, model, cables):
    kind = node[0]
    if node == SOURCE:
        return model.source
    if node == SINK:
        return "|".join(sorted(model.sink_regions)) if len(model.sink_regions) <= 2 else "WORLD"
    if kind == "R":
        return node[1]
    if kind in ("Cin", "Cout", "C"):
        return cables.loc[node[1], "name"] if node[1] in cables.index else node[1]
    if kind in ("Sin", "Sout"):
        return f"[{node[1]}]"
    return str(node)


def decompose_routes(model, cables):
    """Descompone el flujo en caminos s→t (cada uno usa 1 unidad). Quita ciclos."""
    flow = model.net.net_flow()
    routes = []
    while True:
        path, seen, u = [SOURCE], {SOURCE: 0}, SOURCE
        while u != SINK:
            nxt = next((v for v, f in flow.get(u, {}).items() if f > 0), None)
            if nxt is None:
                return routes
            if nxt in seen:  # ciclo: lo cancelamos y seguimos desde ahí
                i = seen[nxt]
                cyc = path[i:] + [nxt]
                for a, b in zip(cyc, cyc[1:]):
                    flow[a][b] -= 1
                for n in path[i + 1:]:
                    seen.pop(n, None)
                path = path[: i + 1]
                u = nxt
                continue
            seen[nxt] = len(path)
            path.append(nxt)
            u = nxt
        for a, b in zip(path, path[1:]):
            flow[a][b] -= 1
        labels = []
        for prev, n in zip([None] + path, path):
            if n[0] in ("Cout", "Sout"):      # cada elemento partido aparece dos veces
                continue
            if n[0] == "Sin" and prev != SOURCE:  # solo mostramos la estación de salida
                continue
            lab = _label(n, model, cables)
            if not labels or labels[-1] != lab:
                labels.append(lab)
        routes.append(" → ".join(labels))


def _details(model, lp, cut):
    out = {}
    for eid in cut:
        if model.mode == "cables":
            rows = lp[lp.cable_id == eid]
        else:
            rows = lp[lp.landing_point_id.isin(model.members.get(eid, {eid}))]
        out[eid] = {
            "stations": sorted(rows.landing_point_name.unique()),
            "cables": sorted(rows.cable_name.unique()),
            "countries": sorted(rows.region.unique()),
        }
    return out


def min_cut(lp, cables, source, sink="us", mode="cables", cluster_km=25.0,
            include_planned=False, protected=(), with_routes=True):
    model = build_model(lp, mode, source, sink, cluster_km, protected)
    res = CutResult(source, sink, mode, include_planned, cluster_km, None)
    try:
        res.value = model.net.max_flow(SOURCE, SINK)
    except Unbounded:
        res.note = "sin corte finito: hay una ruta formada solo por elementos protegidos"
        return res
    src_side = model.net.reachable_from(SOURCE)
    snk_side = model.net.reaching(SINK)
    res.cut = _cut_from_side(model, src_side)
    res.unique = res.cut == _cut_from_side(model, set(model.net.nodes()) - snk_side)
    res.details = _details(model, lp, res.cut)
    if with_routes:
        res.routes = decompose_routes(model, cables)
    return res


def external_bottleneck(lp, cables, source, sink="us", include_planned=False):
    """Corte mínimo cuando los cables del propio país NO se pueden cortar.

    Si da un número parecido al grado del país, hay un cuello de botella
    aguas abajo (p. ej. un país de tránsito). Si no hay corte finito, el país
    tiene cables que llegan directo al sumidero.
    """
    own = set(lp.loc[lp.region == source, "cable_id"])
    res = min_cut(lp, cables, source, sink, "cables", include_planned=include_planned,
                  protected=own, with_routes=False)
    res.mode = "external"  # se reporta como corte de cables
    if res.value is None:
        direct = sorted(cables.loc[c, "name"] for c in own
                        if lp.loc[lp.cable_id == c, "region"].isin(
                            build_model(lp, "cables", source, sink).sink_regions).any())
        res.note = f"sin corte externo finito; cables propios que llegan directo: {direct}"
    return res
