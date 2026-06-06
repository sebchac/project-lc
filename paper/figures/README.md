# Figuras para el artículo

## Figura 1 — pipeline_diagram.pdf
**Descripción:** Diagrama de flujo horizontal del pipeline de cinco pasos.

Contenido sugerido:
- Cinco cajas en línea: [Paso 1: Recolectar] → [Paso 2: Convertir con MarkItDown]
  → [Paso 3: Grafo con Graphify] → [Paso 4: Wiki] → [Paso 5: Consultar]
- Una flecha de retroalimentación desde "Mantenimiento continuo" que vuelve al
  Paso 1
- Iconos o logos de las herramientas bajo cada caja (Python, MarkItDown, Graphify,
  Obsidian, Claude Code)

Herramienta sugerida: draw.io, Inkscape, o LaTeX/TikZ.

---

## Figura 2 — corpus_structure.pdf
**Descripción:** Diagrama de la estructura de tres tracks del corpus.

Contenido sugerido:
- Tres columnas verticales etiquetadas "Track A — Jurisprudencia",
  "Track B — Enforcement FNE", "Track C — Normativa de base"
- En Track A: subcarpetas con número de documentos (sentencias TDLC 212,
  sentencias CS 128, resoluciones TDLC 89, etc.)
- En Track B: subcarpetas FNE con 2.641 documentos pendientes (mostrar en gris
  o con indicador "pendiente")
- En Track C: DL 211 + guías FNE

---

## Figura 3 — graph_screenshot.png
**Descripción:** Captura de pantalla del grafo interactivo (graph.html) generado
por Graphify sobre el corpus chileno.

Obtener: abrir graphify-out/graph.html en el navegador, hacer zoom para mostrar
los clusters principales, capturar pantalla con los nodos más conectados visibles.

Indicar en el pie de figura: número de nodos, aristas, comunidades, y fecha de
la extracción.

---

## Figura 4 — wiki_obsidian.png
**Descripción:** Captura de la vista de grafo de Obsidian mostrando la wiki de
libre competencia. Cada nodo es un artículo temático (ej. colusión, mercado
relevante, etc.). Las aristas son hipervínculos entre páginas.

Obtener: abrir la carpeta graphify-out/wiki/ como vault en Obsidian, activar la
vista de grafo (Graph view).

---

## Figura 5 — wiki_article_example.png
**Descripción:** Captura de un artículo de wiki en Obsidian mostrando la
estructura fija: (1) Resumen, (2) Jurisprudencia, (3) Enforcement FNE,
(4) Casos vinculados, (5) Lo que las fuentes no abordan.

Sugerencia: usar el artículo sobre "colusión" o "mercado relevante" que tenga
contenido rico en los cinco apartados.
