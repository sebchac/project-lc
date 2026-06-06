#!/usr/bin/env python3
"""Módulo de diagnóstico de red para el grafo de graphify.

Lee graphify-out/graph.json y reporta las propiedades de red que pide el
CLAUDE.md (sección "Módulo de diagnóstico"):

  - Distribución de grado: ¿ley de potencia? ¿hay hubs dominantes?
  - Coeficiente de clustering + longitud media de camino: ¿small-world?
  - Entropía entre comunidades: ¿atención concentrada o distribuida?
  - Traza año a año: ¿el campo se consolida o diversifica?

Además, por el hallazgo entidad-vs-concepto de este corpus, reporta la
composición por file_type y la centralidad cruzada (top nodos por grado con
su tipo) — insumo para decidir re-extracciones con foco conceptual.

Escribe graphify-out/GRAPH_DIAGNOSTICS.md (archivo propio, NO toca el
GRAPH_REPORT.md que regenera graphify) e imprime un resumen por stdout.

Uso:
    python code/graph_diagnostics.py [ruta/a/graph.json]
"""
from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import networkx as nx
import numpy as np

YEAR_RE = re.compile(r"(19|20)\d{2}")
# Tipos que usa la versión instalada de graphify (su prompt lista
# code|document|paper|image|concept; rationale aparece en variantes del skill).
VALID_TYPES = {"code", "document", "paper", "image", "rationale", "concept"}


# ---------------------------------------------------------------- carga
def load_graph(path: Path) -> tuple[nx.Graph, dict]:
    data = json.loads(path.read_text())
    G = nx.Graph()
    for n in data["nodes"]:
        G.add_node(n["id"], **{k: v for k, v in n.items() if k != "id"})
    edge_key = "links" if "links" in data else "edges"
    for e in data.get(edge_key, []):
        if e["source"] in G and e["target"] in G:
            G.add_edge(e["source"], e["target"], **{
                k: v for k, v in e.items() if k not in ("source", "target")})
    return G, data


def node_year(attrs: dict) -> int | None:
    txt = f"{attrs.get('source_file', '') or ''} {attrs.get('label', '') or ''}"
    m = YEAR_RE.search(txt)
    return int(m.group(0)) if m else None


# ----------------------------------------------------- métricas de red
def gini(values: list[int]) -> float:
    if not values:
        return 0.0
    x = np.sort(np.array(values, dtype=float))
    n = len(x)
    if x.sum() == 0:
        return 0.0
    cum = np.cumsum(x)
    return float((n + 1 - 2 * np.sum(cum) / cum[-1]) / n)


def fit_powerlaw(degrees: list[int]) -> dict:
    """Ajuste heurístico de ley de potencia: MLE de alpha sobre la cola
    (x >= xmin), eligiendo xmin por mínima distancia KS. No es un test
    riguroso power-law-vs-lognormal; es un indicador de cola pesada."""
    deg = np.array([d for d in degrees if d > 0])
    if len(deg) < 10:
        return {"ok": False, "reason": "muy pocos nodos con grado > 0"}
    best = None
    for xmin in range(1, max(2, int(np.percentile(deg, 90))) + 1):
        tail = deg[deg >= xmin]
        if len(tail) < 10:
            continue
        # MLE continuo (Hill): alpha = 1 + n / sum(ln(x/xmin))
        s = np.sum(np.log(tail / (xmin - 0.5)))
        if s <= 0:
            continue
        alpha = 1.0 + len(tail) / s
        # KS entre CCDF empírica y teórica
        xs = np.sort(tail)
        cdf_emp = np.arange(1, len(xs) + 1) / len(xs)
        cdf_fit = 1.0 - (xs / xmin) ** (1.0 - alpha)
        ks = float(np.max(np.abs(cdf_emp - cdf_fit)))
        if best is None or ks < best["ks"]:
            best = {"alpha": float(alpha), "xmin": int(xmin),
                    "ks": ks, "n_tail": int(len(tail))}
    if best is None:
        return {"ok": False, "reason": "no se pudo ajustar"}
    best["ok"] = True
    # Heavy-tailed si 2 < alpha < 3.5 y KS bajo
    best["heavy_tailed"] = (2.0 < best["alpha"] < 3.5) and best["ks"] < 0.12
    return best


def shannon_entropy(counts: list[int]) -> tuple[float, float]:
    """Entropía de Shannon (bits) y su versión normalizada [0,1]."""
    total = sum(counts)
    if total == 0 or len(counts) <= 1:
        return 0.0, 0.0
    probs = [c / total for c in counts if c > 0]
    H = -sum(p * math.log2(p) for p in probs)
    return H, H / math.log2(len(counts))


# ---------------------------------------------------------------- main
def diagnose(path: Path) -> str:
    G, data = load_graph(path)
    n, m = G.number_of_nodes(), G.number_of_edges()
    L = []
    L.append(f"# Diagnóstico de red del grafo  ({date.today().isoformat()})")
    L.append("")
    L.append(f"Fuente: `{path}`  ·  generado por `code/graph_diagnostics.py`")
    L.append("")

    # --- Resumen estructural ---
    components = list(nx.connected_components(G))
    giant = max(components, key=len) if components else set()
    density = nx.density(G)
    degrees = [d for _, d in G.degree()]
    L.append("## 1. Estructura general")
    L.append("")
    L.append(f"- Nodos: **{n}** · Aristas: **{m}** · Grado medio: **{2*m/n:.2f}**")
    L.append(f"- Densidad: {density:.5f}")
    L.append(f"- Componentes conexas: **{len(components)}** "
             f"(componente gigante: {len(giant)} nodos = {len(giant)/n:.0%})")
    aislados = sum(1 for d in degrees if d == 0)
    hojas = sum(1 for d in degrees if d == 1)
    L.append(f"- Nodos aislados (grado 0): {aislados} · "
             f"hojas (grado 1): {hojas} ({hojas/n:.0%})")
    if m < n:
        L.append(f"- ⚠️ Hay menos aristas que nodos: el grafo es casi un "
                 f"**bosque de estrellas** — pocos hubs concentran las conexiones "
                 f"y la mayoría de los nodos cuelgan de ellos.")
    L.append("")

    # --- Distribución de grado / ley de potencia ---
    pl = fit_powerlaw(degrees)
    deg_sorted = sorted(((d, G.nodes[node].get("label", node))
                         for node, d in G.degree()), reverse=True)
    L.append("## 2. Distribución de grado")
    L.append("")
    L.append(f"- Grado máx: {max(degrees)} · medio: {np.mean(degrees):.2f} · "
             f"mediana: {int(np.median(degrees))}")
    L.append(f"- Gini del grado: **{gini(degrees):.3f}** "
             f"(0 = parejo, →1 = todo concentrado en pocos hubs)")
    if pl.get("ok"):
        verdict = ("**sí, cola pesada**" if pl["heavy_tailed"]
                   else "ajuste débil — no claramente ley de potencia")
        L.append(f"- Ajuste ley de potencia: α = {pl['alpha']:.2f}, "
                 f"x_min = {pl['xmin']}, KS = {pl['ks']:.3f} → {verdict}")
        L.append(f"  - *(heurístico MLE+KS sobre la cola, n={pl['n_tail']}; "
                 f"no es un test riguroso power-law vs lognormal)*")
    else:
        L.append(f"- Ajuste ley de potencia: {pl.get('reason')}")
    L.append("")
    L.append("Top 10 nodos por grado (con tipo):")
    L.append("")
    L.append("| Grado | Nodo | file_type |")
    L.append("|---|---|---|")
    for node, d in sorted(G.degree(), key=lambda x: x[1], reverse=True)[:10]:
        a = G.nodes[node]
        L.append(f"| {d} | {a.get('label', node)[:48]} | "
                 f"{a.get('file_type', '?')} |")
    L.append("")

    # --- Clustering + small-world ---
    L.append("## 3. Clustering y small-world")
    L.append("")
    avg_clust = nx.average_clustering(G)
    trans = nx.transitivity(G)
    L.append(f"- Coef. de clustering medio: **{avg_clust:.4f}** · "
             f"transitividad: {trans:.4f}")
    Gg = G.subgraph(giant)
    if len(giant) > 2:
        avg_path = nx.average_shortest_path_length(Gg)
        diam = nx.diameter(Gg)
        k = 2 * Gg.number_of_edges() / Gg.number_of_nodes()
        c_rand = k / (len(giant) - 1)
        l_rand = math.log(len(giant)) / math.log(k) if k > 1 else float("nan")
        sigma = ((avg_clust / c_rand) / (avg_path / l_rand)
                 if c_rand > 0 and not math.isnan(l_rand) and l_rand > 0
                 else float("nan"))
        L.append(f"- Sobre la componente gigante ({len(giant)} nodos): "
                 f"camino medio = {avg_path:.2f}, diámetro = {diam}")
        L.append(f"- Referencia aleatoria (ER): C_rand ≈ {c_rand:.4f}, "
                 f"L_rand ≈ {l_rand:.2f}")
        if not math.isnan(sigma):
            sw = ("**small-world** (σ > 1)" if sigma > 1
                  else "no small-world (σ ≤ 1)")
            L.append(f"- σ = (C/C_rand)/(L/L_rand) = **{sigma:.2f}** → {sw}")
        if avg_clust < 0.05:
            L.append("- ⚠️ Clustering casi nulo: topología de estrellas/árbol, "
                     "no de comunidades densas. Coherente con un grafo "
                     "entidad-céntrico (documentos→entidad, sin triángulos "
                     "concepto-concepto).")
    L.append("")

    # --- Entropía entre comunidades ---
    L.append("## 4. Entropía entre comunidades")
    L.append("")
    comm = Counter(G.nodes[node].get("community", -1) for node in G)
    sizes = sorted(comm.values(), reverse=True)
    H, Hn = shannon_entropy(sizes)
    L.append(f"- Comunidades: **{len(comm)}** · entropía = {H:.2f} bits · "
             f"normalizada = **{Hn:.3f}** (1 = atención repartida pareja)")
    top_share = sizes[0] / n if sizes else 0
    L.append(f"- Comunidad mayor: {sizes[0]} nodos ({top_share:.0%} del grafo) · "
             f"top-5 suman {sum(sizes[:5])} ({sum(sizes[:5])/n:.0%})")
    if Hn > 0.85:
        L.append("- Lectura: atención **muy distribuida** — muchas comunidades "
                 "pequeñas, sin un núcleo temático dominante.")
    elif Hn < 0.6:
        L.append("- Lectura: atención **concentrada** en pocos clusters.")
    L.append("")

    # --- Composición por tipo (hallazgo entidad-vs-concepto) ---
    L.append("## 5. Composición por tipo y centralidad cruzada")
    L.append("")
    ft = Counter(G.nodes[node].get("file_type", "?") for node in G)
    L.append("Distribución de `file_type`:")
    L.append("")
    for t, c in ft.most_common():
        flag = "" if t in VALID_TYPES else "  ⚠️ tipo fuera del enum de graphify"
        L.append(f"- `{t}`: {c} ({c/n:.0%}){flag}")
    # grado medio de conceptos vs entidades
    concept_types = {"rationale", "concept"}
    deg_concept = [d for node, d in G.degree()
                   if G.nodes[node].get("file_type") in concept_types]
    deg_entity = [d for node, d in G.degree()
                  if G.nodes[node].get("file_type") not in concept_types]
    L.append("")
    if deg_concept and deg_entity:
        L.append(f"- Grado medio de nodos concepto/rationale: "
                 f"{np.mean(deg_concept):.2f}")
        L.append(f"- Grado medio del resto (entidades/documentos): "
                 f"{np.mean(deg_entity):.2f}")
    # posición de los conceptos ancla en el ranking de centralidad
    ranking = [node for node, _ in sorted(G.degree(), key=lambda x: x[1],
                                           reverse=True)]
    first_concept = next(
        (i + 1 for i, node in enumerate(ranking)
         if G.nodes[node].get("file_type") in concept_types), None)
    # 'concept' es un cajón de sastre en graphify: mezcla conceptos reales con
    # entidades nombradas (FNE, TDLC quedan tipadas 'concept'). Si pesa mucho,
    # las métricas por tipo son solo indicativas.
    catchall = ft.get("concept", 0) / n > 0.30
    if catchall:
        L.append("- ⚠️ **file_type es solo indicativo acá**: `concept` funciona "
                 "como cajón de sastre y mezcla conceptos doctrinales con "
                 "entidades (FNE y TDLC quedan tipadas `concept`). La señal "
                 "fiable está en las *etiquetas* del top de grado (sección 2): "
                 "los hubs son entidades e instituciones, no conceptos. "
                 "Re-extraer con foco conceptual y tipado explícito (paso B) "
                 "separa ambas cosas.")
    elif first_concept:
        L.append(f"- Primer nodo concepto/rationale en el ranking de grado: "
                 f"posición **#{first_concept}**.")
    L.append("")

    # --- Traza año a año ---
    L.append("## 6. Traza año a año (¿consolida o diversifica?)")
    L.append("")
    by_year_nodes: dict[int, int] = Counter()
    by_year_comms: dict[int, Counter] = {}
    for node in G:
        y = node_year(G.nodes[node])
        if y and 1990 <= y <= date.today().year:
            by_year_nodes[y] += 1
            by_year_comms.setdefault(y, Counter())[
                G.nodes[node].get("community", -1)] += 1
    L.append("| Año | Nodos | Comunidades activas | Entropía norm. |")
    L.append("|---|---|---|---|")
    for y in sorted(by_year_nodes):
        cc = by_year_comms[y]
        _, hn = shannon_entropy(list(cc.values()))
        L.append(f"| {y} | {by_year_nodes[y]} | {len(cc)} | {hn:.2f} |")
    L.append("")
    years = sorted(by_year_nodes)
    if len(years) >= 4:
        half = len(years) // 2
        early = [shannon_entropy(list(by_year_comms[y].values()))[1]
                 for y in years[:half]]
        late = [shannon_entropy(list(by_year_comms[y].values()))[1]
                for y in years[half:]]
        trend = ("**diversificándose**" if np.nanmean(late) > np.nanmean(early)
                 else "**consolidándose**")
        L.append(f"- Tendencia: la entropía temática media pasa de "
                 f"{np.nanmean(early):.2f} (años tempranos) a "
                 f"{np.nanmean(late):.2f} (recientes) → el campo se está {trend}.")
        L.append("- *(Sesgo: refleja la cobertura del corpus por año, no solo "
                 "la actividad real del campo.)*")
    L.append("")
    L.append("---")
    L.append("")
    L.append("_Regenerar tras cada build con: `python code/graph_diagnostics.py`_")
    return "\n".join(L)


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "graphify-out/graph.json")
    if not path.exists():
        sys.exit(f"No existe {path}")
    report = diagnose(path)
    out = path.parent / "GRAPH_DIAGNOSTICS.md"
    out.write_text(report)
    # Resumen breve por stdout (sin volcar todo el reporte)
    for line in report.splitlines():
        if line.startswith("## ") or "⚠️" in line or line.startswith("- σ") \
                or "Tendencia:" in line or "Gini del grado" in line:
            print(line.replace("**", "").replace("- ", "  "))
    print(f"\n→ Reporte completo: {out}")


if __name__ == "__main__":
    main()
