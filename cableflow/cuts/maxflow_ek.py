"""Edmonds–Karp desde cero, con capacidades enteras.

Lo usa el subpaquete `cableflow.cuts`. Es independiente de `cableflow/maxflow.py`
para no depender de su API; si quieren usar el suyo, basta con que devuelva
el grafo residual (ver `adapter_note` en el README de la extensión).

Además del valor del flujo devuelve:
  - el residual, para sacar el corte mínimo del lado fuente y del lado sumidero
  - el flujo neto por arco, para descomponer en rutas disjuntas (Menger)
"""
from collections import deque

INF = 10**9  # "infinito" entero: evita inf - inf = nan en el residual


class Unbounded(Exception):
    """Hay un camino s→t sin arcos cortables (p. ej. un cable protegido que llega directo)."""


class FlowNetwork:
    def __init__(self):
        self.cap = {}   # cap[u][v] capacidad original
        self.res = {}   # res[u][v] capacidad residual

    def add_node(self, u):
        self.cap.setdefault(u, {})
        self.res.setdefault(u, {})

    def add_edge(self, u, v, c):
        """Arco dirigido u→v. Si se repite, las capacidades se suman."""
        self.add_node(u)
        self.add_node(v)
        self.cap[u][v] = self.cap[u].get(v, 0) + c
        self.res[u][v] = self.res[u].get(v, 0) + c
        self.res[v].setdefault(u, 0)  # arco reverso residual

    def nodes(self):
        return self.cap.keys()

    def arcs(self):
        for u, nbrs in self.cap.items():
            for v, c in nbrs.items():
                yield u, v, c

    # ------------------------------------------------------------------ flujo
    def _bfs(self, s, t):
        parent = {s: None}
        q = deque([s])
        while q:
            u = q.popleft()
            for v, r in self.res[u].items():
                if r > 0 and v not in parent:
                    parent[v] = u
                    if v == t:
                        return parent
                    q.append(v)
        return None

    def max_flow(self, s, t):
        if s not in self.res or t not in self.res:
            return 0
        flow = 0
        while True:
            parent = self._bfs(s, t)
            if parent is None:
                return flow
            # cuello de botella del camino más corto
            b, v = INF, t
            while parent[v] is not None:
                u = parent[v]
                b = min(b, self.res[u][v])
                v = u
            if b >= INF:
                raise Unbounded("camino de capacidad infinita entre s y t")
            v = t
            while parent[v] is not None:
                u = parent[v]
                self.res[u][v] -= b
                self.res[v][u] += b
                v = u
            flow += b
            if flow >= INF:
                raise Unbounded("flujo no acotado")

    # ------------------------------------------------------------ post-flujo
    def reachable_from(self, s):
        """Nodos alcanzables desde s en el residual (lado fuente del corte)."""
        seen = {s}
        q = deque([s])
        while q:
            u = q.popleft()
            for v, r in self.res[u].items():
                if r > 0 and v not in seen:
                    seen.add(v)
                    q.append(v)
        return seen

    def reaching(self, t):
        """Nodos que alcanzan t en el residual (lado sumidero del corte)."""
        rev = {}
        for u, nbrs in self.res.items():
            for v, r in nbrs.items():
                if r > 0:
                    rev.setdefault(v, []).append(u)
        seen = {t}
        q = deque([t])
        while q:
            v = q.popleft()
            for u in rev.get(v, ()):
                if u not in seen:
                    seen.add(u)
                    q.append(u)
        return seen

    def net_flow(self):
        """Flujo neto positivo por arco original: f(u,v) = c(u,v) - r(u,v) > 0."""
        out = {}
        for u, v, c in self.arcs():
            f = c - self.res[u][v]
            if f > 0:
                out.setdefault(u, {})[v] = f
        return out
