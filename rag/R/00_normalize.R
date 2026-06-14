# 00_normalize.R — Normalización del corpus
# ---------------------------------------------------------------------------
# Patrón diagnosticado sobre el corpus real (9 tipos de documentos, 2004–2026):
#
#  PROBLEMA 1 — Espacios dobles internos
#    "tiene  competencia" → "tiene competencia"  (OCR columnar en 2 columnas)
#
#  PROBLEMA 2 — Párrafos partidos en líneas cortas
#    El PDF escaneado convierte un párrafo largo en ~10 líneas de 60-80 chars.
#    markdown_chunk() trataría cada línea como chunk independiente.
#
#  ESTRUCTURA REAL (varía por tipo y período):
#    Secciones fijas:  VISTOS: / Vistos: / CONSIDERANDO: / VISTOS Y CONSIDERANDO:
#    Considerandos:
#      - Ordinales textuales:  PRIMERO:  SEGUNDO:  TERCERO:  (resoluciones, CS)
#      - Numeración decimal:   1.   2.   1.1.   1.2.3.      (sentencias post-2010)
#      - Mixto:                CONSIDERANDO: + PRIMERO:  (sentencias pre-2010)
#    Resolutivo:    SE RESUELVE: / SE RESUELVE, / SE DECLARA / RESUELVE /
#                  1. (en resolutivo CS) / PRIMERO: (resolutivo resoluciones)
#    Otros:         I.- / II.-  (romano con guion, ERN/CS)
#
#  QUÉ HACE ESTE SCRIPT:
#    A. Colapsa espacios dobles → uno (solo dentro de línea, no cruza tokens).
#    B. Re-une líneas de párrafo partidas (preserva texto exacto).
#    C. Inserta prefijo ## o ### en marcadores estructurales para que
#       markdown_chunk() capture el contexto de sección por chunk.
#
#  INVARIANTE DE FIDELIDAD:
#    Todos los tokens (palabras) del original aparecen en el normalizado,
#    en el mismo orden. Solo cambian saltos de línea, espacios y se añaden
#    los prefijos ## / ###. La verificación token-a-token lo comprueba.
#
#  NO modifica raw-md/ — escribe en rag/corpus-norm/ (gitignored).
# ---------------------------------------------------------------------------

suppressPackageStartupMessages({
  library(stringr)
  library(fs)
  library(here)
  library(purrr)
  library(readr)
})

source(here::here("rag", "R", "config.R"))

# Suprimir avisos del linter por variables globales definidas en config.R
utils::globalVariables(c(
  "CORPUS_MD", "CORPUS_NORM", "PILOTO", "PILOTO_SENTENCIAS"
))

# ---------------------------------------------------------------------------
# Patrones de estructura (compilados una sola vez)
# ---------------------------------------------------------------------------

# Secciones de nivel 1 (## en el output) — presentes en TODOS los tipos
pat_h1 <- paste0(
  "^(VISTOS|Vistos)\\s*[:\\.]*\\s*$",
  "|^CONSIDERANDO\\s*[:\\.]*\\s*$",
  "|^VISTOS\\s+Y\\s+CONSIDERANDO\\s*[:\\.]*\\s*$",
  "|^CON\\s+LO\\s+RELACIONADO\\s+Y\\s+CONSIDERANDO\\s*[:\\.]*\\s*$",
  "|^SE\\s+RESUELVE\\s*[,:\\.]*\\s*$",
  "|^SE\\s+DECLARA\\s*[,:\\.]*\\s*$",
  "|^RESUELVE\\s*[:\\.]*\\s*$"
)

# Subsecciones de nivel 2 (### en el output)
# NOTA: todos los str_detect que usan pat_h2 deben pasarlo como
#   regex(pat_h2, ignore_case = TRUE)  — el corpus mezcla ALL CAPS y Title Case.

# Unidades reutilizables (1-9) para componer ordinales compuestos
.ORD_UNIDADES <- paste0(
  "PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO|",
  "SEXTO|S[EÉ]PTIMO|OCTAVO|NOVENO"
)
# Decenas (20-90) y centena (100) que admiten forma compuesta
.ORD_DECENAS <- paste0(
  "VIG[EÉ]SIMO|TRIG[EÉ]SIMO|CUADRAG[EÉ]SIMO|QUINCUAG[EÉ]SIMO|",
  "SEXAG[EÉ]SIMO|SEPTUAG[EÉ]SIMO|OCTOG[EÉ]SIMO|NONAG[EÉ]SIMO|CENT[EÉ]SIMO"
)

pat_h2 <- paste0(
  # Ordinales simples 1-9 y compuestos con decena + unidad
  # ignore_case se aplica en str_detect — aquí el patrón es case-insensitive-ready
  "^(PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO|SEXTO|S[EÉ]PTIMO|OCTAVO|NOVENO|",
  "D[EÉ]CIMO(\\s+(", .ORD_UNIDADES, "))?|",
  "UND[EÉ]CIMO|DUO D[EÉ]CIMO|DUOD[EÉ]CIMO|",
  # Decenas completas: VIGÉSIMO [UNIDAD]? ... CENTÉSIMO [UNIDAD]?
  "(", .ORD_DECENAS, ")(\\s+(", .ORD_UNIDADES, "))?",
  ")\\s*:",

  # Numeración decimal de primer nivel sola en su línea: "1." "2." ... "99."
  # (no "1.1." ni "1.2." — esos son tercer nivel o subnumeración)
  "|^[0-9]{1,3}\\.\\s*$",

  # Numeración decimal de segundo nivel: "1.1." "1.2." "10.3." al inicio
  # Máximo 2 dígitos tras el punto para no capturar miles: "1.000"  "20.000"
  "|^[0-9]{1,3}\\.[0-9]{1,2}\\.?\\s",
  "|^[0-9]{1,3}\\.[0-9]{1,2}\\.$",

  # Romano con guion: I.- II.- III.- IV.- V.-
  "|^(I{1,3}|IV|V{0,1}I{0,3}|IX|X{1,2})\\.[-–]",

  # EN CUANTO A / SOBRE EL / ACERCA DE (divisiones internas frecuentes)
  "|^EN\\s+CUANTO\\s+A",
  "|^SOBRE\\s+EL\\s+FONDO",
  "|^SOBRE\\s+LA\\s+",
  "|^ACERCA\\s+DE"
)

# Líneas que NUNCA se pegan a la línea anterior (encabezados + líneas vacías)
es_encabezado <- function(ln) {
  str_detect(ln, regex(paste0(pat_h1, "|", pat_h2,
                        "|^#",
                        "|^REPÚBLICA|^REPUBLICA",
                        "|^TRIBUNAL DE",
                        "|^CORTE SUPREMA",
                        "|^DECRETO LEY"),
                       ignore_case = TRUE))
}

# ---------------------------------------------------------------------------
# A + B: colapsa espacios y re-une párrafos partidos
# ---------------------------------------------------------------------------
rejoin_lines <- function(lineas) {
  out    <- character()
  buffer <- ""

  flush_buf <- function() {
    trimmed <- str_squish(buffer)
    if (nzchar(trimmed)) out[[length(out) + 1L]] <<- trimmed
    buffer <<- ""
  }

  for (raw_ln in lineas) {
    # A. Colapsa espacios dobles
    ln <- str_replace_all(raw_ln, "  +", " ")

    # Línea vacía → cierra párrafo
    if (!nzchar(str_trim(ln))) {
      flush_buf()
      out[[length(out) + 1L]] <- ""
      next
    }

    # Encabezado → cierra párrafo, emite tal cual
    if (es_encabezado(ln)) {
      flush_buf()
      out[[length(out) + 1L]] <- str_trim(ln)
      next
    }

    # B. Acumulación de líneas de párrafo
    ln_trim <- str_trim(ln)
    if (nzchar(buffer)) {
      # Une si el buffer NO termina en puntuación que cierra oración
      if (str_detect(buffer, "[.?!]\\s*$")) {
        flush_buf()
        buffer <- ln_trim
      } else {
        buffer <- paste(buffer, ln_trim)
      }
    } else {
      buffer <- ln_trim
    }
  }
  flush_buf()
  out
}

# ---------------------------------------------------------------------------
# C: inserta prefijos ## / ### en marcadores estructurales
# ---------------------------------------------------------------------------
add_headings <- function(lineas) {
  map_chr(lineas, function(ln) {
    if (str_detect(ln, regex(pat_h1, ignore_case = TRUE))) return(paste("##",  ln))
    if (str_detect(ln, regex(pat_h2, ignore_case = TRUE))) return(paste("###", ln))
    ln
  })
}

# ---------------------------------------------------------------------------
# Pipeline completo para un archivo
# ---------------------------------------------------------------------------
normalize_file <- function(path_in, path_out) {
  texto  <- read_file(path_in)
  lineas <- str_split(texto, "\n")[[1]]

  resultado <- lineas |>
    rejoin_lines() |>
    add_headings() |>
    paste(collapse = "\n")

  write_file(resultado, path_out)
  invisible(path_out)
}

# ---------------------------------------------------------------------------
# Verificación de fidelidad (tokens preservados, mismo orden)
# ---------------------------------------------------------------------------
verify_fidelity <- function(path_in, path_out) {
  # Excluye los prefijos ## / ### que agregamos (son los únicos tokens nuevos)
  limpiar <- function(txt) {
    txt |>
      str_replace_all("(?m)^#{1,6} ", "") |>
      str_squish() |>
      str_split("\\s+")
  }
  tok_in  <- limpiar(read_file(path_in))[[1]]
  tok_out <- limpiar(read_file(path_out))[[1]]

  if (!identical(tok_in, tok_out)) {
    extras   <- setdiff(tok_out, tok_in)
    faltantes <- setdiff(tok_in, tok_out)
    warning(sprintf(
      "%s: %d tokens extra, %d tokens faltantes. Extras: [%s] Faltantes: [%s]",
      basename(path_in), length(extras), length(faltantes),
      paste(head(extras, 5), collapse = "|"),
      paste(head(faltantes, 5), collapse = "|")
    ))
    return(FALSE)
  }
  TRUE
}

# ---------------------------------------------------------------------------
# Normaliza el corpus (piloto o completo) y reporta
# ---------------------------------------------------------------------------
normalize_corpus <- function(verbose = TRUE) {
  all_files <- fs::dir_ls(CORPUS_MD, recurse = TRUE, glob = "*.md")

  if (PILOTO) {
    patt  <- paste(PILOTO_SENTENCIAS, collapse = "|")
    files <- all_files[str_detect(fs::path_file(all_files), patt)]
  } else {
    files <- all_files
  }

  if (length(files) == 0)
    stop("Sin archivos para normalizar. Verifica CORPUS_MD y PILOTO_SENTENCIAS.")

  fs::dir_create(CORPUS_NORM)

  resultados <- map(files, function(f) {
    rel      <- fs::path_rel(fs::path_dir(f), CORPUS_MD)
    dir_out  <- file.path(CORPUS_NORM, rel)
    fs::dir_create(dir_out)
    path_out <- file.path(dir_out, fs::path_file(f))

    normalize_file(f, path_out)
    ok <- tryCatch(verify_fidelity(f, path_out),
                   warning = function(w) { message("ADVERTENCIA: ", conditionMessage(w)); FALSE })

    list(archivo = fs::path_file(f), ok = ok, path_out = path_out)
  })

  n_ok   <- sum(map_lgl(resultados, "ok"))
  n_fail <- length(resultados) - n_ok
  message(sprintf("Normalización: %d/%d archivos OK, %d con advertencia.",
                  n_ok, length(resultados), n_fail))
  invisible(resultados)
}

# ---------------------------------------------------------------------------
# Runner: solo ejecuta si se llama directamente (no al source())
# ---------------------------------------------------------------------------
if (sys.nframe() == 0L) {
  normalize_corpus(verbose = TRUE)
}
