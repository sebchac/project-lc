# Componente RAG — Base de Conocimiento Libre Competencia Chile

> **Documento de diseño (plan escrito, sin ejecución).** v0.1 — 2026-06-11.
> Segundo componente del proyecto dual **graphify + RAG** sobre el mismo corpus.
> Fuente de aprendizaje del stack: Bastián Olea, *"RAG con ragnar"* (https://bastianolea.rbind.io/blog/rag_ragnar/).

---

## 1. Objetivo y encuadre dual

El repositorio ofrece **dos paradigmas de recuperación sobre un mismo corpus jurídico**, complementarios y no redundantes:

| | **graphify** (existente) | **RAG / ragnar** (este componente) |
|---|---|---|
| Pregunta que responde | *Qué* documentos existen y *cómo* se conectan | *Qué dijo* exactamente una fuente sobre un punto |
| Fortaleza | Estructura, enumeración exhaustiva, comunidades, god nodes, contradicciones | Recuperación semántica a nivel de pasaje, **cita textual** |
| Salida típica | Mapas, listas completas, tensiones doctrinales | Considerando/párrafo verbatim con puntero exacto |
| Debilidad | No devuelve el texto literal del considerando | No garantiza exhaustividad ("todas las X") |
| Caso de trabajo | Lista de las 213 sentencias APD (`outputs/lista-apd-tdlc.md`) | Extraer el considerando resolutivo de cada una |

**Tesis del paper dual:** el aporte no es "cómo armar un RAG" (eso lo cubre el post de Olea), sino **el criterio de elección y la complementariedad** sobre datos jurídicos chilenos, con las reglas de autoridad y citación de `../CLAUDE.md` aplicadas a ambas herramientas. La tarea de abuso de posición dominante (APD) es el ejemplo trabajado que recorre todo el artículo.

---

## 2. Principio rector: un corpus, dos consumidores

- **No se duplica el corpus.** Este componente lee desde `../raw-md/` (fuente de verdad única). `raw/` y `raw-md/` siguen siendo intocables.
- Las reglas de dominio de `../CLAUDE.md` (jerarquía de autoridad, citas textuales obligatorias, regla de tensión TDLC/CS, ponderación por centralidad) **se trasladan al prompt de generación** del RAG, no se reinventan.
- Los **metadatos** que enriquecen cada chunk son los mismos que estructuran el grafo (tipo de documento, autoridad, año, rol, track). Eso permite la integración de la §7.

---

## 3. Stack técnico

| Capa | Elección | Notas |
|---|---|---|
| Lenguaje | R (proyecto `rag/`) | Convive con el pipeline Python de graphify; solo comparten archivos de texto |
| Orquestación RAG | `{ragnar}` | `markdown_chunk()`, `ragnar_store_insert()`, `ragnar_store_build_index()`, `ragnar_register_tool_retrieve()` |
| Almacén vectorial | DuckDB | Escala sin problema a cientos de miles de chunks; archivo único `store.duckdb` |
| Embeddings | **A validar** (ver §5) | Candidatos: `nomic-embed-text` (Ollama, local) vs multilingüe español (`multilingual-e5`) vs externo |
| Recuperación léxica | BM25 (vía ragnar) | Para búsqueda híbrida y como baseline sin embeddings |
| Generación (LLM) | Claude vía `{ellmer}` | Modelo a elegir por costo/calidad; el post usa `claude-haiku-4-5` |

**Dependencias R:** `ragnar`, `ellmer`, `duckdb`, `dplyr`, `stringr`, `fs`. **Externas:** Ollama (si embeddings locales) y/o `ANTHROPIC_API_KEY`.

---

## 4. Estructura de directorios (creada — scripts listos, sin ejecutar)

```
rag/
├── README.md            # este documento
├── rag-lc.Rproj
├── .gitignore           # ignora store.duckdb y corpus-norm/ (regenerables)
├── R/
│   ├── config.R         # TODAS las decisiones (modelos, rutas, piloto) en un lugar
│   ├── setup.R          # dependencias + helpers (embedding, metadatos)
│   ├── prompt_rules.R   # reglas de CLAUDE.md como system prompt
│   ├── 00_normalize.R   # preprocesamiento del corpus (ver §5.1)
│   ├── 01_chunk_index.R # chunk → store_insert → build_index
│   └── 02_query.R       # retrieve + register_tool_retrieve + ellmer
├── store.duckdb         # (gitignored) generado por 01
├── corpus-norm/         # (gitignored) markdown normalizado, derivado de raw-md/
└── eval/
    └── consultas_test.md # set de validación con respuesta conocida (§5.2)
```

`outputs/` (compartido en la raíz) recibe las minutas generadas por el RAG, igual que graphify.

### Cómo correr (cuando autorices ejecutar)

> Todos los scripts están **guardados con `if (sys.nframe()==0)`**: `source()`-earlos
> solo define funciones; el trabajo pesado corre únicamente si ejecutas el archivo.
> El modo `PILOTO <- TRUE` de `config.R` limita todo a ~20 sentencias APD.

```r
# 1) Una sola vez: instalar paquetes (editar setup.R, descomentar install.packages)
source("rag/R/setup.R")        # carga librerías y helpers
rag_check_env()                # verifica Ollama / ANTHROPIC_API_KEY

# 2) Indexar la muestra piloto (normaliza + chunk + embeddings + índice)
source("rag/R/01_chunk_index.R")
rag_index(overwrite = TRUE)

# 3a) Evaluar SOLO recuperación (sin costo de LLM) sobre eval/consultas_test.md
source("rag/R/02_query.R")
rag_retrieve("estrangulamiento de márgenes en telecom")

# 3b) Preguntar con respuesta citada
rag_ask("¿Multa impuesta a la ANFP por abuso de posición dominante?")

# 4) Generar una minuta a outputs/ (usa modelo GEN_SMART)
rag_minuta("Síntesis de abuso por estrangulamiento de márgenes (TDLC)",
           file = "minuta-estrangulamiento-rag.md")
```

**Decisiones de modelo:** se cambian en `R/config.R` (`EMBED_MODEL`, `GEN_MODEL`).
Recomendado para el piloto: `EMBED_MODEL = "bge-m3"` (Ollama, gratis) y
`GEN_MODEL = GEN_FAST` (Haiku) para lookups; `GEN_SMART` (Sonnet) para minutas.

> **Advertencia de API.** `ragnar` y `ellmer` evolucionan rápido. Las firmas usadas
> (`ragnar_store_create`, `markdown_chunk`, `ragnar_store_insert`,
> `ragnar_store_build_index`, `ragnar_retrieve`, `ragnar_register_tool_retrieve`,
> `chat_anthropic`) siguen el post de Olea; **verificar contra la versión instalada**
> (`?ragnar::<fn>`) antes de correr. Los puntos a confirmar están marcados con
> `# VERIFICAR` en los scripts.

---

## 5. Decisiones de diseño

### 5.1. Normalización del corpus (riesgo #1 — el más importante)

**Problema constatado:** el OCR de MarkItDown sobre PDF escaneado deja texto cortado por líneas (una cláusula partida en muchas líneas) y *headings* inconsistentes. `markdown_chunk()` se apoya en la jerarquía de títulos para dar contexto a cada fragmento; con el corpus crudo, el chunking saldrá desparejo.

**Plan:**
- Paso `00_normalize.R` previo a la indexación: re-unir líneas dentro de párrafos, colapsar espacios, y **derivar estructura** (encabezados sintéticos por considerando: detectar "PRIMERO:", "VIGÉSIMO:", "SE RESUELVE", "VISTOS", "CONSIDERANDO") para que cada chunk lleve su número de considerando.
- Esto convierte el defecto en metadato útil: cada chunk podrá citar *"Sentencia TDLC N°X, Considerando N°"* — justo lo que exige la regla de citas de `../CLAUDE.md`.
- **No tocar `raw-md/`**: la normalización escribe a un directorio derivado (`rag/corpus-norm/`, gitignored) o se aplica en memoria al indexar.
- *Hallazgo para el paper:* "la preparación del corpus jurídico es el 80% del trabajo y condiciona la calidad del RAG".

### 5.2. Estrategia de chunking

- **Primario:** `markdown_chunk()` sobre el corpus normalizado, chunk por considerando/sección.
- **Fallback:** si la estructura sigue siendo pobre, chunk por tamaño (~800–1200 tokens) con solapamiento (~15%).
- Cada chunk conserva puntero a documento + considerando para trazabilidad.

### 5.3. Embeddings (riesgo #2 — validar, no asumir)

- `nomic-embed-text` es genérico; el corpus es **español jurídico técnico**.
- Plan de validación: indexar la muestra APD con 2–3 modelos (nomic local, multilingüe español, y un externo) y medir recall sobre el set `eval/consultas_test.md`.
- Privacidad: embeddings locales (Ollama) → el corpus no sale de la máquina para indexar. Para jurisprudencia pública es indiferente, pero es un argumento del instructivo frente a herramientas cerradas (NotebookLM).

### 5.4. Metadatos por chunk (clave para la jerarquía de autoridad)

Cada chunk se inserta con: `documento`, `tipo` (sentencia_tdlc / sentencia_cs / resolución / AE / ERN / ICG / guía_fne / DL211), `autoridad` (nivel 1–7 de `../CLAUDE.md`), `año`, `rol`, `track` (A/B/C), `considerando`. Esto permite **filtrar y ponderar** la recuperación por autoridad y recencia (reglas 4 y 5 de `../CLAUDE.md`).

### 5.5. Recuperación

- **Híbrida:** vector (semántica) + BM25 (léxica, captura nombres de partes y roles exactos).
- `top_k` inicial 8–12, con posible reranking.
- Filtros por metadato (p. ej. "solo TDLC+CS post-2018").

### 5.6. Generación y trazabilidad (riesgo #3 — el post NO trae citas)

El post de Olea **no** implementa atribución de fuentes; nosotros la hacemos obligatoria:
- `prompt_rules.R` inyecta como system prompt: citas textuales entre comillas con puntero exacto, jerarquía de autoridad, regla de tensión TDLC/CS, alerta de "no hay precedente en el corpus".
- Toda respuesta cita el chunk recuperado (documento + considerando). Sin pasaje recuperado → no se afirma.

---

## 6. Plan por fases

1. **Fase 0 — piloto** (siguiente paso, cuando autorices ejecutar): `rag/` sobre ~20–30 sentencias APD. Mide chunking, embeddings y calidad de cita. Decide modelo de embeddings.
2. **Fase 1 — Track A completo:** 520 docs ya en markdown (sentencias/resoluciones TDLC+CS, AE, ERN, ICG).
3. **Fase 2 — Track C:** DL 211 + guías FNE como ancla normativa.
4. **Fase 3 — Track B (FNE):** 2.641 investigaciones. Aquí el RAG **brilla** frente al grafo (volumen alto, consultas semánticas), y donde NotebookLM no llega por límite de fuentes.

---

## 7. Integración con graphify (el diferencial del proyecto)

No son dos silos: se potencian.
- **Metadatos compartidos:** mismo esquema de tipo/autoridad/track → consistencia entre grafo y store.
- **Ranking por centralidad:** usar los *god nodes* de `graphify-out/` como señal de *boost* en el reranking del RAG (un considerando de un fallo central pesa más). Implementa la "ponderación por centralidad de nodo" de `../CLAUDE.md` dentro del RAG.
- **Flujo combinado:** graphify *enumera y mapea* (qué fallos, cómo se conectan, dónde hay contradicción) → RAG *extrae el texto* del considerando relevante. La tarea APD es el ejemplo: el grafo dio las 213; el RAG daría el considerando resolutivo de cada una con cita.

---

## 8. Riesgos y mitigaciones (resumen)

| Riesgo | Impacto | Mitigación |
|---|---|---|
| OCR/headings irregulares | Chunks sin contexto, citas imprecisas | `00_normalize.R` + encabezados sintéticos por considerando |
| Embeddings genéricos en español jurídico | Recall bajo | Validar 2–3 modelos sobre set de prueba antes de escalar |
| Sin trazabilidad nativa en ragnar | Respuestas sin cita = inservibles para litigio | Prompt obligado + metadato de puntero por chunk |
| Doble stack R+Python | Curva para el lector del paper | Declararlo; cada herramienta en su capítulo; corpus compartido |
| Confidencialidad (futuro material no público) | Fuga de datos | Embeddings locales (Ollama); documentar en el instructivo |

---

## 9. Decisiones abiertas (a resolver empíricamente en el piloto)

1. Modelo de embeddings definitivo (local vs externo; español).
2. Tamaño/solape de chunk óptimo para texto judicial chileno.
3. Si versionar `store.duckdb` en git o regenerarlo desde `raw-md/`.
4. Modelo de generación (Haiku para costo vs Sonnet/Opus para razonamiento jurídico).
5. Grado de acoplamiento con graphify en Fase 1 (¿el boost por centralidad entra ya o después?).

---

## 10. Qué va al paper dual

- Sección método: dos paradigmas, mismo corpus, criterio de elección.
- Caso trabajado: APD de extremo a extremo (grafo enumera → RAG cita).
- Hallazgo transversal: **preparación del corpus** como cuello de botella real.
- Reproducibilidad: un repo, dos pipelines, instrucciones para que el lector arme cualquiera de los dos según su necesidad.
