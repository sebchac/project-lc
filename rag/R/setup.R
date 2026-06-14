# setup.R — Dependencias y helpers compartidos
# ---------------------------------------------------------------------------
# source() este archivo desde cualquier script para cargar todo lo necesario.
# No indexa nada ni ejecuta trabajo pesado.
#
# PRIMERA VEZ: instalar paquetes con el bloque de abajo (descomentar).
# ---------------------------------------------------------------------------

# --- Instalación (descomentar y ejecutar UNA vez) ----------------------------
# install.packages(
#   c("ragnar", "ellmer", "duckdb", "dplyr", "stringr",
#     "fs", "here", "purrr", "readr", "tibble"),
#   repos = "https://cloud.r-project.org"
# )

suppressPackageStartupMessages({
  library(dplyr)
  library(stringr)
  library(fs)
  library(here)
  library(purrr)
  library(readr)
  library(tibble)
})

# ragnar y ellmer se cargan solo si están instalados (permiten correr
# el pipeline en modo BM25 / solo normalización sin ellos).
if (requireNamespace("ragnar", quietly = TRUE)) library(ragnar)
if (requireNamespace("ellmer", quietly = TRUE)) library(ellmer)

source(here::here("rag", "R", "config.R"))

# ---------------------------------------------------------------------------
# Selector de función de embedding
# Devuelve NULL en modo BM25 (ragnar_store_create acepta embed=NULL).
# VERIFICAR firmas contra la versión instalada: ?ragnar::ragnar_store_create
# ---------------------------------------------------------------------------
rag_embed_fn <- function(backend = EMBED_BACKEND, model = EMBED_MODEL) {
  if (backend == "bm25") return(NULL)
  if (!requireNamespace("ragnar", quietly = TRUE))
    stop("ragnar no instalado. Corre: install.packages('ragnar')")
  switch(
    backend,
    ollama = function(x) ragnar::embed_ollama(x, model = model),
    voyage = function(x) ragnar::embed_voyage(x, model = model),
    openai = function(x) ragnar::embed_openai(x, model = model),
    stop("EMBED_BACKEND desconocido: ", backend)
  )
}

# ---------------------------------------------------------------------------
# Verificación de entorno con instrucciones de instalación
# ---------------------------------------------------------------------------
rag_check_env <- function() {
  ok <- TRUE

  # ragnar
  if (!requireNamespace("ragnar", quietly = TRUE)) {
    message("FALTA: ragnar  ->  install.packages('ragnar')")
    ok <- FALSE
  }
  # ellmer
  if (!requireNamespace("ellmer", quietly = TRUE)) {
    message("FALTA: ellmer  ->  install.packages('ellmer')")
    ok <- FALSE
  }

  # Ollama (solo si el perfil activo lo necesita)
  if (EMBED_BACKEND == "ollama") {
    if (!nzchar(Sys.which("ollama"))) {
      message(paste(
        "FALTA: Ollama no encontrado en PATH.",
        "Instalar: brew install ollama",
        "Luego arrancar: ollama serve",
        paste0("Luego bajar modelo: ollama pull ", EMBED_MODEL),
        sep = "\n  "
      ))
      ok <- FALSE
    }
  }

  # API keys
  if (EMBED_BACKEND == "voyage" && !nzchar(Sys.getenv("VOYAGE_API_KEY"))) {
    message("FALTA: VOYAGE_API_KEY no definida en el entorno.")
    ok <- FALSE
  }
  if (grepl("^claude", GEN_MODEL) && !nzchar(Sys.getenv("ANTHROPIC_API_KEY"))) {
    message("FALTA: ANTHROPIC_API_KEY no definida en el entorno.")
    ok <- FALSE
  }

  if (ok) {
    message(sprintf(
      "Entorno OK  |  embedding: %s / %s  |  generacion: %s",
      EMBED_PROFILE, EMBED_MODEL, GEN_MODEL
    ))
  }
  invisible(ok)
}

# ---------------------------------------------------------------------------
# Derivar metadatos desde la ruta del archivo
# Alimenta el filtrado y ponderación por jerarquía de autoridad (CLAUDE.md)
# ---------------------------------------------------------------------------
rag_meta_from_path <- function(path) {
  base    <- fs::path_ext_remove(fs::path_file(path))
  carpeta <- fs::path_file(fs::path_dir(path))

  tipo <- case_when(
    str_detect(carpeta, "sentencias-tdlc")   ~ "sentencia_tdlc",
    str_detect(carpeta, "sentencias-cs")      ~ "sentencia_cs",
    str_detect(carpeta, "resoluciones-tdlc")  ~ "resolucion_tdlc",
    str_detect(carpeta, "resoluciones-cs")    ~ "resolucion_cs",
    str_detect(carpeta, "ae-tdlc")            ~ "acuerdo_extrajudicial",
    str_detect(carpeta, "ern-tdlc")           ~ "ern",
    str_detect(carpeta, "icg-tdlc")           ~ "icg",
    str_detect(carpeta, "normativa-fusiones") ~ "guia_fne",
    str_detect(carpeta, "normativa-general")  ~ "dl211",
    .default                                  = "otro"
  )

  # Jerarquía de autoridad según CLAUDE.md (0 = ancla normativa, 9 = sin clasificar)
  autoridad <- case_when(
    tipo %in% c("sentencia_cs", "resolucion_cs")                          ~ 1L,
    tipo %in% c("sentencia_tdlc", "resolucion_tdlc",
                "icg", "acuerdo_extrajudicial", "ern")                     ~ 2L,
    tipo == "guia_fne"                                                     ~ 4L,
    tipo == "dl211"                                                        ~ 0L,
    .default                                                               = 9L
  )

  track <- if_else(tipo %in% c("guia_fne", "dl211"), "C", "A")
  anio  <- str_extract(base, "(?<=_)[0-9]{4}")
  rol   <- str_extract(base, "[0-9]+_[0-9]{4}")

  tibble(
    documento = base,
    tipo      = tipo,
    autoridad = autoridad,
    track     = track,
    anio      = anio,
    rol       = rol
  )
}
