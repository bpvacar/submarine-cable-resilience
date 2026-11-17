# Submarine cable resilience (min-cut)

How many submarine cables must fail, at minimum, to cut every submarine route
between a country and the United States? We model the cable network as a flow
network and compute an s-t minimum cut with max-flow (Edmonds–Karp), written
from scratch in [`cableflow/maxflow.py`](cableflow/maxflow.py).

Course: CMP 4007 Advanced Algorithms, USFQ.

## Model

```
country --∞--> c_in --1--> c_out --∞--> country
```

- **One node per country.** All landing points of a country are merged, which
  assumes a domestic terrestrial backbone that does not fail.
- **The US is split.** Alaska, Hawaii, Puerto Rico and the U.S. Virgin Islands
  are separate nodes. The sink `United States` is the contiguous states.
- **Each cable is two nodes** joined by an arc of capacity 1. That arc is the
  cable, so a cable costs 1 to cut regardless of how many countries it touches.
  Landing arcs have capacity ∞ and are never cut.
- **No land links between countries.** Only submarine routes count.
- **Active cables only** by default (`is_planned = False`, 608 of 714).
  `--include-planned` adds the rest.

By max-flow/min-cut (and Menger's theorem), the max flow equals both the number
of cable-disjoint routes and the minimum number of cables that must fail.

## Usage

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m cableflow Ecuador
.venv/bin/python -m cableflow Chile --include-planned
.venv/bin/python -m pytest
```

Tests cross-check the max-flow against `networkx` on random graphs and on the
real network for the ten countries in the assignment.

## Results

### Ecuador → United States: 4 cables

All four cables that land in Ecuador must fail. The cut is unique: the
source-side and sink-side minimum cuts coincide.

| Cable-disjoint route |
|---|
| Ecuador → PCCS → United States |
| Ecuador → PanAm South → Panama → ARCOS → United States |
| Ecuador → SAm-1 → United States |
| Ecuador → SPCS/Mistral → Guatemala → AMX-1 → United States |

With CSN-1 (planned, RFS 2026 Q4) the answer is 5. Full output in
[`results/`](results/).

## Data

[`data/`](data/) is a snapshot of TeleGeography's
[Submarine Cable Map](https://www.submarinecablemap.com) taken on 2026-11-12,
licensed CC BY-SA 4.0 (as cited in the assignment). Regenerate it with
`python3 scripts/fetch_submarine_cables.py`.

- `cables.csv`: one row per cable (length, RFS year, owners, countries).
- `cable_landing_points.csv`: one row per (cable, landing point), with
  coordinates. Landing points come in alphabetical order by country, not in
  route order.
