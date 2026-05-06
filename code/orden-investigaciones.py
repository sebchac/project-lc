"""
orden-investigaciones.py
========================
Organiza y clasifica los archivos descargados de la FNE.

Pasos que ejecuta:
  1. Combina todos los CSV de rangos en un único investigaciones_fne_completo.csv
  2. Detecta las categorías únicas de la columna "conducta"
  3. Crea subcarpetas sanitizadas por categoría dentro de src/investigaciones/
  4. Mueve cada PDF a su carpeta de categoría
  5. Añade columna "categoria_folder" al CSV combinado
  6. Genera errores.log con los PDFs no encontrados
  7. Imprime un resumen final

Uso:
    python scripts/orden-investigaciones.py
    python scripts/orden-investigaciones.py --dry-run   # simular sin mover archivos
    python scripts/orden-investigaciones.py --base src/investigaciones
"""

import argparse
import logging
import re
import shutil
import unicodedata
from collections import Counter
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Configuración de rutas (relativas al directorio donde se ejecuta el script)
# ---------------------------------------------------------------------------

DEFAULT_BASE = Path("src") / "investigaciones"
PDF_SUBDIR   = "pdfs"            # carpeta origen de los PDFs
COMBINED_CSV = "investigaciones_fne_completo.csv"
ERROR_LOG    = "errores.log"
MAPPING_FILE = "categorias_mapping.csv"   # mapeo categoría → carpeta
SIN_CATEGORIA = "sin-categoria"           # carpeta para filas sin conducta
COLISIONES    = "colisiones"              # carpeta para PDFs con categoría ambigua


# ---------------------------------------------------------------------------
# Sanitización de nombres de carpeta
# ---------------------------------------------------------------------------

def sanitize_folder(text: str) -> str:
    """
    Convierte un texto a nombre de carpeta válido y legible:
      - Minúsculas
      - Normaliza Unicode (elimina tildes: é → e, ó → o, etc.)
      - Reemplaza espacios y caracteres no alfanuméricos por guiones
      - Colapsa guiones múltiples
      - Elimina guiones al inicio/fin

    Ejemplos:
      "Concentraciones o Integraciones"    → "concentraciones-o-integraciones"
      "Abusos de posición de dominio"      → "abusos-de-posicion-de-dominio"
      "Actos anticompetitivos de la auto." → "actos-anticompetitivos-de-la-auto"
    """
    if not text or not text.strip():
        return SIN_CATEGORIA
    # Normalizar Unicode: descompone caracteres acentuados y descarta diacríticos
    nfkd = unicodedata.normalize("NFKD", text.strip().lower())
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    # Reemplazar todo lo que no sea letra o número por guión
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_str)
    return slug.strip("-")


# ---------------------------------------------------------------------------
# Paso 1: Combinar CSVs
# ---------------------------------------------------------------------------

def combine_csvs(base_dir: Path) -> pd.DataFrame:
    """
    Lee todos los CSV de rangos (investigaciones_fne_paginas_*.csv) y los
    concatena en un único DataFrame.
    Normaliza los nombres de columna a minúsculas.
    """
    pattern = "investigaciones_fne_paginas_*.csv"
    csv_files = sorted(base_dir.glob(pattern))

    if not csv_files:
        raise FileNotFoundError(
            f"No se encontraron archivos {pattern} en {base_dir}"
        )

    logging.info(f"Combinando {len(csv_files)} archivos CSV...")
    frames = []
    for f in csv_files:
        df = pd.read_csv(f, dtype=str).fillna("")
        df.columns = [c.strip().lower() for c in df.columns]
        frames.append(df)
        logging.info(f"  {f.name}: {len(df)} filas")

    combined = pd.concat(frames, ignore_index=True)
    logging.info(f"Total filas combinadas: {len(combined)}")
    return combined


# ---------------------------------------------------------------------------
# Paso 2: Detectar categorías y crear carpetas
# ---------------------------------------------------------------------------

def build_category_map(df: pd.DataFrame, base_dir: Path,
                        dry_run: bool = False) -> dict[str, str]:
    """
    A partir de los valores únicos de la columna "conducta", genera un dict:
        { valor_original → nombre_de_carpeta }

    Crea las carpetas correspondientes (excepto en dry_run).
    Devuelve también el mapping y lo guarda en un CSV de referencia.
    """
    conducta_col = "conducta"
    if conducta_col not in df.columns:
        raise ValueError(
            f"Columna '{conducta_col}' no encontrada. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    valores_unicos = df[conducta_col].str.strip().unique()
    mapping = {}
    for val in sorted(valores_unicos):
        folder = sanitize_folder(val)
        mapping[val] = folder

    # Siempre incluir sin-categoria para filas vacías
    mapping[""] = SIN_CATEGORIA
    mapping[SIN_CATEGORIA] = SIN_CATEGORIA

    # Crear carpetas
    folders_created = set(mapping.values())
    for folder in sorted(folders_created):
        dest = base_dir / folder
        if not dry_run:
            dest.mkdir(exist_ok=True)
        logging.info(f"{'[dry-run] ' if dry_run else ''}Carpeta: {dest}")

    # Guardar mapping de referencia
    mapping_path = base_dir / MAPPING_FILE
    mapping_df = pd.DataFrame(
        [(k, v) for k, v in sorted(mapping.items()) if k not in ("", SIN_CATEGORIA)],
        columns=["conducta_original", "carpeta"]
    )
    if not dry_run:
        mapping_df.to_csv(mapping_path, index=False, encoding="utf-8")
        logging.info(f"Mapping guardado: {mapping_path}")

    logging.info(f"Categorías detectadas: {len(folders_created)}")
    for orig, folder in sorted(mapping.items()):
        if orig not in ("", SIN_CATEGORIA):
            logging.info(f"  {orig!r} → {folder}/")

    return mapping


# ---------------------------------------------------------------------------
# Paso 3: Mover PDFs
# ---------------------------------------------------------------------------

def move_pdfs(df: pd.DataFrame, base_dir: Path, pdf_source: Path,
              category_map: dict[str, str],
              dry_run: bool = False) -> pd.DataFrame:
    """
    Para cada fila del DataFrame, busca el PDF en pdf_source y lo mueve a la
    subcarpeta correspondiente a su conducta.

    Reglas:
    - El nombre del PDF se obtiene de la columna "pdf_filename".
      Si está vacía, se extrae del último segmento de "url_pdf".
    - Si el PDF no existe, se registra en errores.log.
    - Si ya existe en destino (reanudación), se omite el movimiento.
    - Añade/actualiza la columna "categoria_folder" en el DataFrame.

    Devuelve el DataFrame con la columna "categoria_folder" actualizada.
    """
    counters = Counter()
    conflict_log: list[str] = []

    # Construir índice de archivos disponibles en pdf_source (nombre → Path)
    available_pdfs: dict[str, Path] = {}
    if pdf_source.exists():
        for p in pdf_source.iterdir():
            if p.is_file():
                available_pdfs[p.name] = p

    logging.info(f"PDFs disponibles en origen: {len(available_pdfs)}")

    # Rastrear qué PDFs ya se asignaron (para detectar colisiones)
    assigned: dict[str, str] = {}   # pdf_filename → carpeta_destino

    categoria_folder_col = []

    for _, row in df.iterrows():
        # Determinar nombre del PDF
        pdf_name = str(row.get("pdf_filename", "")).strip()
        if not pdf_name and row.get("url_pdf", ""):
            pdf_name = str(row["url_pdf"]).rstrip("/").split("/")[-1].strip()

        if not pdf_name:
            categoria_folder_col.append("")
            counters["sin_nombre_pdf"] += 1
            continue

        # Determinar carpeta destino según conducta
        conducta_val = str(row.get("conducta", "")).strip()
        folder_name  = category_map.get(conducta_val, SIN_CATEGORIA)
        dest_dir     = base_dir / folder_name

        # Detectar colisión (mismo PDF, distinta categoría)
        if pdf_name in assigned and assigned[pdf_name] != folder_name:
            msg = (f"COLISIÓN: {pdf_name} — categorías en conflicto: "
                   f"{assigned[pdf_name]!r} vs {folder_name!r} → movido a {COLISIONES}/")
            conflict_log.append(msg)
            logging.warning(msg)
            # Mover desde la carpeta donde ya quedó a "colisiones/"
            if not dry_run:
                col_dir = base_dir / COLISIONES
                col_dir.mkdir(exist_ok=True)
                ya_en = base_dir / assigned[pdf_name] / pdf_name
                dest_col = col_dir / pdf_name
                if ya_en.exists() and not dest_col.exists():
                    shutil.move(str(ya_en), str(dest_col))
            assigned[pdf_name] = COLISIONES
            categoria_folder_col.append(COLISIONES)
            counters["colision"] += 1
            continue

        # Comprobar si el PDF existe en origen
        if pdf_name not in available_pdfs:
            logging.warning(f"NO ENCONTRADO: {pdf_name}")
            categoria_folder_col.append(folder_name)
            counters["no_encontrado"] += 1
            continue

        origen = available_pdfs[pdf_name]
        destino = dest_dir / pdf_name

        # Si ya existe en destino (ejecución previa), registrar y continuar
        if destino.exists():
            assigned[pdf_name] = folder_name
            categoria_folder_col.append(folder_name)
            counters["ya_existia"] += 1
            continue

        # Mover
        if not dry_run:
            shutil.move(str(origen), str(destino))
            # Quitar del índice para no procesarlo dos veces
            del available_pdfs[pdf_name]

        assigned[pdf_name] = folder_name
        categoria_folder_col.append(folder_name)
        counters["movido"] += 1

    df = df.copy()
    df["categoria_folder"] = categoria_folder_col

    # PDFs en origen que no aparecen en ningún CSV
    if not dry_run and available_pdfs:
        sin_csv_dir = base_dir / SIN_CATEGORIA
        sin_csv_dir.mkdir(exist_ok=True)
        logging.warning(
            f"{len(available_pdfs)} PDFs sin fila en CSV → movidos a {SIN_CATEGORIA}/"
        )
        for pname, ppath in available_pdfs.items():
            if not (sin_csv_dir / pname).exists():
                shutil.move(str(ppath), str(sin_csv_dir / pname))
        counters["sin_csv"] = len(available_pdfs)

    logging.info("Resumen de movimientos:")
    for k, v in sorted(counters.items()):
        logging.info(f"  {k}: {v}")

    return df, counters, conflict_log


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Organiza los PDFs de investigaciones FNE por categoría de conducta"
    )
    parser.add_argument(
        "--base", type=Path, default=DEFAULT_BASE,
        help=f"Directorio raíz de investigaciones (default: {DEFAULT_BASE})"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Simular sin mover archivos ni escribir nada en disco"
    )
    args = parser.parse_args()

    base_dir   = args.base.resolve()
    pdf_source = base_dir / PDF_SUBDIR
    dry_run    = args.dry_run

    # Configurar logging a consola + archivo
    log_path = base_dir / ERROR_LOG
    handlers = [logging.StreamHandler()]
    if not dry_run:
        handlers.append(logging.FileHandler(log_path, mode="w", encoding="utf-8"))

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s  %(message)s",
        handlers=handlers
    )

    if dry_run:
        logging.info("=== MODO DRY-RUN: no se moverá ningún archivo ===")

    # ------------------------------------------------------------------
    # 1. Combinar CSVs
    # ------------------------------------------------------------------
    logging.info("\n--- Paso 1: Combinar CSVs ---")
    df = combine_csvs(base_dir)

    # ------------------------------------------------------------------
    # 2. Detectar categorías y crear carpetas
    # ------------------------------------------------------------------
    logging.info("\n--- Paso 2: Categorías y carpetas ---")
    category_map = build_category_map(df, base_dir, dry_run=dry_run)

    # ------------------------------------------------------------------
    # 3. Mover PDFs
    # ------------------------------------------------------------------
    logging.info("\n--- Paso 3: Mover PDFs ---")
    df, counters, conflicts = move_pdfs(
        df, base_dir, pdf_source, category_map, dry_run=dry_run
    )

    # ------------------------------------------------------------------
    # 4. Guardar CSV combinado con columna categoria_folder
    # ------------------------------------------------------------------
    logging.info("\n--- Paso 4: Guardar CSV combinado ---")
    combined_path = base_dir / COMBINED_CSV
    if not dry_run:
        df.to_csv(combined_path, index=False, encoding="utf-8")
        logging.info(f"CSV combinado guardado: {combined_path} ({len(df)} filas)")
    else:
        logging.info(f"[dry-run] Se escribiría: {combined_path} ({len(df)} filas)")

    # ------------------------------------------------------------------
    # 5. Resumen final
    # ------------------------------------------------------------------
    logging.info("\n" + "=" * 60)
    logging.info("RESUMEN FINAL")
    logging.info("=" * 60)
    logging.info(f"Total filas en CSV combinado : {len(df)}")
    logging.info(f"Categorías detectadas        : {len(set(category_map.values()))}")

    # Conteo por categoría
    if "categoria_folder" in df.columns:
        por_cat = df["categoria_folder"].value_counts().sort_index()
        logging.info("Filas por categoría:")
        for cat, n in por_cat.items():
            logging.info(f"  {n:5d}  {cat}/")

    logging.info(f"PDFs movidos                 : {counters.get('movido', 0)}")
    logging.info(f"PDFs ya en destino (skip)    : {counters.get('ya_existia', 0)}")
    logging.info(f"PDFs no encontrados          : {counters.get('no_encontrado', 0)}")
    logging.info(f"PDFs sin fila en CSV         : {counters.get('sin_csv', 0)}")
    if conflicts:
        logging.info(f"Colisiones (→ {COLISIONES}/)  : {len(conflicts)}")

    if not dry_run:
        logging.info(f"Log de errores               : {log_path}")
        logging.info(f"Mapping de categorías        : {base_dir / MAPPING_FILE}")


if __name__ == "__main__":
    main()
