"""Edmonds–Karp max-flow, minimum cuts and flow decomposition.

Graphs are capacity maps ``cap[u][v] = c``. Antiparallel arcs (both ``u -> v``
and ``v -> u``) are not supported; the cable network never has them.
"""

from collections import defaultdict, deque


def max_flow(cap: dict, s, t):
    """Return ``(value, flow, residual)``.

    Repeatedly finds a shortest augmenting path in the residual graph with BFS
    and pushes its bottleneck capacity. O(V E^2).
    """
    for u, nbrs in cap.items():
        for v in nbrs:
            if u in cap.get(v, {}):
                raise ValueError(f"antiparallel arcs {u} <-> {v} are not supported")

    residual = defaultdict(lambda: defaultdict(int))
    for u, nbrs in cap.items():
        for v, c in nbrs.items():
            residual[u][v] += c
            residual[v][u] += 0  # reverse arc, starts empty

    value = 0
    while True:
        parent = {s: None}
        queue = deque([s])
        while queue and t not in parent:
            u = queue.popleft()
            for v, r in residual[u].items():
                if r > 0 and v not in parent:
                    parent[v] = u
                    queue.append(v)
        if t not in parent:
            break

        path = []
        v = t
        while parent[v] is not None:
            path.append((parent[v], v))
            v = parent[v]
        bottleneck = min(residual[u][v] for u, v in path)
        for u, v in path:
            residual[u][v] -= bottleneck
            residual[v][u] += bottleneck
        value += bottleneck

    flow = {
        u: {v: c - residual[u][v] for v, c in nbrs.items() if c - residual[u][v] > 0}
        for u, nbrs in cap.items()
    }
    return value, flow, residual


def _reachable(start, neighbors):
    seen = {start}
    stack = [start]
    while stack:
        u = stack.pop()
        for v in neighbors(u):
            if v not in seen:
                seen.add(v)
                stack.append(v)
    return seen


def source_side_cut(cap: dict, residual, s):
    """Minimum cut closest to s: arcs leaving the set reachable from s in the
    residual graph."""
    S = _reachable(s, lambda u: [v for v, r in residual[u].items() if r > 0])
    return [(u, v) for u in S for v in cap.get(u, {}) if v not in S]


def sink_side_cut(cap: dict, residual, t):
    """Minimum cut closest to t: arcs entering the set that can still reach t in
    the residual graph."""
    incoming = defaultdict(list)
    for u, nbrs in residual.items():
        for v, r in nbrs.items():
            if r > 0:
                incoming[v].append(u)
    T = _reachable(t, lambda v: incoming[v])
    return [(u, v) for u, nbrs in cap.items() if u not in T for v in nbrs if v in T]


def decompose_paths(flow: dict, s, t):
    """Split an s-t flow into paths ``[(amount, [s, ..., t]), ...]``.

    Cycles found along the way carry no s-t flow and are cancelled.
    """
    f = {u: dict(nbrs) for u, nbrs in flow.items()}
    paths = []
    while any(x > 0 for x in f.get(s, {}).values()):
        path, pos, u = [s], {s: 0}, s
        while u != t:
            v = next(v for v, x in f[u].items() if x > 0)
            if v in pos:  # cycle: remove it and continue from v
                cycle = path[pos[v]:] + [v]
                m = min(f[a][b] for a, b in zip(cycle, cycle[1:]))
                for a, b in zip(cycle, cycle[1:]):
                    f[a][b] -= m
                path = path[: pos[v] + 1]
                pos = {n: i for i, n in enumerate(path)}
                u = v
                continue
            path.append(v)
            pos[v] = len(path) - 1
            u = v
        m = min(f[a][b] for a, b in zip(path, path[1:]))
        for a, b in zip(path, path[1:]):
            f[a][b] -= m
        paths.append((m, path))
    return paths
