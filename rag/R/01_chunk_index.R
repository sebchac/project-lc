# 01_chunk_index.R — Chunking, inserción e índice en DuckDB
# ---------------------------------------------------------------------------
# Pipeline: corpus-norm/ -> markdown_chunk() -> ragnar_store_insert()
#           -> ragnar_store_build_index()
#
# Modos de embedding (controlados desde config.R con EMBED_PROFILE):
#   "bm25"   — sin vectores, búsqueda léxica. Cero dependencias extra.
#   "bge_m3" — embeddings locales vía Ollama (requiere: ollama serve)
#   "mxbai"  — embeddings locales vía Ollama (alternativa)
#   "voyage" — embeddings remotos via voyage-law-2 (requiere VOYAGE_API_KEY)
#
# VERIFICAR firmas de ragnar contra la versión instalada:
#   ?ragnar::ragnar_store_create
#   ?ragnar::markdown_chunk
#   ?ragnar::ragnar_store_insert
#   ?ragnar::ragnar_store_build_index
# ---------------------------------------------------------------------------

source(here::here("rag", "R", "setup.R"))
source(here::here("rag", "R", "00_normalize.R"))

utils::globalVariables(c(
  "EMBED_PROFILE", "EMBED_MODEL", "EMBED_BACKEND",
  "STORE_PATH", "CORPUS_NORM",
  "rag_embed_fn", "rag_meta_from_path", "rag_check_env",
  "normalize_corpus"
))

# ---------------------------------------------------------------------------
# Crea (o recrea) el store DuckDB
# embed=NULL activa modo BM25 puro (sin vectores)
# ---------------------------------------------------------------------------
rag_build_store <- function(overwrite = FALSE) {
  if (fs::file_exists(STORE_PATH) && !overwrite)
    stop("Ya existe ", STORE_PATH, ". Usa overwrite=TRUE para recrear.")
  if (fs::file_exists(STORE_PATH))
    fs::file_delete(STORE_PATH)

  embed_fn <- rag_embed_fn()   # NULL si EMBED_PROFILE == "bm25"

  message(sprintf(
    "Creando store  |  perfil: %s  |  embed: %s",
    EMBED_PROFILE,
    if (is.null(embed_fn)) "BM25 (sin vectores)" else EMBED_MODEL
  ))

  ragnar::ragnar_store_create(
    location   = STORE_PATH,
    embed      = embed_fn
  )
}

# ---------------------------------------------------------------------------
# Chunkea un archivo normalizado y adjunta sus metadatos por chunk
# ---------------------------------------------------------------------------
rag_chunk_file <- function(path_norm) {
  meta   <- rag_meta_from_path(path_norm)

  # read_as_markdown fija @document@origin = path_norm automáticamente.
  # ragnar v2 extrae origin desde ese atributo, no desde columnas del tibble.
  doc    <- ragnar::read_as_markdown(as.character(path_norm))
  chunks <- ragnar::markdown_chunk(doc)

  # Metadatos extra: ignorados por ragnar_store_insert (schema fijo),
  # pero útiles si en el futuro se extiende el store o se hace un join externo.
  considerando <- stringr::str_extract(
    chunks[["context"]] %||% chunks[["text"]],
    "(?:##+ )(.+?)(?=\n|$)"
  )

  dplyr::mutate(
    chunks,
    documento    = meta$documento,
    tipo         = meta$tipo,
    autoridad    = meta$autoridad,
    track        = meta$track,
    anio         = meta$anio,
    rol          = meta$rol,
    considerando = considerando
  )
}

# ---------------------------------------------------------------------------
# Indexa el corpus piloto (o completo según config.R)
# ---------------------------------------------------------------------------
rag_index <- function(overwrite = FALSE) {
  rag_check_env()

  # Normalizar si corpus-norm/ está vacío
  norm_files <- fs::dir_ls(CORPUS_NORM, recurse = TRUE, glob = "*.md",
                           fail = FALSE)
  if (length(norm_files) == 0) {
    message("corpus-norm/ vacío — normalizando primero...")
    normalize_corpus()
    norm_files <- fs::dir_ls(CORPUS_NORM, recurse = TRUE, glob = "*.md")
  }

  store <- rag_build_store(overwrite = overwrite)

  message("Chunkeando e insertando ", length(norm_files), " documentos...")
  purrr::walk(norm_files, function(f) {
    chunks <- rag_chunk_file(f)
    ragnar::ragnar_store_insert(store, chunks)
  })

  # fts = full-text search (BM25), siempre útil para nombres propios y roles
  message("Construyendo índice FTS (BM25)...")
  ragnar::ragnar_store_build_index(store, type = "fts")

  # vss = vector similarity search, solo si hay embeddings
  if (EMBED_BACKEND != "bm25") {
    message("Construyendo índice VSS (vectores)...")
    ragnar::ragnar_store_build_index(store, type = "vss")
  }

  n_chunks <- ragnar::ragnar_retrieve(store, "posición dominante", top_k = 1L) |>
    nrow()
  message(sprintf(
    "Store listo: %s  |  perfil: %s  |  chunks accesibles: %d+",
    STORE_PATH, EMBED_PROFILE, n_chunks
  ))

  invisible(store)
}

`%||%` <- function(a, b) if (is.null(a)) b else a

# ---------------------------------------------------------------------------
# Runner (solo si se ejecuta el archivo directamente)
# ---------------------------------------------------------------------------
if (sys.nframe() == 0L) {
  rag_index(overwrite = TRUE)
}
