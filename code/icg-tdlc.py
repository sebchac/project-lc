"""
icg-tdlc.py
===========
Descarga todas las Instrucciones de Carácter General (ICG) del Tribunal de
Defensa de la Libre Competencia (TDLC) desde https://www.tdlc.cl/icg/

Estrategia de scraping:
  1. El listado usa Search & Filter + JetEngine. Las páginas se obtienen vía una
     API AJAX que devuelve JSON con HTML embebido.
     Endpoint: GET https://www.tdlc.cl/?sfid=38615&sf_action=get_data&sf_data=results&sf_paged=N
     Header requerido: X-Requested-With: XMLHttpRequest

  2. Por cada ficha (/tdlc-icg/SLUG/) se extrae:
     - Número de ICG            (del primer <h2> de título)
     - Fecha de dictación       (campo "FECHA DE DICTACIÓN:")
     - Carátula                 (campo "carátula:")
     - Rol de causa             (clase CSS del wrapper del post)
     - Resultado del TDLC       (campo "RESULTADO DEL TDLC:")
     - Resultado CS             (campo "RESULTADO EXCMA. CORTE SUPREMA:", si existe)
     - Temas                    (campo "TEMAS:", si existe)
     - URL PDF principal del ICG
     - URL PDF de la CS (si existe)

  3. Los PDFs se guardan en:
       raw/icg/pdfs/            → PDFs del ICG (principal TDLC)
       raw/icg/pdfs/            → PDFs de la CS (con sufijo _CS)

Uso:
    pip install requests beautifulsoup4 lxml tqdm
    python icg-tdlc.py

    # Sólo metadatos, sin descargar PDFs:
    python icg-tdlc.py --no-pdf

    # Procesar sólo primeras N fichas (útil para pruebas):
    python icg-tdlc.py --limit 3
"""

from __future__ import annotations

import argparse
import csv
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

BASE_URL = "https://www.tdlc.cl"

# sfid=38615 corresponde al widget Search & Filter de la página /icg/
LISTING_API = (
    "https://www.tdlc.cl/?sfid=38615&sf_action=get_data&sf_data=results&sf_paged={page}"
)

OUTPUT_CSV = Path(__file__).parent.parent / "raw" / "icg" / "icg-tdlc.csv"
PDF_DIR    = Path(__file__).parent.parent / "raw" / "icg"

DELAY_LISTING = 1.0
DELAY_FICHA   = 1.5
DELAY_PDF     = 2.0

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


def safe_filename(text: str) -> str:
    return re.sub(r'[<>:"/\\|?*\s]+', "_", text).strip("_")[:100]


def get_with_retry(session: requests.Session, url: str, retries: int = 3,
                   extra_headers: dict = None, **kwargs) -> requests.Response | None:
    headers = {}
    if extra_headers:
        headers.update(extra_headers)
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, headers=headers, timeout=30, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            wait = attempt * 3
            print(f"  [reintento {attempt}/{retries}] {url} → {e}. Esperando {wait}s…")
            time.sleep(wait)
    print(f"  [ERROR] No se pudo obtener: {url}")
    return None


# ---------------------------------------------------------------------------
# Paso 1: Obtener todas las URLs de fichas desde el listado paginado
# ---------------------------------------------------------------------------

def get_total_pages(session: requests.Session) -> int:
    url = LISTING_API.format(page=1)
    resp = get_with_retry(
        session, url,
        extra_headers={"X-Requested-With": "XMLHttpRequest",
                       "Referer": f"{BASE_URL}/icg/"}
    )
    if not resp:
        raise RuntimeError("No se pudo acceder a la API del listado.")

    data = resp.json()
    html = data.get("results", "")
    match = re.search(r"Page \d+ of (\d+)", html)
    if match:
        return int(match.group(1))

    soup = BeautifulSoup(html, "lxml")
    paged_links = [
        int(m)
        for a in soup.find_all("a", href=re.compile(r"sf_paged=(\d+)"))
        for m in re.findall(r"sf_paged=(\d+)", a["href"])
    ]
    return max(paged_links, default=1)


def scrape_listing_page(session: requests.Session, page: int) -> list[dict]:
    url = LISTING_API.format(page=page)
    resp = get_with_retry(
        session, url,
        extra_headers={"X-Requested-With": "XMLHttpRequest",
                       "Referer": f"{BASE_URL}/icg/"}
    )
    if not resp:
        return []

    data = resp.json()
    html = data.get("results", "")
    soup = BeautifulSoup(html, "lxml")

    entries = []
    for h2 in soup.find_all("h2"):
        a = h2.find("a", href=True)
        if not a or "tdlc-icg" not in a["href"]:
            continue
        parent_div = h2.find_parent("div")
        date_listing = ""
        if parent_div:
            small = parent_div.find("small")
            if small:
                date_listing = small.get_text(strip=True)
        entries.append({"url": a["href"], "date_listing": date_listing})

    return entries


def collect_all_ficha_urls(session: requests.Session) -> list[dict]:
    total_pages = get_total_pages(session)
    print(f"Total de páginas del listado: {total_pages}")

    all_entries = []
    for page in tqdm(range(1, total_pages + 1), desc="Páginas del listado"):
        entries = scrape_listing_page(session, page)
        all_entries.extend(entries)
        time.sleep(DELAY_LISTING)

    seen = set()
    unique = []
    for e in all_entries:
        if e["url"] not in seen:
            seen.add(e["url"])
            unique.append(e)

    print(f"Total de fichas únicas encontradas: {len(unique)}")
    return unique


# ---------------------------------------------------------------------------
# Paso 2: Procesar cada ficha individual
# ---------------------------------------------------------------------------

def extract_field(soup: BeautifulSoup, label: str) -> str:
    """
    Busca en los contenedores elementor el valor correspondiente al label dado.
    Estructura esperada:
        <div class="elementor-container">
            <h2 class="elementor-heading-title">LABEL:</h2>
            <div class="jet-listing-dynamic-field__content">VALOR</div>
        </div>
    """
    label_lower = label.lower()
    for container in soup.find_all("div", class_=lambda c: c and "elementor-container" in c):
        heading = container.find(["h2", "h3"], class_="elementor-heading-title")
        if not heading:
            continue
        if label_lower not in heading.get_text(strip=True).lower():
            continue
        field = container.find("div", class_="jet-listing-dynamic-field__content")
        if field:
            return field.get_text(separator=" ", strip=True)
    return ""


def extract_rol(soup: BeautifulSoup) -> str:
    """
    El rol de causa está en las clases CSS del wrapper del post:
        rol-de-causa-icg-NC-474-2020  →  NC-474-2020
    """
    wrapper = soup.find("div", class_=lambda c: c and "elementor-location-single" in c)
    if wrapper:
        for cls in wrapper.get("class", []):
            if cls.startswith("rol-de-causa-icg-"):
                raw = cls.replace("rol-de-causa-icg-", "")
                return raw.upper()
    return ""


def extract_pdfs(soup: BeautifulSoup) -> tuple[str, str]:
    """
    Extrae el PDF principal del ICG y el PDF de la CS (si existe).
    Retorna (url_pdf_icg, url_pdf_cs).

    Heurística:
    - PDF bajo sección "RESULTADO DEL TDLC" o sin sección → ICG principal
    - PDF bajo sección con "CORTE SUPREMA" → PDF de la CS
    - Fallback: si el nombre del archivo termina en _cs.pdf → CS
    """
    pdf_pattern = re.compile(r"\.pdf", re.I)
    seen: set[str] = set()
    url_pdf = ""
    url_pdf_cs = ""

    for container in soup.find_all("div", class_=lambda c: c and "elementor-container" in c):
        heading = container.find(["h2", "h3"], class_="elementor-heading-title")
        field   = container.find("div", class_="jet-listing-dynamic-field__content")
        if not field:
            continue

        heading_text = heading.get_text(strip=True).lower() if heading else ""
        is_cs_section = "corte suprema" in heading_text or "excma" in heading_text

        for a in field.find_all("a", href=pdf_pattern):
            href = a["href"]
            if href.startswith("/"):
                href = urljoin("https://www.tdlc.cl", href)
            if href in seen:
                continue
            seen.add(href)

            anchor_lower = a.get_text(strip=True).lower()
            filename_lower = href.rstrip("/").split("/")[-1].lower()
            is_cs_file = filename_lower.endswith("_cs.pdf") or "corte suprema" in anchor_lower

            if (is_cs_section or is_cs_file) and not url_pdf_cs:
                url_pdf_cs = href
            elif not url_pdf:
                url_pdf = href

    # Fallback: scan toda la página
    for a in soup.find_all("a", href=pdf_pattern):
        href = a["href"]
        if href.startswith("/"):
            href = urljoin("https://www.tdlc.cl", href)
        if href in seen:
            continue
        seen.add(href)

        filename_lower = href.rstrip("/").split("/")[-1].lower()
        anchor_lower = a.get_text(strip=True).lower()
        if (filename_lower.endswith("_cs.pdf") or "corte suprema" in anchor_lower) and not url_pdf_cs:
            url_pdf_cs = href
        elif not url_pdf:
            url_pdf = href

    return url_pdf, url_pdf_cs


def parse_ficha(session: requests.Session, url: str) -> dict:
    resp = get_with_retry(
        session, url,
        extra_headers={"Referer": f"{BASE_URL}/icg/"}
    )
    if not resp:
        return {"url_ficha": url, "error": "petición fallida"}

    soup = BeautifulSoup(resp.text, "lxml")

    numero = ""
    for h2 in soup.find_all("h2", class_="elementor-heading-title"):
        txt = h2.get_text(strip=True)
        if re.search(r"instrucción|icg|NC-", txt, re.I):
            numero = txt
            break

    fecha        = extract_field(soup, "fecha de dictación")
    caratula     = extract_field(soup, "carátula")
    rol          = extract_rol(soup)
    resultado    = extract_field(soup, "resultado del tdlc")
    resultado_cs = extract_field(soup, "resultado excma. corte suprema")
    temas        = extract_field(soup, "temas")

    url_pdf, url_pdf_cs = extract_pdfs(soup)

    return {
        "numero":        numero,
        "fecha":         fecha,
        "caratula":      caratula,
        "rol_causa":     rol,
        "resultado_tdlc": resultado,
        "resultado_cs":  resultado_cs,
        "temas":         temas,
        "url_pdf":       url_pdf,
        "url_pdf_cs":    url_pdf_cs,
        "url_ficha":     url,
        "error":         "",
    }


# ---------------------------------------------------------------------------
# Paso 3: Descargar PDFs
# ---------------------------------------------------------------------------

def download_pdf(session: requests.Session, pdf_url: str, dest_dir: Path,
                 numero: str, suffix: str = "") -> str:
    """
    Descarga un PDF y lo guarda en dest_dir.
    `suffix` se añade al nombre de archivo (ej. "_CS") para el PDF de la CS.
    Devuelve la ruta del archivo guardado, o "" si falla.
    """
    if not pdf_url:
        return ""

    base = safe_filename(numero.split(":")[0].strip()) if numero else \
           safe_filename(pdf_url.split("/")[-1].replace(".pdf", ""))
    dest = dest_dir / f"{base}{suffix}.pdf"

    if dest.exists():
        return str(dest)

    if pdf_url.startswith("/"):
        pdf_url = urljoin(BASE_URL, pdf_url)

    resp = get_with_retry(session, pdf_url, extra_headers={"Referer": BASE_URL}, stream=True)
    if not resp:
        return ""

    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    return str(dest)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Descarga ICG del TDLC (metadatos + PDFs)"
    )
    parser.add_argument(
        "--no-pdf", action="store_true",
        help="No descargar archivos PDF, sólo guardar metadatos en CSV"
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Limitar a las primeras N fichas (0 = sin límite, útil para pruebas)"
    )
    args = parser.parse_args()

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    session = make_session()

    print("\n=== Recolectando URLs del listado ===")
    ficha_entries = collect_all_ficha_urls(session)

    if args.limit:
        ficha_entries = ficha_entries[: args.limit]
        print(f"Limitando a {args.limit} fichas.")

    print("\n=== Procesando fichas ===")
    rows = []
    csv_fields = [
        "numero", "fecha", "caratula", "rol_causa",
        "resultado_tdlc", "resultado_cs", "temas",
        "url_pdf", "ruta_pdf",
        "url_pdf_cs", "ruta_pdf_cs",
        "url_ficha", "error",
    ]

    for entry in tqdm(ficha_entries, desc="ICGs"):
        data = parse_ficha(session, entry["url"])

        if not data.get("fecha") and entry.get("date_listing"):
            data["fecha"] = entry["date_listing"]

        numero = data.get("numero", "")

        ruta_pdf = ""
        if not args.no_pdf and data.get("url_pdf"):
            ruta_pdf = download_pdf(session, data["url_pdf"], PDF_DIR, numero)
            time.sleep(DELAY_PDF)
        data["ruta_pdf"] = ruta_pdf

        ruta_pdf_cs = ""
        if not args.no_pdf and data.get("url_pdf_cs"):
            ruta_pdf_cs = download_pdf(session, data["url_pdf_cs"], PDF_DIR, numero, suffix="_CS")
            if not ruta_pdf_cs:
                prev = data.get("error", "")
                data["error"] = (prev + " | error descarga PDF CS").lstrip(" | ")
            time.sleep(DELAY_PDF)
        data["ruta_pdf_cs"] = ruta_pdf_cs

        rows.append(data)
        time.sleep(DELAY_FICHA)

    print(f"\n=== Guardando CSV en {OUTPUT_CSV} ===")
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    total      = len(rows)
    errors     = sum(1 for r in rows if r.get("error"))
    pdfs_ok    = sum(1 for r in rows if r.get("ruta_pdf"))
    cs_ok      = sum(1 for r in rows if r.get("ruta_pdf_cs"))
    print(
        f"\nListo. {total} ICGs procesadas | {errors} errores\n"
        f"  PDFs ICG: {pdfs_ok} descargados\n"
        f"  PDFs CS:  {cs_ok} descargados"
    )
    print(f"CSV: {OUTPUT_CSV}")
    if not args.no_pdf:
        print(f"PDFs: {PDF_DIR}")


if __name__ == "__main__":
    main()
