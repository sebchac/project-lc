# 02_query.R — Consulta del store (retrieval + generación con citas)
# ---------------------------------------------------------------------------
# Dos modos:
#   rag_retrieve(q)        -> solo recuperación (para evaluar recall, sin LLM).
#   rag_ask(q, model)      -> recupera + genera respuesta citada con ellmer.
#
# VERIFICAR firmas: ?ragnar::ragnar_retrieve ;
#   ?ragnar::ragnar_register_tool_retrieve ; ?ellmer::chat_anthropic
# ---------------------------------------------------------------------------

source(here::here("rag", "R", "setup.R"))
source(here::here("rag", "R", "prompt_rules.R"))

rag_open_store <- function() {
  if (!fs::file_exists(STORE_PATH))
    stop("No existe el store. Corre primero 01_chunk_index.R")
  ragnar::ragnar_store_connect(STORE_PATH)   # verificar nombre exacto en ragnar
}

# --- Modo 1: solo recuperación (evaluación de recall, sin costo de LLM) -------
rag_retrieve <- function(q, top_k = TOP_K, store = rag_open_store()) {
  ragnar::ragnar_retrieve(store, q, top_k = top_k)
}

# --- Modo 2: pregunta con respuesta citada -----------------------------------
# system_prompt: SYSTEM_PROMPT_LC (razonamiento) o SYSTEM_PROMPT_EXTRACT (lookup).
rag_ask <- function(q,
                    model = GEN_MODEL,
                    system_prompt = SYSTEM_PROMPT_LC,
                    store = rag_open_store()) {
  chat <- ellmer::chat_anthropic(model = model, system_prompt = system_prompt)
  # Registra la búsqueda como herramienta: el modelo recupera por sí mismo.
  ragnar::ragnar_register_tool_retrieve(chat, store, top_k = TOP_K)
  chat$chat(q)
}

# --- Generación de minuta a outputs/ (usa GEN_SMART por defecto) -------------
rag_minuta <- function(q, file, model = GEN_SMART) {
  resp <- rag_ask(q, model = model, system_prompt = SYSTEM_PROMPT_LC)
  path <- file.path(OUTPUTS_DIR, file)
  readr::write_file(resp, path)
  message("Minuta escrita en ", path)
  invisible(path)
}

# --- Runner de ejemplo (guardado) --------------------------------------------
if (sys.nframe() == 0L) {
  rag_check_env()
  cat(rag_ask(
    "¿Qué estándar aplicó el TDLC para configurar abuso de posición dominante
     por estrangulamiento de márgenes en telecomunicaciones? Cita el considerando."
  ))
}
