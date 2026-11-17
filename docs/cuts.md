# Extensión `cableflow.cuts`: Israel, cortes por estación y fallas correlacionadas

## Qué agrega

| Archivo | Qué hace |
|---|---|
| `cableflow/cuts/maxflow_ek.py` | Edmonds–Karp propio con capacidades enteras (`INF = 10**9`), corte del lado fuente y del lado sumidero, flujo neto por arco |
| `cableflow/cuts/models.py` | Arma la red para 3 modelos (`cables`, `stations`, `sites`) y 3 sumideros (`us`, `world`, `country:<X>`) |
| `cableflow/cuts/analysis.py` | Corte mínimo, unicidad, rutas disjuntas (Menger) y cuello de botella externo |
| `cableflow/cuts/__main__.py` | CLI: `python -m cableflow.cuts <País> ...` |
| `scripts/compare_countries.py` | Tabla para varios países o ranking global (`--all`) |
| `scripts/sweep_cluster_radius.py` | Sensibilidad del corte por sitios al radio de agrupación |
| `scripts/plot_cut_map.py` | Mapa esquemático del corte |
| `tests/test_cuts.py` | 49 tests: EK contra networkx, grafo de juguete, valores reales, certificado de minimalidad |

## Modelos

| Modo | Elemento cortable (capacidad 1) | Infinito | Pregunta |
|---|---|---|---|
| `cables` | cable, partido `Cin → Cout` | aterrizajes | ¿cuántos cables? (modelo original) |
| `stations` | estación de aterrizaje, partida `Sin → Sout` | cables | ¿cuántas estaciones físicas? |
| `sites` | grupo de estaciones del mismo país a ≤ `--cluster-km` km | cables | ¿cuántos eventos locales (sismo, tsunami, sabotaje)? |

Un corte de **nodos** se reduce a un corte de **arcos** partiendo cada nodo `v` en `v_in → v_out` con capacidad 1.
Así se resuelve con el mismo max-flow, y por Menger el valor es el número máximo de rutas que no comparten estación.

Otras opciones:
- `--sink world` usa un súper-sumidero con todos los demás países.
- `--sink country:Israel` resuelve el corte entre dos países.
- `--external` protege los cables propios (capacidad ∞) para buscar un cuello de botella fuera del país.

## Resultados (snapshot 2026-11-12, sumidero EE.UU. contiguo)

| País | Cables (activos / +planificados) | Estaciones | Sitios a 25 km | Corte externo |
|---|---|---|---|---|
| Ecuador | 4 / 5 | 3 / 4 | **2 / 2** | no finito (PCCS y SAm-1 llegan directo) |
| Israel | 4 / 7 | **2** / 5 | 2 / 3 | 26 / 37 |

**Ecuador.**
- Con estaciones el corte baja a 3, porque PanAm South y SAm-1 comparten Punta Carnero.
- Con sitios baja a 2: Punta Carnero, Salinas y Ancón están en la península de Santa Elena, y queda Manta aparte.
- El CSN-1 planificado aterriza en Ancón, el mismo sitio, así que no mejora la resiliencia por sitios.

**Israel.**
- Bastan 2 estaciones: **Tel Aviv** (Blue, Jonah, MedNautilus) y **Tirat Carmel** (Exelera North, MedNautilus). IC-1 es doméstico.
- Andromeda y EMC West-1/2 aterrizan en estaciones nuevas (Haifa, Netanya, Ashkelon) y suben el corte por estaciones de 2 a 5: diversifican de verdad.
- El corte externo es de 26 cables, así que el punto débil está dentro de Israel, no en Chipre ni en el Mediterráneo.

**Ecuador ↔ Israel** (`--sink country:Israel`):
- Por cables el corte es 4 y no es único: sirven tanto los 4 cables de Ecuador como los 4 de Israel.
- Por estaciones el corte es 2 (Tel Aviv y Tirat Carmel): el lado débil es Israel.

**Ranking global** (`scripts/compare_countries.py --all`, 184 países con ruta submarina a EE.UU.):
- En el 62 % de los países, cortar estaciones requiere menos elementos que cortar cables.
- 46 países dependen de una sola estación, y 73 caen con un solo sitio a 25 km.
- Casos extremos: Singapur (27 cables, 1 sitio), Pakistán (7 cables, 1 estación: Karachi) y Djibouti (8 cables, 1 sitio).

**Sensibilidad al radio** (`results/sweep_radius.png`):
- Israel baja a 1 sitio desde 50 km, porque el clustering single-linkage encadena Haifa con la costa de Tel Aviv.
- Ecuador baja a 1 sitio desde 150 km (Manta con Santa Elena).

## Limitaciones
- Se asume que el backbone terrestre doméstico no falla, y no hay enlaces terrestres entre países (Israel–Jordania y Ecuador–Colombia/Perú existen por tierra).
- Todos los elementos pesan 1; el CSV no trae capacidad en Tbps.
- El clustering single-linkage encadena estaciones, así que el resultado de `sites` depende del radio: por eso está el barrido.
- Las coordenadas `is_tbd` son aproximadas. Las rutas de Menger son una descomposición válida entre varias posibles.

## Reproducir
```bash
python -m cableflow.cuts Israel --mode all --external
python -m cableflow.cuts Ecuador --mode all --include-planned
python -m cableflow.cuts Ecuador --sink country:Israel --mode all
python scripts/compare_countries.py Ecuador Israel
python scripts/compare_countries.py --all          # ~2.5 min
python scripts/sweep_cluster_radius.py
python scripts/plot_cut_map.py Israel --mode stations
pytest tests/test_cuts.py
```

## Usar el `maxflow.py` original en vez del EK incluido
`analysis.py` solo usa de la red: `max_flow(s, t)`, `reachable_from(s)`, `reaching(t)` y `net_flow()`.
Si `cableflow/maxflow.py` expone el residual, basta con un adaptador de esas cuatro funciones.
Los tests `test_ek_igual_a_networkx` y `test_valores_*` validan cualquiera de las dos implementaciones.
