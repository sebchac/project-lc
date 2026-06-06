#!/usr/bin/env python3
"""Re-extracción del grafo con foco en los conceptos ancla (paso B).

Parchea en tiempo de ejecución el prompt de extracción de graphify
(`llm._EXTRACTION_SYSTEM`) para inyectarle contexto de dominio y los 30
conceptos ancla del CLAUDE.md con IDs canónicos estables, de modo que cada
documento que discute un concepto se conecte al MISMO nodo-concepto. Así la
centralidad pasa de reflejar "quién litigó" (entidades) a "qué doctrina es
central" (conceptos).

NO modifica el paquete global de graphify; el parche vive sólo en este proceso.

Uso:
    python code/reextract_concepts.py --dry-run        # muestra estratificada, no toca el grafo
    python code/reextract_concepts.py --dry-run -n 6   # N docs
    python code/reextract_concepts.py --full           # corpus completo raw-md/, reconstruye el grafo

Requiere GEMINI_API_KEY en el entorno.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

from graphify import llm
from graphify.extract import collect_files

MODEL = "gemini-3-flash-preview"
CORPUS = Path("raw-md")

# IDs canónicos estables — mismo id en todos los documentos => fusión natural.
ANCHORS = """
  concept_colusion · concept_bid_rigging · concept_abuso_posicion_dominante
  concept_precio_predatorio · concept_negativa_venta · concept_margin_squeeze
  concept_operacion_concentracion · concept_mercado_relevante
  concept_mercado_geografico · concept_poder_mercado · concept_hhi
  concept_barreras_entrada · concept_estandar_prueba · concept_prueba_indirecta
  concept_eficiencias · concept_teoria_del_dano · concept_remedio_estructural
  concept_condicion_conductual · concept_multa · concept_acuerdo_extrajudicial
  concept_desinversion · concept_nexo_causal · concept_cuantificacion_dano
  concept_dano_emergente_lucro_cesante · concept_before_after_did
  concept_modelo_contrafactual · concept_dl211 · concept_articulo_3_dl211
  concept_umbrales_notificacion · concept_argumento_rechazado
""".strip()

ADDENDUM = f"""

────────────────────────────────────────────────────────────────────
DOMINIO: corpus de libre competencia chilena (sentencias y resoluciones del
TDLC y de la Corte Suprema, Acuerdos Extrajudiciales, Expedientes de
Recomendación Normativa, Instrucciones de Carácter General, DL 211 y guías de
la FNE). Texto en español.

CONCEPTOS ANCLA — PRIORIDAD MÁXIMA. Cuando un documento discuta SUSTANTIVAMENTE
alguno de estos conceptos, DEBES:
  1. emitir un nodo con el ID CANÓNICO EXACTO de la lista (file_type "concept"),
     usando SIEMPRE el mismo id para que el concepto se fusione entre documentos;
  2. emitir una arista documento→concepto con relation "references",
     confidence "EXTRACTED", confidence_score 1.0.

IDs canónicos (no inventes variantes; si el concepto no está en la lista pero es
claramente uno de ellos, usa el id de la lista):
{ANCHORS}

REGLAS:
- Los conceptos ancla son nodos de primera clase. NO los degrades a atributos.
- El `label` de cada concepto ancla debe ser su nombre natural en español
  (p.ej. id `concept_mercado_relevante` → label "Mercado Relevante").
- Las partes, empresas, personas e instituciones siguen siendo nodos, pero la
  PRIORIDAD es conectar cada documento con los conceptos que invoca.
- Conecta también concepto↔concepto con relation "conceptually_related_to"
  cuando el documento los relacione explícitamente (p.ej. mercado relevante →
  poder de mercado).
- NO uses file_type "concept" para entidades nombradas (empresas, personas,
  instituciones como FNE, TDLC, Corte Suprema): ésas son nodos, pero NO son
  conceptos doctrinales. file_type "concept" se reserva EXCLUSIVAMENTE para
  conceptos jurídico-económicos.
────────────────────────────────────────────────────────────────────
"""


def patch_prompt() -> None:
    if "CONCEPTOS ANCLA" not in llm._EXTRACTION_SYSTEM:
        llm._EXTRACTION_SYSTEM = llm._EXTRACTION_SYSTEM + ADDENDUM


def stratified_sample(n: int) -> list[Path]:
    """Un archivo de cada subcarpeta clave hasta llegar a n."""
    subdirs = ["sentencias-tdlc-md", "sentencias-cs-md", "resoluciones-tdlc-md",
               "normativa-general-md", "ae-tdlc-md", "icg-tdlc-md"]
    picked: list[Path] = []
    for sd in subdirs:
        files = sorted((CORPUS / sd).glob("*.md"))
        if files:
            picked.append(files[0])
        if len(picked) >= n:
            break
    return picked[:n]


def report_concepts(result: dict) -> None:
    nodes = result.get("nodes", [])
    edges = result.get("edges", result.get("links", []))
    concepts = [n for n in nodes if n.get("file_type") == "concept"]
    anchor_ids = {a.strip() for a in ANCHORS.replace("·", " ").split()}
    anchor_hits = [n for n in concepts if n["id"] in anchor_ids]
    doc2concept = [e for e in edges
                   if any(e.get("target") == n["id"] for n in concepts)]

    print(f"\n{'='*60}")
    print(f"Documentos procesados: {len({n.get('source_file') for n in nodes})}")
    print(f"Nodos totales: {len(nodes)} · aristas: {len(edges)}")
    print(f"Nodos concepto: {len(concepts)} "
          f"(de los cuales {len(anchor_hits)} son anclas canónicas)")
    print(f"Aristas hacia conceptos: {len(doc2concept)}")
    print(f"\nAnclas canónicas detectadas (frecuencia como target de arista):")
    tgt = Counter(e.get("target") for e in edges if e.get("target") in anchor_ids)
    for cid, c in tgt.most_common():
        label = next((n.get("label") for n in concepts if n["id"] == cid), cid)
        print(f"  {c:2d}  {cid:38s} {label}")
    non_anchor = [n for n in concepts if n["id"] not in anchor_ids]
    if non_anchor:
        print(f"\nConceptos NO-ancla (ejemplos, deberían ser pocos):")
        for n in non_anchor[:12]:
            print(f"  - {n['id']}  ({n.get('label')})")
    print(f"\nTokens: {result.get('input_tokens', 0):,} in / "
          f"{result.get('output_tokens', 0):,} out")
    print('='*60)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--rebuild-derived", action="store_true",
                    help="recalcula análisis/labels/wiki/html desde graph.json "
                         "existente, sin re-extraer (gratis)")
    ap.add_argument("-n", type=int, default=5, help="docs en dry-run")
    args = ap.parse_args()

    if args.rebuild_derived:
        rebuild_derived()
        return
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("Falta GEMINI_API_KEY en el entorno.")
    if not (args.dry_run or args.full):
        sys.exit("Especifica --dry-run, --full o --rebuild-derived.")

    patch_prompt()

    if args.dry_run:
        files = stratified_sample(args.n)
        print(f"DRY-RUN · modelo {MODEL} · {len(files)} documentos:")
        for f in files:
            print(f"  - {f}")
        result = llm.extract_corpus_parallel(
            files, backend="gemini", model=MODEL, root=Path("."),
            max_concurrency=4)
        report_concepts(result)
        Path("/tmp/reextract_dryrun.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2))
        print("\nResultado completo en /tmp/reextract_dryrun.json")
        print("Revisa y, si convence, corre:  "
              "python code/reextract_concepts.py --full")
        return

    run_full()


def run_full() -> None:
    import shutil
    import subprocess
    from datetime import datetime

    from graphify import analyze, build, cluster, detect as detect_mod, report
    from graphify.dedup import deduplicate_entities
    from graphify.export import to_json

    out = Path("graphify-out")

    # 1. Respaldo fuera del repo (sin ensuciar git)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = Path(f"/tmp/project-lc-graph-backup-{ts}")
    backup.mkdir(parents=True, exist_ok=True)
    for item in ["graph.json", "GRAPH_REPORT.md", "GRAPH_DIAGNOSTICS.md"]:
        if (out / item).exists():
            shutil.copy2(out / item, backup / item)
    if (out / "wiki").exists():
        shutil.copytree(out / "wiki", backup / "wiki", dirs_exist_ok=True)
    print(f"[1/7] Respaldo en {backup}")

    # 2. Extracción Gemini con prompt parcheado
    files = collect_files(CORPUS)
    print(f"[2/7] Extrayendo {len(files)} documentos con {MODEL} "
          f"(esto toma varios minutos)…")
    extraction = llm.extract_corpus_parallel(
        files, backend="gemini", model=MODEL, root=Path("."),
        max_concurrency=4)
    nodes, edges = extraction["nodes"], extraction["edges"]
    print(f"      extraídos {len(nodes)} nodos, {len(edges)} aristas · "
          f"{extraction.get('input_tokens',0):,} in / "
          f"{extraction.get('output_tokens',0):,} out tokens")

    # 3. Clustering inicial → mapa nodo→comunidad para el dedup
    G0 = build.build_from_json({"nodes": nodes, "edges": edges})
    comm0 = cluster.cluster(G0)
    node_to_comm = {nid: c for c, members in comm0.items() for nid in members}

    # 4. Dedup nativo OBLIGATORIO (lección registrada en memoria)
    nodes, edges = deduplicate_entities(nodes, edges, communities=node_to_comm)
    # No hay código en el corpus: cualquier file_type "code" es un error de
    # clasificación de entidades → reasignar a "document".
    fixed = 0
    for n in nodes:
        if n.get("file_type") == "code":
            n["file_type"] = "document"
            fixed += 1
    print(f"[3/7] Dedup → {len(nodes)} nodos, {len(edges)} aristas "
          f"({fixed} 'code'→'document')")

    # 5. Build final + clustering + análisis
    G = build.build_from_json({"nodes": nodes, "edges": edges})
    communities = cluster.cluster(G)
    cohesion = cluster.score_all(G, communities)
    gods = analyze.god_nodes(G)
    surprises = analyze.surprising_connections(G, communities)
    print(f"[4/7] Grafo: {G.number_of_nodes()} nodos, "
          f"{G.number_of_edges()} aristas, {len(communities)} comunidades")

    # 6. Etiquetar comunidades por su nodo de mayor grado (auto-label)
    deg = dict(G.degree())
    labels = {}
    for cid, members in communities.items():
        top = max(members, key=lambda x: deg.get(x, 0)) if members else None
        labels[cid] = (G.nodes[top].get("label", f"Community {cid}")[:48]
                       if top else f"Community {cid}")
    (out / ".graphify_labels.json").write_text(
        json.dumps({str(k): v for k, v in labels.items()}, ensure_ascii=False))

    # 7. Reporte + export grafo
    detection = detect_mod.detect(CORPUS)
    questions = analyze.suggest_questions(G, communities, labels)
    tokens = {"input": extraction.get("input_tokens", 0),
              "output": extraction.get("output_tokens", 0)}
    rep = report.generate(G, communities, cohesion, labels, gods, surprises,
                          detection, tokens, str(CORPUS),
                          suggested_questions=questions)
    (out / "GRAPH_REPORT.md").write_text(rep)
    to_json(G, communities, str(out / "graph.json"), force=True)
    # Análisis para que `graphify export wiki` no se niegue a generar
    (out / ".graphify_analysis.json").write_text(json.dumps({
        "communities": {str(k): v for k, v in communities.items()},
        "cohesion": {str(k): v for k, v in cohesion.items()},
        "gods": gods, "surprises": surprises, "questions": questions,
    }, ensure_ascii=False))
    print("[5/7] graph.json, GRAPH_REPORT.md y análisis regenerados")

    # Wiki + HTML vía CLI de graphify (consistente con cómo se generaron antes)
    print("[6/7] Regenerando wiki y HTML…")
    subprocess.run(["graphify", "export", "wiki"], check=False)
    subprocess.run(["graphify", "export", "html"], check=False)

    # Diagnóstico comparativo
    print("[7/7] Diagnóstico:")
    subprocess.run([sys.executable, "code/graph_diagnostics.py"], check=False)
    print(f"\n✅ Listo. Respaldo del grafo anterior en {backup}")


def rebuild_derived() -> None:
    """Reconstruye análisis/labels/reporte/wiki/html desde el graph.json
    existente, sin re-extraer. Repara también el file_type 'code'→'document'."""
    import subprocess

    from networkx.readwrite import json_graph
    from graphify import analyze, cluster, detect as detect_mod, report
    from graphify.export import to_json

    out = Path("graphify-out")
    gpath = out / "graph.json"
    raw = json.loads(gpath.read_text())

    # Reparar file_type: no hay código en el corpus.
    fixed = sum(1 for n in raw["nodes"] if n.get("file_type") == "code")
    for n in raw["nodes"]:
        if n.get("file_type") == "code":
            n["file_type"] = "document"
    print(f"file_type 'code'→'document': {fixed} nodos")

    G = json_graph.node_link_graph(raw, edges="links")

    # Comunidades desde el atributo ya presente en los nodos
    communities: dict[int, list[str]] = {}
    for nid, d in G.nodes(data=True):
        communities.setdefault(int(d.get("community", -1)), []).append(nid)

    cohesion = cluster.score_all(G, communities)
    gods = analyze.god_nodes(G)
    surprises = analyze.surprising_connections(G, communities)

    deg = dict(G.degree())
    labels = {}
    for cid, members in communities.items():
        top = max(members, key=lambda x: deg.get(x, 0)) if members else None
        labels[cid] = (G.nodes[top].get("label", f"Community {cid}")[:48]
                       if top else f"Community {cid}")
    questions = analyze.suggest_questions(G, communities, labels)

    (out / ".graphify_labels.json").write_text(
        json.dumps({str(k): v for k, v in labels.items()}, ensure_ascii=False))
    (out / ".graphify_analysis.json").write_text(json.dumps({
        "communities": {str(k): v for k, v in communities.items()},
        "cohesion": {str(k): v for k, v in cohesion.items()},
        "gods": gods, "surprises": surprises, "questions": questions,
    }, ensure_ascii=False))

    detection = detect_mod.detect(CORPUS)
    rep = report.generate(G, communities, cohesion, labels, gods, surprises,
                          detection, {"input": 0, "output": 0}, str(CORPUS),
                          suggested_questions=questions)
    (out / "GRAPH_REPORT.md").write_text(rep)
    to_json(G, communities, str(gpath), force=True)
    print(f"Regenerados: análisis, labels, GRAPH_REPORT.md, graph.json "
          f"({G.number_of_nodes()} nodos, {len(communities)} comunidades)")

    subprocess.run(["graphify", "export", "wiki"], check=False)
    subprocess.run(["graphify", "export", "html"], check=False)
    subprocess.run([sys.executable, "code/graph_diagnostics.py"], check=False)


if __name__ == "__main__":
    main()
