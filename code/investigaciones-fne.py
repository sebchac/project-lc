"""
investigaciones-fne.py
======================
Descarga investigaciones de la Fiscalía Nacional Económica (FNE) desde:
  https://www.fne.gob.cl/biblioteca/actuaciones-de-la-fne/investigaciones-de-la-fne-2/

Estructura real del sitio (verificada):
  - El contenido está en un iframe apuntando a /search/investigaciones.php
  - Los resultados están en /search/investigaciones_resultados.php?pagina=N&...
  - Cada página devuelve HTML estático con una <table class="results"> de 10 filas
  - 4 columnas: Título (con link PDF directo), Conducta, Mercado, Fecha
  - Total: ~2792 resultados en 280 páginas
  - Paginación: <td class="paginar">Página 1 de 280</td>
  - El PDF se descarga directamente desde el <a class="lytebox" href="...pdf">

Uso:
    python investigaciones-fne.py                    # rango definido en PAGINA_INICIO/FIN
    python investigaciones-fne.py --inicio 1 --fin 50
    python investigaciones-fne.py --no-pdf           # sólo metadatos CSV
    python investigaciones-fne.py --total-paginas    # imprime el total y sale

Para procesar todo en bloques sin saturar el servidor:
    python investigaciones-fne.py --inicio 1   --fin 50
    python investigaciones-fne.py --inicio 51  --fin 100
    ...
    python investigaciones-fne.py --inicio 251 --fin 280
"""

import argparse
import csv
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Configuración — modifica estos valores para cada bloque de descarga
# ---------------------------------------------------------------------------

PAGINA_INICIO = 1
PAGINA_FIN    = 50   # primer bloque; cambia para continuar en bloques siguientes

BASE_URL       = "https://www.fne.gob.cl"
RESULTS_URL    = (
    "https://www.fne.gob.cl/search/investigaciones_resultados.php"
    "?pagina={page}&select1=0&Conducta=0&Mercado=0"
    "&Partes=&select2=&Clave=&AnoIni=0&AnoFin=0"
)
REFERER_SEARCH = "https://www.fne.gob.cl/search/investigaciones.php"

OUTPUT_DIR = Path(__file__).parent.parent / "src" / "investigaciones"
PDF_DIR    = OUTPUT_DIR / "pdfs"

# Pausas entre peticiones para no sobrecargar el servidor
DELAY_PAGE = 1.0    # entre páginas del listado
DELAY_PDF  = 0.5    # entre descargas de PDF dentro de la misma página

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def get_with_retry(session: requests.Session, url: str, retries: int = 3,
                   extra_headers: dict = None, **kwargs) -> requests.Response | None:
    """GET con reintentos exponenciales. Devuelve None si falla definitivamente."""
    hdrs = {}
    if extra_headers:
        hdrs.update(extra_headers)
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, headers=hdrs, timeout=30, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            wait = attempt * 3
            print(f"  [reintento {attempt}/{retries}] {url} → {e}. Esperando {wait}s…")
            time.sleep(wait)
    print(f"  [ERROR] No se pudo obtener: {url}")
    return None


# ---------------------------------------------------------------------------
# Paso 1: Obtener total de páginas
# ---------------------------------------------------------------------------

def get_total_pages(session: requests.Session) -> int:
    """
    Extrae el total de páginas desde el texto "Página 1 de 280" en
    <td class="paginar">.
    """
    url = RESULTS_URL.format(page=1)
    resp = get_with_retry(session, url, extra_headers={"Referer": REFERER_SEARCH})
    if not resp:
        raise RuntimeError("No se pudo acceder a la primera página de resultados.")

    soup = BeautifulSoup(resp.text, "lxml")
    for td in soup.find_all("td", class_="paginar"):
        m = re.search(r"P[áa]gina\s+\d+\s+de\s+(\d+)", td.get_text(), re.I)
        if m:
            return int(m.group(1))

    raise RuntimeError("No se encontró el total de páginas en la respuesta.")


# ---------------------------------------------------------------------------
# Paso 2: Parsear una página de resultados
# ---------------------------------------------------------------------------

def parse_results_page(session: requests.Session, page: int) -> list[dict]:
    """
    Descarga y parsea una página de resultados.
    Devuelve lista de dicts con los campos de cada investigación.

    Estructura de la tabla (verificada):
        <table class="results">
          <tr>  ← encabezado con <th>
          <tr>  ← datos con <td>
            <td><a class="lytebox" href="URL_PDF">Título</a></td>
            <td>Conducta</td>
            <td>Mercado</td>
            <td>Fecha</td>
    """
    url = RESULTS_URL.format(page=page)
    resp = get_with_retry(session, url, extra_headers={"Referer": REFERER_SEARCH})
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    table = soup.find("table", class_="results")
    if not table:
        print(f"  [AVISO] No se encontró tabla en página {page}")
        return []

    entries = []
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue   # saltar encabezado (<th>) y filas incompletas

        # Celda 0: título + enlace directo al PDF
        a = cells[0].find("a", class_="lytebox")
        if not a:
            continue

        titulo  = a.get_text(strip=True)
        url_pdf = a.get("href", "").strip()

        # Asegurar URL absoluta
        if url_pdf.startswith("/"):
            url_pdf = urljoin(BASE_URL, url_pdf)

        # Nombre del archivo PDF (se usa tal cual para guardar en disco)
        pdf_filename = url_pdf.split("/")[-1] if url_pdf else ""

        # Número de caso desde el nombre del PDF: inic_F457_2026.pdf → F457
        m = re.search(r"_([A-Z]\d+)_", pdf_filename, re.I)
        numero_caso = m.group(1).upper() if m else ""

        conducta = cells[1].get_text(separator=" ", strip=True)
        mercado  = cells[2].get_text(separator=" ", strip=True)
        fecha    = cells[3].get_text(strip=True)

        entries.append({
            "pagina":       page,
            "numero_caso":  numero_caso,
            "titulo":       titulo,
            "conducta":     conducta,
            "mercado":      mercado,
            "fecha":        fecha,
            "url_pdf":      url_pdf,
            "pdf_filename": pdf_filename,
            "ruta_pdf":     "",
            "error":        "",
        })

    return entries


# ---------------------------------------------------------------------------
# Paso 3: Descargar un PDF
# ---------------------------------------------------------------------------

def download_pdf(session: requests.Session, url_pdf: str,
                 pdf_filename: str, dest_dir: Path) -> str:
    """
    Descarga un PDF guardándolo con su nombre original en dest_dir.
    Omite la descarga si el archivo ya existe (permite reanudar sin re-descargar).
    Devuelve la ruta del archivo guardado, o "" si falla.
    """
    if not url_pdf or not pdf_filename:
        return ""

    dest = dest_dir / pdf_filename
    if dest.exists():
        return str(dest)

    resp = get_with_retry(
        session, url_pdf,
        extra_headers={"Referer": REFERER_SEARCH},
        stream=True
    )
    if not resp:
        return ""

    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    return str(dest)


# ---------------------------------------------------------------------------
# Paso 4: Guardar CSV
# ---------------------------------------------------------------------------

CSV_FIELDS = [
    "pagina", "numero_caso", "titulo", "conducta",
    "mercado", "fecha", "url_pdf", "pdf_filename", "ruta_pdf", "error",
]


def save_csv(rows: list[dict], inicio: int, fin: int) -> Path:
    """Guarda los metadatos en un CSV nombrado con el rango de páginas procesado."""
    path = OUTPUT_DIR / f"investigaciones_fne_paginas_{inicio}_{fin}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Descarga investigaciones de la FNE por rango de páginas"
    )
    parser.add_argument(
        "--inicio", type=int, default=PAGINA_INICIO,
        help=f"Página inicial incluida (default: {PAGINA_INICIO})"
    )
    parser.add_argument(
        "--fin", type=int, default=PAGINA_FIN,
        help=f"Página final incluida (default: {PAGINA_FIN})"
    )
    parser.add_argument(
        "--no-pdf", action="store_true",
        help="Sólo guardar metadatos en CSV, sin descargar PDFs"
    )
    parser.add_argument(
        "--total-paginas", action="store_true",
        help="Imprime el total de páginas disponibles y sale sin descargar"
    )
    args = parser.parse_args()

    # Crear directorios de salida
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    session = make_session()

    # Modo informativo: sólo mostrar total de páginas
    if args.total_paginas:
        total = get_total_pages(session)
        print(f"Total de páginas disponibles: {total}")
        sys.exit(0)

    inicio = args.inicio
    fin    = args.fin

    print(f"\n=== FNE Investigaciones | páginas {inicio}–{fin} ===")
    try:
        total_pages = get_total_pages(session)
        print(f"Total disponible en el sitio: {total_pages} páginas")
        fin = min(fin, total_pages)
    except RuntimeError as e:
        print(f"[AVISO] No se pudo verificar total de páginas: {e}")

    # --- Iterar el rango de páginas ---
    all_rows: list[dict] = []

    for page in tqdm(range(inicio, fin + 1), desc="Páginas"):
        entries = parse_results_page(session, page)

        if not entries:
            time.sleep(DELAY_PAGE)
            continue

        # Descargar los PDFs de esta página antes de pasar a la siguiente
        if not args.no_pdf:
            for entry in entries:
                if entry["url_pdf"]:
                    ruta = download_pdf(
                        session,
                        entry["url_pdf"],
                        entry["pdf_filename"],
                        PDF_DIR,
                    )
                    entry["ruta_pdf"] = ruta
                    if not ruta:
                        entry["error"] = "PDF no descargado"
                    time.sleep(DELAY_PDF)

        all_rows.extend(entries)
        time.sleep(DELAY_PAGE)

    # --- Guardar CSV del rango procesado ---
    csv_path = save_csv(all_rows, inicio, fin)

    # --- Resumen final ---
    total_inv = len(all_rows)
    errors    = sum(1 for r in all_rows if r.get("error"))
    pdfs_ok   = sum(1 for r in all_rows if r.get("ruta_pdf"))

    print(f"\nListo.")
    print(f"  Investigaciones procesadas : {total_inv}")
    print(f"  Errores                    : {errors}")
    print(f"  PDFs descargados           : {pdfs_ok}")
    print(f"  CSV guardado en            : {csv_path}")
    if not args.no_pdf:
        print(f"  PDFs en                    : {PDF_DIR}")


if __name__ == "__main__":
    main()
