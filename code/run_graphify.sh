#!/usr/bin/env bash
# =============================================================================
# run_graphify.sh
# Script de referencia para ejecutar Graphify sobre las sentencias del TDLC
# Basado en: Schrepel (2026), "Building a Digital Brain for Research"
#
# IMPORTANTE: Este script NO se ejecuta directamente con bash.
# Graphify es un skill de Claude Code CLI. Los comandos de la sección
# "EJECUCIÓN" se escriben DENTRO de una sesión de Claude Code (claude CLI).
# =============================================================================

# -----------------------------------------------------------------------------
# PASO 1 — INSTALACIÓN (solo la primera vez)
# Ejecutar en tu Terminal normal:
# -----------------------------------------------------------------------------
# pip install graphifyy        # nota: doble 'y'
# graphify install             # registra el skill en Claude Code

# -----------------------------------------------------------------------------
# PASO 2 — ABRIR CLAUDE CODE EN LA CARPETA RAÍZ DEL PROYECTO
# Ejecutar en tu Terminal normal:
# -----------------------------------------------------------------------------
# cd /Users/chac/Documents/GitHub/project-lc
# claude

# -----------------------------------------------------------------------------
# PASO 3 — EJECUCIÓN DEL GRAFO (escribir dentro de Claude Code)
# Primera ejecución completa:
# -----------------------------------------------------------------------------
# /graphify build/sentencias-tdlc-md
#
# → Cuando Claude Code pregunte por el tamaño del corpus, responder: all
#
# Corpus: 209 archivos .md
# Tiempo estimado: 15-30 minutos (1-2 sesiones según tokens disponibles)
# El SHA-256 cache asegura que si se interrumpe, se reanuda donde quedó.

# -----------------------------------------------------------------------------
# PASO 4 — REANUDAR SI SE INTERRUMPE (en nueva sesión de Claude Code)
# -----------------------------------------------------------------------------
# /graphify build/sentencias-tdlc-md --update

# -----------------------------------------------------------------------------
# PASO 5 — GENERAR LA WIKI (dentro de Claude Code, tras el grafo)
# Opción A — con el comando nativo de Graphify:
# -----------------------------------------------------------------------------
# /graphify --wiki

# Opción B — con prompt directo a Claude Code (si el comando devuelve error):
# -----------------------------------------------------------------------------
# Read everything in /Users/chac/Documents/GitHub/project-lc/build/sentencias-tdlc-md
# Then compile a wiki in wiki/ following the rules in CLAUDE.md.
# Create an INDEX.md first, then create one .md file per major topic.
# Link related topics. Summarize every source.

# -----------------------------------------------------------------------------
# SALIDA ESPERADA (carpeta graphify-out/ en la raíz del proyecto)
# -----------------------------------------------------------------------------
# graphify-out/
# ├── graph.html        → grafo interactivo (abrir en browser)
# ├── graph.json        → grafo consultable en formato JSON
# ├── GRAPH_REPORT.md   → reporte: nodos god, comunidades, preguntas sugeridas
# └── cache/            → caché SHA-256 (no tocar)

# -----------------------------------------------------------------------------
# NOTAS PARA EL CORPUS TDLC
# -----------------------------------------------------------------------------
# - El CLAUDE.md ya está configurado con jerarquía de autoridad, áreas de
#   foco, Claim Extraction Rules, Hypothesis Register y Diagnostic Module.
# - No es necesario modificar nada antes de correr Graphify.
# - Las sentencias están en: build/sentencias-tdlc-md/ (209 archivos)
# - Las resoluciones están en: build/resoluciones-tdlc-md/ (para una segunda
#   pasada después de las sentencias)
# =============================================================================
