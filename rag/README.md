# Componente RAG — Base de Conocimiento Libre Competencia Chile

Segundo componente del proyecto dual **graphify + RAG** sobre el mismo corpus de
~520 documentos (Tracks A y C). Fuente de referencia del stack: Bastián Olea,
*"RAG con ragnar"* (https://bastianolea.rbind.io/blog/rag_ragnar/).

---

## 1. Qué hace y qué no hace

| | **graphify** | **RAG (este componente)** |
|---|---|---|
| Pregunta que responde | *Qué* documentos existen y *cómo* se conectan | *Qué dijo exactamente* una fuente sobre un punto |
| Fortaleza | Estructura, comunidades, god nodes, contradicciones | Cita textual con puntero al considerando exacto |
| Debilidad | No devuelve el texto literal del considerando | No garantiza exhaustividad ("todas las X") |

El aporte no es "cómo armar un RAG" sino el criterio de elección y la
complementariedad sobre datos jurídicos chilenos, con las reglas de autoridad y
citación de `../CLAUDE.md` aplicadas a ambos instrumentos.

---

## 2. Principio rector: un corpus, dos consumidores

- **No se duplica el corpus.** Lee desde `../raw-md/` (fuente de verdad única).
- Las reglas de `../CLAUDE.md` (jerarquía de autoridad, citas textuales, regla
  de tensión TDLC/CS) se trasladan al prompt de generación en `R/prompt_rules.R`.
- Los metadatos por chunk (tipo, autoridad, año, track) son los mismos que
  estructuran el grafo, lo que permite integración futura.

---

## 3. Stack técnico

| Capa | Elección | Notas |
|---|---|---|
| Lenguaje | R | Convive con el pipeline Python de graphify |
| Orquestación RAG | `{ragnar}` v0.3.0 | `markdown_chunk()`, `ragnar_store_insert()`, `ragnar_store_build_index()` |
| Almacén vectorial | DuckDB | Archivo único portable (`store.duckdb`) |
| Embeddings | **bge-m3** (BAAI, vía Ollama) | Multilingüe, 8.192 tokens, local y gratuito |
| Recuperación | Híbrida: VSS + BM25 | VSS para consultas semánticas; BM25 para nombres de partes y roles |
| Generación (LLM) | Claude vía `{ellmer}` o CLI | Ver modelos escalonados en `R/config.R` |

**Dependencias R:** `ragnar`, `ellmer`, `duckdb`, `dplyr`, `stringr`, `fs`,
`here`, `purrr`, `readr`.  
**Externas:** Ollama + `ollama pull bge-m3` y/o `ANTHROPIC_API_KEY`.

---

## 4. Estructura de directorios

```
rag/
├── README.md
├── rag-lc.Rproj
├── .gitignore           # ignora store.duckdb y corpus-norm/ (regenerables)
├── R/
│   ├── config.R         # todas las decisiones (modelos, rutas, top_k) en un lugar
│   ├── setup.R          # dependencias + helpers (embedding, metadatos)
│   ├── prompt_rules.R   # reglas de CLAUDE.md como system prompt
│   ├── 00_normalize.R   # raw-md/ → corpus-norm/ (limpieza + headings sintéticos)
│   ├── 01_chunk_index.R # chunk → store_insert → build_index
│   └── 02_query.R       # retrieve + register_tool_retrieve + ellmer
├── store.duckdb         # (gitignored) generado por 01_chunk_index.R
├── corpus-norm/         # (gitignored) markdown normalizado, derivado de raw-md/
├── eval/
│   └── consultas_test.md  # 2 consultas de referencia con resultado esperado
└── ask.sh               # interfaz de consulta desde terminal
```

---

## 5. Cómo correr

```bash
# Requisito previo: Ollama corriendo con bge-m3
ollama serve          # en una pestaña separada
ollama pull bge-m3    # solo la primera vez (~1.2 GB)

# Desde la raíz del repositorio:
Rscript rag/R/00_normalize.R     # normaliza raw-md/ → rag/corpus-norm/
Rscript rag/R/01_chunk_index.R   # indexa con bge-m3 → rag/store.duckdb

# Consultar
./rag/ask.sh "¿Qué estándar aplicó el TDLC para condenar por colusión?"
./rag/ask.sh "tu pregunta" 20    # top_k=20 para documentos largos
```

El primer `source()` de cada script solo carga funciones. El trabajo pesado
corre únicamente si ejecutas el archivo directamente (`Rscript`) o si llamas
explícitamente a `rag_index()` / `rag_ask()` en la consola R.

---

## 6. Decisiones de diseño clave

### Normalización del corpus (riesgo #1)

El OCR de MarkItDown sobre PDFs escaneados deja dos problemas que afectan el
chunking: espacios dobles internos y párrafos partidos en líneas de 60–80
caracteres. `00_normalize.R` los resuelve en tres pasos: (A) colapsa espacios
dobles, (B) re-une líneas de párrafo, (C) inserta prefijos `##`/`###` en los
marcadores estructurales del fallo (VISTOS, CONSIDERANDO, numerales ordinales
en tres estilos distintos según el período). La normalización es token-fiel:
todos los términos del original aparecen en el mismo orden.

### Embeddings bge-m3 y búsqueda híbrida

bge-m3 (BAAI) es multilingüe (100+ idiomas), soporta hasta 8.192 tokens y corre
localmente vía Ollama sin costo de API. La búsqueda híbrida (VSS + BM25) combina
recuperación semántica para conceptos abstractos (estándar de prueba, nexo causal)
con recuperación léxica para términos exactos (número de rol, artículo del DL 211,
nombres de partes).

### Trazabilidad obligatoria

`ragnar::read_as_markdown(path)` fija el atributo `@document@origin` en el
objeto `MarkdownDocumentChunks`. Sin esto, el campo de origen de todos los
fragmentos queda vacío. `prompt_rules.R` inyecta como system prompt la
obligación de citar considerandos textuales — sin fragmento recuperado, no
se afirma.

### Fallback para replicadores sin Ollama

Cambiar `EMBED_PROFILE <- "bm25"` en `config.R` activa búsqueda léxica pura
sin dependencia de Ollama. El store se reconstruye con `rag_index(overwrite=TRUE)`.

---

## 7. Integración con graphify

Los dos instrumentos se complementan sobre el mismo corpus:

- **graphify enumera y mapea** → qué fallos existen sobre un tema, cómo se
  conectan, dónde hay contradicciones entre niveles de autoridad.
- **RAG extrae el texto** → el considerando exacto, con cita literal.

Los metadatos compartidos (tipo, autoridad, track) permiten en el futuro usar
los *god nodes* del grafo como señal de boost en el reranking del RAG.
