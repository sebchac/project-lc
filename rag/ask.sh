#!/usr/bin/env bash
# rag/ask.sh — Consulta RAG desde la terminal sin API key
#
# USO:
#   ./rag/ask.sh "¿Qué estándar probatorio usó el TDLC en colusión?"
#   ./rag/ask.sh "tu pregunta" 10          # top_k=10 (default: 7)
#
# REQUIERE: R con ragnar instalado + store.duckdb construido (01_chunk_index.R)
# MODELO:   usa claude CLI (tu suscripción Claude.ai, sin API key separada)

set -euo pipefail

PREGUNTA="${1:-}"
TOP_K="${2:-12}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ -z "$PREGUNTA" ]]; then
  echo "Uso: $0 \"tu pregunta\" [top_k]" >&2
  exit 1
fi

# 1. Recuperar chunks desde el store ragnar
# Pasamos la pregunta via archivo temporal para evitar problemas con caracteres especiales
TMPQ=$(mktemp)
echo "$PREGUNTA" > "$TMPQ"

CONTEXTO=$(Rscript --quiet -e "
suppressPackageStartupMessages({ library(ragnar); library(here) })
source(here::here('rag', 'R', 'config.R'))

pregunta <- readLines('${TMPQ}', warn = FALSE)
store <- ragnar_store_connect(STORE_PATH, read_only = TRUE)
res   <- ragnar_retrieve(store, pregunta, top_k = ${TOP_K}L)

doc_name <- function(o) basename(tools::file_path_sans_ext(o))
for (i in seq_len(nrow(res))) {
  cat(sprintf('--- [%d] %s ---\n%s\n\n',
    i, doc_name(res\$origin[i]), res\$text[i]))
}
" 2>/dev/null)
rm -f "$TMPQ"

if [[ -z "$CONTEXTO" ]]; then
  echo "Error: no se recuperaron chunks. ¿Está construido el store?" >&2
  exit 1
fi

# 2. Generar respuesta con claude CLI (autenticado con suscripción Claude.ai)
SYSTEM_PROMPT="Eres un asistente experto en libre competencia chilena. \
Responde SOLO con base en los fragmentos del corpus que se te entregan. \
Cita siempre el documento y considerando exacto entre comillas. \
Si la información no está en los fragmentos, dilo explícitamente. \
Jerarquía de autoridad: CS > TDLC > FNE. \
Indica siempre si la CS confirmó, revocó o no conoció la sentencia del TDLC citada."

PROMPT="CONTEXTO DEL CORPUS (fragmentos recuperados):

${CONTEXTO}

PREGUNTA: ${PREGUNTA}"

echo "$PROMPT" | claude --print --system-prompt "$SYSTEM_PROMPT"
