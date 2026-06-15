# Cerebro digital para la investigación en libre competencia chilena

Base de conocimiento sobre jurisprudencia y doctrina de libre competencia en Chile (TDLC, Corte Suprema, FNE). Construida con dos instrumentos complementarios sobre un corpus de ~520 documentos:

- **Grafo de conocimiento** (Graphify): mapea conceptos, relaciones y comunidades temáticas. Revela nodos centrales, contradicciones entre autoridades y silencios doctrinales.
- **Sistema RAG vectorial** (ragnar + bge-m3 + DuckDB): recupera el considerando exacto que respalda un argumento, con cita literal y referencia precisa.

El pipeline completo es replicable, de código abierto y adaptable a cualquier corpus jurídico. Ver el paper en `paper/` para la descripción metodológica completa.

---

## Estructura del repositorio

```
raw/              — PDFs fuente por tipo de documento (no versionados)
raw-md/           — Markdown producido con MarkItDown desde raw/ (no versionado)
graphify-out/
  wiki/           — Wiki temática generada por Graphify (184 artículos)
  notes/          — Notas personales del investigador (no son fuente de autoridad)
  GRAPH_REPORT.md — Diagnóstico de red del grafo
rag/
  R/              — Scripts del pipeline RAG (normalización, indexación, consulta)
  eval/           — Set de validación con 10 consultas y respuestas esperadas
  ask.sh          — Interfaz de consulta desde terminal
code/             — Scripts de descarga y conversión de PDFs
paper/            — Artículo de investigación (LaTeX)
outputs/          — Minutas y documentos generados
```

---

## Corpus

**Track A — Jurisprudencia (520 docs procesados)**

| Carpeta en `raw-md/` | Tipo | N° |
|---|---|---|
| `sentencias-tdlc-md/` | Sentencias TDLC | 212 |
| `sentencias-cs-md/` | Sentencias Corte Suprema | 128 |
| `resoluciones-tdlc-md/` | Resoluciones TDLC | 89 |
| `resoluciones-cs-md/` | Resoluciones Corte Suprema | 13 |
| `ae-tdlc-md/` | Acuerdos Extrajudiciales | 38 |
| `ern-tdlc-md/` | Expedientes de Recomendación Normativa | 22 |
| `icg-tdlc-md/` | Instrucciones de Carácter General | 9 |

**Track C — Normativa de base**

| Carpeta en `raw-md/` | Tipo | N° |
|---|---|---|
| `normativa-fusiones-fne-md/` | Guías y reglamentos FNE | 8 |
| `normativa-general-md/` | DL 211 refundido | 1 |

Los PDFs fuente (`raw/`) y los Markdown (`raw-md/`) no se incluyen en el repositorio por tamaño. Los scripts de descarga están en `code/`.

---

## Replicar el pipeline

### Requisitos

- Python ≥ 3.10: `pip install 'markitdown[pdf]'`
- R ≥ 4.3: paquetes `ragnar`, `ellmer`, `duckdb`, `dplyr`, `stringr`, `fs`, `here`, `purrr`, `readr`
- [Claude Code](https://claude.ai/code) (para el grafo con Graphify)
- [Ollama](https://ollama.com) + `ollama pull bge-m3` (para embeddings RAG)

### Paso 1 — Recolectar y convertir

```bash
python3 code/batch_convert.py        # raw/ → raw-md/
# Para PDFs escaneados:
python3 code/batch_convert_ocr.py
```

### Paso 2 — Construir el grafo (dentro de Claude Code)

```
/graphify raw-md/
```

### Paso 3 — Indexar el RAG

```bash
# Con ollama serve corriendo en background:
Rscript rag/R/00_normalize.R     # raw-md/ → rag/corpus-norm/
Rscript rag/R/01_chunk_index.R   # chunk + bge-m3 → rag/store.duckdb
```

### Paso 4 — Consultar

```bash
# Desde la terminal (usa suscripción Claude.ai, sin API key):
./rag/ask.sh "¿Qué estándar aplicó el TDLC para condenar por colusión?"

# O en R (usa ANTHROPIC_API_KEY):
source("rag/R/02_query.R")
rag_ask("¿Cuándo ha absuelto el TDLC por insuficiencia probatoria en colusión?")
```

---

## Adaptar a otro corpus

1. Reemplaza los PDFs en `raw/` con los de tu campo.
2. Edita `CLAUDE.md`: ajusta la jerarquía de autoridad, las anclas conceptuales y las reglas de respuesta para tu dominio.
3. Corre el pipeline desde el Paso 1.

El archivo `CLAUDE.md` es la pieza central del diseño. El Anexo A del paper incluye una versión con `[placeholders]` para que el lector complete con sus propios datos.

---

## Paper

`paper/main.tex` contiene el artículo de investigación. Para compilar:

```bash
latexmk -pdf -output-directory=paper/build paper/main.tex
```

---

## Licencia

MIT — ver [LICENSE](LICENSE).

## Autor

Sebastián Chacón Salinas — Facultad de Economía y Negocios, Universidad de Chile  
[schacon@fen.uchile.cl](mailto:schacon@fen.uchile.cl)
