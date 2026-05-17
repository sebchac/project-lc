"""
resoluciones-tdlc.py
====================
Descarga todas las resoluciones del Tribunal de Defensa de la Libre Competencia
(TDLC) desde https://www.tdlc.cl/resoluciones/

Diferencias clave respecto a sentencias-tdlc.py:
  - El listado es server-side (sin AJAX): se accede directamente a
    https://www.tdlc.cl/resoluciones/?sf_paged=N
  - Los links "Ver Ficha" están en el HTML principal como
    <h2 class="elementor-heading-title"><a href="...">Ver Ficha</a></h2>
  - El total de páginas se extrae del link con clase "pagelast" (enlace "Last").
  - La ficha tiene los mismos campos elementor que sentencias (FECHA DE DICTACIÓN,
    carátula, resultado del tdlc con PDF, etc.)
  - Cuando el caso fue elevado a la Corte Suprema, la ficha incluye un bloque
    "RESULTADO EXCMA. CORTE SUPREMA" con el PDF asociado.

Los PDFs se guardan según su tipo:
    raw/resoluciones-tdlc/         → PDFs del TDLC (principal)
    raw/resoluciones-cs/           → PDFs de la Corte Suprema
    raw/resoluciones-tdlc/otros/   → PDFs adicionales (rectificaciones, etc.)

Uso:
    python resoluciones-tdlc.py             # descarga todo
    python resoluciones-tdlc.py --no-pdf    # sólo metadatos CSV
    python resoluciones-tdlc.py --limit 5   # prueba con 5 resoluciones
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

BASE_URL     = "https://www.tdlc.cl"
LISTING_URL  = "https://www.tdlc.cl/resoluciones/"
# Paginación directa: el servidor devuelve HTML completo para cada página
LISTING_PAGE_URL = "https://www.tdlc.cl/resoluciones/?sf_paged={page}"

OUTPUT_CSV    = Path(__file__).parent.parent / "raw" / "resoluciones-tdlc" / "resoluciones-tdlc.csv"
PDF_DIR       = Path(__file__).parent.parent / "raw" / "resoluciones-tdlc"
CS_PDF_DIR    = Path(__file__).parent.parent / "raw" / "resoluciones-cs"
OTROS_PDF_DIR = PDF_DIR / "otros"

# Pausas entre peticiones para no saturar el servidor
DELAY_LISTING = 1.5   # entre páginas del listado
DELAY_FICHA   = 1.5   # entre fichas individuales
DELAY_PDF     = 2.0   # entre descargas de PDF

# Cabeceras HTTP realistas para evitar bloqueos 403
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
    """GET con reintentos exponenciales. Devuelve None si falla definitivamente."""
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
    """
    Obtiene el número total de páginas del listado.

    La página principal tiene un link con clase "pagelast" cuyo href contiene
    sf_paged=N, donde N es la última página.
    Ejemplo: href="https://www.tdlc.cl/?page_id=38816&sf_paged=8"
    """
    resp = get_with_retry(
        session, LISTING_URL,
        extra_headers={"Referer": BASE_URL}
    )
    if not resp:
        raise RuntimeError("No se pudo acceder al listado de resoluciones.")

    soup = BeautifulSoup(resp.text, "lxml")

    last_link = soup.find("a", class_=re.compile(r"pagelast"))
    if last_link and last_link.get("href"):
        m = re.search(r"sf_paged=(\d+)", last_link["href"])
        if m:
            return int(m.group(1))

    # Fallback: máximo valor de sf_paged en los links de paginación
    paged_values = [
        int(m)
        for a in soup.find_all("a", href=re.compile(r"sf_paged=(\d+)"))
        for m in re.findall(r"sf_paged=(\d+)", a["href"])
    ]
    return max(paged_values, default=1)


def scrape_listing_page(session: requests.Session, page: int) -> list[str]:
    """
    Extrae los URLs de las fichas de una página del listado.

    Los links "Ver Ficha" están en el HTML del servidor como:
        <h2 class="elementor-heading-title"><a href="URL">Ver Ficha</a></h2>
    """
    url = LISTING_URL if page == 1 else LISTING_PAGE_URL.format(page=page)
    resp = get_with_retry(
        session, url,
        extra_headers={"Referer": LISTING_URL}
    )
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "lxml")

    urls = []
    for a in soup.find_all("a", string="Ver Ficha"):
        href = a.get("href", "")
        if "tdlc-resoluciones" in href:
            urls.append(href)

    return urls


def collect_all_ficha_urls(session: requests.Session) -> list[str]:
    """
    Itera todas las páginas del listado y devuelve la lista completa de URLs de fichas.
    """
    total_pages = get_total_pages(session)
    print(f"Total de páginas del listado: {total_pages}")

    all_urls = []
    for page in tqdm(range(1, total_pages + 1), desc="Páginas del listado"):
        urls = scrape_listing_page(session, page)
        all_urls.extend(urls)
        time.sleep(DELAY_LISTING)

    seen = set()
    unique = []
    for u in all_urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)

    print(f"Total de fichas únicas encontradas: {len(unique)}")
    return unique


# ---------------------------------------------------------------------------
# Paso 2: Extraer metadatos de cada ficha
# ---------------------------------------------------------------------------

def extract_field(soup: BeautifulSoup, label: str) -> str:
    """
    Extrae el valor de un campo buscando el contenedor elementor que tiene:
        <h2 class="elementor-heading-title">LABEL</h2>
        <div class="jet-listing-dynamic-field__content">VALOR</div>
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


# Mapeo de palabras clave del encabezado de sección al tipo de documento.
# Se evalúa en orden; la primera coincidencia gana.
_HEADING_TIPO: list[tuple[str, str]] = [
    ("resultado excma. corte suprema", "fallo_cs"),
    ("resultado excma", "fallo_cs"),
    ("corte suprema", "fallo_cs"),
    ("resultado del tdlc", "fallo_tdlc"),
    ("resultado tdlc", "fallo_tdlc"),
]


def _classify_by_context(heading_text: str, anchor_text: str, href: str) -> str:
    """Determina el tipo de un PDF a partir del contexto en el que aparece."""
    h = heading_text.lower()
    for keyword, tipo in _HEADING_TIPO:
        if keyword in h:
            return tipo

    combined = (anchor_text + " " + href).lower()
    if "rectif" in combined:
        return "rectificacion"
    if "corte suprema" in combined or href.rstrip("/").split("/")[-1].lower().endswith("_cs.pdf"):
        return "fallo_cs"
    return "desconocido"


def extract_all_pdfs(soup: BeautifulSoup) -> list[dict]:
    """
    Extrae todos los enlaces a PDFs de la ficha y los clasifica por tipo.

    Retorna una lista de dicts, cada uno con:
        'url'         → URL absoluta del PDF
        'tipo'        → 'fallo_tdlc' | 'fallo_cs' | 'rectificacion' | 'desconocido'
        'anchor_text' → texto visible del enlace
    """
    results: list[dict] = []
    seen_urls: set[str] = set()

    pdf_pattern = re.compile(r"\.pdf", re.I)

    for container in soup.find_all("div", class_=lambda c: c and "elementor-container" in c):
        heading = container.find(["h2", "h3"], class_="elementor-heading-title")
        field   = container.find("div", class_="jet-listing-dynamic-field__content")
        if not field:
            continue

        heading_text = heading.get_text(strip=True) if heading else ""

        for a in field.find_all("a", href=pdf_pattern):
            href = a["href"]
            if not href.startswith("http"):
                href = urljoin(BASE_URL, href)
            if href in seen_urls:
                continue
            seen_urls.add(href)

            anchor_text = a.get_text(strip=True)
            tipo = _classify_by_context(heading_text, anchor_text, href)
            results.append({"url": href, "tipo": tipo, "anchor_text": anchor_text})

    # Fallback: recorrer toda la página por si algún PDF está fuera de los contenedores
    for a in soup.find_all("a", href=pdf_pattern):
        href = a["href"]
        if not href.startswith("http"):
            href = urljoin(BASE_URL, href)
        if href in seen_urls:
            continue
        seen_urls.add(href)

        anchor_text = a.get_text(strip=True)
        tipo = _classify_by_context("", anchor_text, href)
        results.append({"url": href, "tipo": tipo, "anchor_text": anchor_text})

    return results


def extract_numero_from_url(url: str) -> str:
    """
    Extrae el número de resolución desde el slug de la URL.
    Ejemplo: /tdlc-resoluciones/resolucion-n-77-2023-... → 77/2023
    """
    m = re.search(r"resolucion-n[°o]?-(\d+)-(\d{4})", url, re.I)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    return ""


def parse_ficha(session: requests.Session, url: str) -> dict:
    """
    Descarga y parsea una página de ficha de resolución.
    Devuelve un dict con los metadatos extraídos.
    """
    resp = get_with_retry(
        session, url,
        extra_headers={"Referer": LISTING_URL}
    )
    if not resp:
        return {
            "numero": extract_numero_from_url(url),
            "titulo": "", "fecha": "", "caratula": "",
            "objeto": "", "resultado_tdlc": "",
            "url_pdf": "", "url_pdf_cs": "",
            "urls_pdf_adicionales": [],
            "url_ficha": url, "error": "petición fallida",
        }

    soup = BeautifulSoup(resp.text, "lxml")

    titulo = ""
    for h2 in soup.find_all("h2", class_="elementor-heading-title"):
        txt = h2.get_text(strip=True)
        if txt.lower().startswith("resoluc"):
            titulo = txt
            break

    numero = ""
    if titulo:
        m = re.search(r"N[°o]?\s*([\d/]+)", titulo, re.I)
        if m:
            numero = m.group(1)
    if not numero:
        numero = extract_numero_from_url(url)

    fecha     = extract_field(soup, "fecha de dictación")
    caratula  = extract_field(soup, "carátula")
    objeto    = extract_field(soup, "objeto del proceso")
    resultado = extract_field(soup, "resultado del tdlc")

    all_pdfs = extract_all_pdfs(soup)

    url_pdf            = ""
    url_pdf_cs         = ""
    urls_pdf_adicionales: list[dict] = []

    for pdf in all_pdfs:
        if pdf["tipo"] == "fallo_tdlc" and not url_pdf:
            url_pdf = pdf["url"]
        elif pdf["tipo"] == "fallo_cs" and not url_pdf_cs:
            url_pdf_cs = pdf["url"]
        else:
            urls_pdf_adicionales.append(pdf)

    return {
        "numero":               numero,
        "titulo":               titulo,
        "fecha":                fecha,
        "caratula":             caratula,
        "objeto":               objeto,
        "resultado_tdlc":       resultado,
        "url_pdf":              url_pdf,
        "url_pdf_cs":           url_pdf_cs,
        "urls_pdf_adicionales": urls_pdf_adicionales,  # list[dict], no se escribe al CSV directamente
        "url_ficha":            url,
        "error":                "",
    }


# ---------------------------------------------------------------------------
# Paso 3: Descargar PDFs
# ---------------------------------------------------------------------------

def download_pdf(session: requests.Session, pdf_url: str, dest_dir: Path,
                 numero: str) -> str:
    """
    Descarga el PDF principal del TDLC en dest_dir.
    Nombre: Resolucion_{numero}.pdf  (ej. Resolucion_77_2023.pdf)
    """
    if not pdf_url:
        return ""

    base = f"Resolucion_{safe_filename(numero)}" if numero else \
           safe_filename(pdf_url.split("/")[-1].replace(".pdf", ""))
    dest = dest_dir / f"{base}.pdf"

    if dest.exists():
        return str(dest)

    resp = get_with_retry(session, pdf_url, extra_headers={"Referer": BASE_URL}, stream=True)
    if not resp:
        return ""

    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    return str(dest)


def download_cs_pdf(session: requests.Session, pdf_url: str, cs_dir: Path,
                    numero: str) -> str:
    """
    Descarga la resolución de la Corte Suprema con sufijo _CS.
    """
    if not pdf_url:
        return ""

    base = f"Resolucion_{safe_filename(numero)}" if numero else \
           safe_filename(pdf_url.split("/")[-1].replace(".pdf", ""))
    dest = cs_dir / f"{base}_CS.pdf"

    if dest.exists():
        return str(dest)

    resp = get_with_retry(session, pdf_url, extra_headers={"Referer": BASE_URL}, stream=True)
    if not resp:
        return ""

    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    return str(dest)


def download_additional_pdf(session: requests.Session, pdf_url: str, dest_dir: Path,
                            numero: str, tipo: str, index: int) -> str:
    """
    Descarga un PDF adicional (rectificación u otro) en dest_dir.
    Nombre: Resolucion_{numero}_{tipo}.pdf; añade el índice si hay colisión.
    Devuelve la ruta del archivo guardado, o "" si falla.
    """
    if not pdf_url:
        return ""

    base = f"Resolucion_{safe_filename(numero)}" if numero else \
           safe_filename(pdf_url.split("/")[-1].replace(".pdf", ""))

    suffix = tipo if tipo != "desconocido" else f"adicional_{index}"
    dest = dest_dir / f"{base}_{suffix}.pdf"

    if dest.exists() and index > 0:
        dest = dest_dir / f"{base}_{suffix}_{index}.pdf"

    if dest.exists():
        return str(dest)

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
        description="Descarga resoluciones del TDLC (metadatos CSV + PDFs)"
    )
    parser.add_argument(
        "--no-pdf", action="store_true",
        help="Sólo guardar metadatos en CSV, sin descargar PDFs"
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Procesar sólo las primeras N resoluciones (0 = sin límite, útil para pruebas)"
    )
    args = parser.parse_args()

    # Crear directorios de salida
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    CS_PDF_DIR.mkdir(parents=True, exist_ok=True)
    OTROS_PDF_DIR.mkdir(parents=True, exist_ok=True)

    session = make_session()

    # --- Paso 1: Recolectar URLs del listado ---
    print("\n=== Recolectando URLs del listado ===")
    ficha_urls = collect_all_ficha_urls(session)

    if args.limit:
        ficha_urls = ficha_urls[: args.limit]
        print(f"Limitando a {args.limit} resoluciones.")

    # --- Paso 2 + 3: Procesar fichas y descargar PDFs ---
    print("\n=== Procesando fichas ===")
    rows = []
    csv_fields = [
        "numero", "titulo", "fecha", "caratula",
        "objeto", "resultado_tdlc", "url_pdf", "ruta_pdf",
        "url_pdf_cs", "ruta_pdf_cs",
        "ruta_pdfs_adicionales",
        "url_ficha", "error",
    ]

    # Control de duplicados por URL (evita doble descarga entre resoluciones)
    cs_urls_descargadas:     set[str] = set()
    adicionales_descargadas: set[str] = set()

    total_adicionales_detectados  = 0
    total_adicionales_descargados = 0

    for url in tqdm(ficha_urls, desc="Resoluciones"):
        data = parse_ficha(session, url)

        numero = data.get("numero", "")

        # --- PDF principal del TDLC ---
        ruta_pdf = ""
        if not args.no_pdf and data.get("url_pdf"):
            ruta_pdf = download_pdf(session, data["url_pdf"], PDF_DIR, numero)
            time.sleep(DELAY_PDF)
        data["ruta_pdf"] = ruta_pdf

        # --- PDF de la Corte Suprema ---
        ruta_pdf_cs = ""
        url_pdf_cs  = data.get("url_pdf_cs", "")
        if not args.no_pdf and url_pdf_cs:
            if url_pdf_cs in cs_urls_descargadas:
                ruta_pdf_cs = "[duplicado, ya descargado]"
            else:
                ruta_pdf_cs = download_cs_pdf(session, url_pdf_cs, CS_PDF_DIR, numero)
                if ruta_pdf_cs:
                    cs_urls_descargadas.add(url_pdf_cs)
                else:
                    prev = data.get("error", "")
                    data["error"] = (prev + " | error descarga PDF CS").lstrip(" | ")
                time.sleep(DELAY_PDF)
        data["ruta_pdf_cs"] = ruta_pdf_cs

        # --- PDFs adicionales ---
        rutas_adicionales: list[str] = []
        pdfs_adicionales = data.get("urls_pdf_adicionales", [])
        total_adicionales_detectados += len(pdfs_adicionales)

        if not args.no_pdf:
            tipo_counter: dict[str, int] = {}
            for pdf_info in pdfs_adicionales:
                url_adic = pdf_info["url"]
                tipo     = pdf_info["tipo"]

                tipo_counter[tipo] = tipo_counter.get(tipo, 0) + 1
                idx = tipo_counter[tipo]

                if url_adic in adicionales_descargadas:
                    rutas_adicionales.append(f"[duplicado: {url_adic}]")
                    continue

                ruta_adic = download_additional_pdf(
                    session, url_adic, OTROS_PDF_DIR, numero, tipo, idx
                )
                if ruta_adic:
                    adicionales_descargadas.add(url_adic)
                    rutas_adicionales.append(ruta_adic)
                    total_adicionales_descargados += 1
                else:
                    prev = data.get("error", "")
                    data["error"] = (
                        prev + f" | error descarga PDF adicional ({tipo})"
                    ).lstrip(" | ")
                time.sleep(DELAY_PDF)

        data["ruta_pdfs_adicionales"] = ";".join(rutas_adicionales)
        rows.append(data)

        time.sleep(DELAY_FICHA)

    # --- Guardar CSV ---
    print(f"\n=== Guardando CSV en {OUTPUT_CSV} ===")
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    # Resumen final
    total          = len(rows)
    errors         = sum(1 for r in rows if r.get("error"))
    pdfs_ok        = sum(1 for r in rows if r.get("ruta_pdf"))
    cs_detectadas  = sum(1 for r in rows if r.get("url_pdf_cs"))
    cs_descargadas = sum(
        1 for r in rows
        if r.get("ruta_pdf_cs") and r["ruta_pdf_cs"] != "[duplicado, ya descargado]"
    )
    print(
        f"\nListo. {total} resoluciones procesadas | {errors} errores\n"
        f"  PDFs TDLC:       {pdfs_ok} descargados\n"
        f"  PDFs CS:         {cs_detectadas} detectados | {cs_descargadas} descargados\n"
        f"  PDFs adicionales:{total_adicionales_detectados} detectados "
        f"| {total_adicionales_descargados} descargados"
    )
    print(f"CSV: {OUTPUT_CSV}")
    if not args.no_pdf:
        print(f"PDFs TDLC:        {PDF_DIR}")
        print(f"PDFs CS:          {CS_PDF_DIR}")
        print(f"PDFs adicionales: {OTROS_PDF_DIR}")


if __name__ == "__main__":
    main()
