# config.R — Decisiones centralizadas del componente RAG
# ---------------------------------------------------------------------------
# Cambiar de modelo de embedding o de generación = editar UNA línea aquí.
# Ningún script ejecuta trabajo pesado al ser "source()"-eado: solo define
# rutas y parámetros. El runner explícito está al final de cada script.
# ---------------------------------------------------------------------------

# --- Rutas (todas relativas a la raíz del repo) ------------------------------
RAG_ROOT      <- here::here("rag")              # requiere paquete {here}
CORPUS_MD     <- here::here("raw-md")           # FUENTE DE VERDAD — no modificar
CORPUS_NORM   <- file.path(RAG_ROOT, "corpus-norm")  # derivado, gitignored
STORE_PATH    <- file.path(RAG_ROOT, "store.duckdb")
OUTPUTS_DIR   <- here::here("outputs")

# --- Modo piloto -------------------------------------------------------------
# TRUE  = indexa solo la muestra APD (rápido, barato, para validar).
# FALSE = corpus completo (Track A; luego C y B por fases).
PILOTO        <- TRUE

# Muestra del piloto: sentencias APD ya clasificadas en outputs/lista-apd-tdlc.md
# Se usan como set de validación porque ya conocemos el resultado correcto.
PILOTO_SENTENCIAS <- c(
  "Sentencia_173_2020", "Sentencia_178_2021", "Sentencia_184_2022",
  "Sentencia_76_2008",  "Sentencia_100_2010", "Sentencia_132_2013",
  "Sentencia_55_2007",  "Sentencia_53_2007",  "Sentencia_75_2008",
  "Sentencia_156_2017", "Sentencia_158_2017", "Sentencia_174_2020",
  "Sentencia_189_2023", "Sentencia_195_2024", "Sentencia_206_2025",
  "Sentencia_46_2006",  "Sentencia_80_2009",  "Sentencia_164_2018",
  "Sentencia_186_2023", "Sentencia_N°_191_2024"
)

# --- Modelo de EMBEDDING --------------------------------------------------
# Cambiar EMBED_PROFILE para alternar entre modelos (para el benchmark).
# Los perfiles están definidos abajo; solo editar esta línea.
#
#   "bm25"    — sin vectores, búsqueda léxica BM25. Cero dependencias.
#               Ideal para validar el pipeline antes de instalar Ollama.
#   "bge_m3"  — bge-m3 vía Ollama (local, gratis). Recomendado como default.
#               Instalar: ollama pull bge-m3
#   "mxbai"   — mxbai-embed-large vía Ollama. Alternativa robusta en español.
#               Instalar: ollama pull mxbai-embed-large
#   "voyage"  — voyage-law-2 vía API (pago, especializado en texto jurídico).
#               Requiere: VOYAGE_API_KEY en el entorno.
#
EMBED_PROFILE <- "bm25"    # <- CAMBIA AQUÍ para cambiar de modelo

embed_profiles <- list(
  bm25   = list(backend = "bm25",   model = NA_character_),
  bge_m3 = list(backend = "ollama", model = "bge-m3"),
  mxbai  = list(backend = "ollama", model = "mxbai-embed-large"),
  voyage = list(backend = "voyage", model = "voyage-law-2")
)

EMBED_BACKEND <- embed_profiles[[EMBED_PROFILE]]$backend
EMBED_MODEL   <- embed_profiles[[EMBED_PROFILE]]$model

# --- Modelo de GENERACIÓN (escalonado por tarea) -----------------------------
# Barato para lookups; fuerte para minutas; tope para grado-paper.
GEN_FAST   <- "claude-haiku-4-5"    # extracción de considerandos, Q&A simple
GEN_SMART  <- "claude-sonnet-4-6"   # minutas, tensión TDLC/CS, contradicciones
GEN_TOP    <- "claude-opus-4-8"     # síntesis grado-paper, registro de hipótesis
GEN_MODEL  <- GEN_FAST              # default del runner interactivo

# --- Parámetros de recuperación ----------------------------------------------
TOP_K          <- 10        # candidatos recuperados por consulta
USE_HYBRID     <- TRUE      # vector + BM25 (nombres de partes, "Considerando 14°")
CHUNK_TOKENS   <- 1000      # tamaño objetivo de chunk (fallback por tamaño)
CHUNK_OVERLAP  <- 0.15      # solape relativo

# --- Chequeo de entorno (no ejecuta indexación) ------------------------------
rag_check_env <- function() {
  msg <- c()
  if (EMBED_BACKEND == "ollama" &&
      nzchar(Sys.which("ollama")) == FALSE)
    msg <- c(msg, "Ollama no está en PATH (necesario para embeddings locales).")
  if (grepl("^claude", GEN_MODEL) &&
      !nzchar(Sys.getenv("ANTHROPIC_API_KEY")))
    msg <- c(msg, "Falta ANTHROPIC_API_KEY para la generación con Claude.")
  if (EMBED_BACKEND == "voyage" && !nzchar(Sys.getenv("VOYAGE_API_KEY")))
    msg <- c(msg, "Falta VOYAGE_API_KEY.")
  if (EMBED_BACKEND == "openai" && !nzchar(Sys.getenv("OPENAI_API_KEY")))
    msg <- c(msg, "Falta OPENAI_API_KEY.")
  if (length(msg)) {
    warning(paste(msg, collapse = "\n"))
    invisible(FALSE)
  } else {
    message("Entorno OK: backend=", EMBED_BACKEND, " embed=", EMBED_MODEL,
            " gen=", GEN_MODEL)
    invisible(TRUE)
  }
}
