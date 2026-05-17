"""
sentencias-tdlc.py
==================
Descarga todas las sentencias del Tribunal de Defensa de la Libre Competencia
(TDLC) desde https://www.tdlc.cl/sentencia/

Estrategia de scraping:
  1. El listado usa Search & Filter + JetEngine. Las páginas se obtienen vía una
     API AJAX que devuelve JSON con HTML embebido.
     Endpoint: GET https://www.tdlc.cl/?sfid=38813&sf_action=get_data&sf_data=results&sf_paged=N
     Header requerido: X-Requested-With: XMLHttpRequest

  2. Por cada ficha (/tdlc-sentencias/SLUG/) se extrae:
     - Número de sentencia  (del primer <h2> de título)
     - Fecha de dictación   (campo "FECHA DE DICTACIÓN:")
     - Carátula             (campo "carátula:")
     - Rol de causa         (clase CSS del wrapper del post)
     - Resultado del TDLC   (texto + enlace PDF)
     - Todos los PDFs de la ficha, clasificados por tipo:
         'fallo_tdlc'    → resultado del TDLC
         'fallo_cs'      → resultado Excma. Corte Suprema
         'rectificacion' → rectificaciones/aclaraciones
         'desconocido'   → cualquier otro PDF
     - URL de la ficha

  3. Los PDFs se guardan según su tipo:
       raw/sentencias-tdlc/          → PDFs del TDLC (principal)
       raw/sentencias-cs/            → PDFs de la Corte Suprema
       raw/sentencias-tdlc/otros/    → PDFs adicionales (rectificaciones, etc.)

Uso:
    pip install requests beautifulsoup4 lxml tqdm
    python sentencias-tdlc.py

    # Sólo metadatos, sin descargar PDFs:
    python sentencias-tdlc.py --no-pdf

    # Procesar sólo primeras N sentencias (útil para pruebas):
    python sentencias-tdlc.py --limit 10
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

# Endpoint de la API Search & Filter (descubierto inspeccionando el HTML fuente)
LISTING_API = (
    "https://www.tdlc.cl/?sfid=38813&sf_action=get_data&sf_data=results&sf_paged={page}"
)

OUTPUT_CSV = Path(__file__).parent.parent / "raw" / "sentencias-tdlc" / "sentencias-tdlc.csv"
PDF_DIR    = Path(__file__).parent.parent / "raw" / "sentencias-tdlc"
CS_PDF_DIR = Path(__file__).parent.parent / "raw" / "sentencias-cs"
OTROS_PDF_DIR = PDF_DIR / "otros"

# Pausa entre peticiones (segundos) — respeta el servidor
DELAY_LISTING = 1.0   # entre páginas del listado
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
    """GET con reintentos. Devuelve None si falla definitivamente."""
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
    Obtiene el número total de páginas desde la primera respuesta de la API.
    La respuesta JSON contiene HTML con el texto "Page N of M".
    """
    url = LISTING_API.format(page=1)
    resp = get_with_retry(
        session, url,
        extra_headers={"X-Requested-With": "XMLHttpRequest",
                       "Referer": f"{BASE_URL}/sentencia/"}
    )
    if not resp:
        raise RuntimeError("No se pudo acceder a la API del listado.")

    data = resp.json()
    html = data.get("results", "")
    match = re.search(r"Page \d+ of (\d+)", html)
    if match:
        return int(match.group(1))

    # Fallback: contar páginas en los links de paginación
    soup = BeautifulSoup(html, "lxml")
    paged_links = [
        int(m)
        for a in soup.find_all("a", href=re.compile(r"sf_paged=(\d+)"))
        for m in re.findall(r"sf_paged=(\d+)", a["href"])
    ]
    return max(paged_links, default=1)


def scrape_listing_page(session: requests.Session, page: int) -> list[dict]:
    """
    Extrae las entradas de una página del listado.
    Devuelve lista de dicts con 'url' y 'date_listing' (fecha del listado, dd/mm/yyyy).
    """
    url = LISTING_API.format(page=page)
    resp = get_with_retry(
        session, url,
        extra_headers={"X-Requested-With": "XMLHttpRequest",
                       "Referer": f"{BASE_URL}/sentencia/"}
    )
    if not resp:
        return []

    data = resp.json()
    html = data.get("results", "")
    soup = BeautifulSoup(html, "lxml")

    entries = []
    for h2 in soup.find_all("h2"):
        a = h2.find("a", href=True)
        if not a or "tdlc-sentencias" not in a["href"]:
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
    """
    Itera todas las páginas del listado y devuelve la lista completa de fichas.
    """
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
    Los campos tienen estructura:
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

    # Sin encabezado reconocido: intentar inferir del texto del enlace o del nombre del archivo
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
            if href.startswith("/"):
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
        if href.startswith("/"):
            href = urljoin(BASE_URL, href)
        if href in seen_urls:
            continue
        seen_urls.add(href)

        anchor_text = a.get_text(strip=True)
        tipo = _classify_by_context("", anchor_text, href)
        results.append({"url": href, "tipo": tipo, "anchor_text": anchor_text})

    return results


def extract_rol(soup: BeautifulSoup) -> str:
    """
    El rol de causa está en las clases CSS del wrapper del post, como:
        rol-de-causa-sent-c-446-22  →  C-446-22
    """
    wrapper = soup.find("div", class_=lambda c: c and "elementor-location-single" in c)
    if wrapper:
        for cls in wrapper.get("class", []):
            if cls.startswith("rol-de-causa-sent-"):
                raw = cls.replace("rol-de-causa-sent-", "")
                return raw.upper()
    return ""


def parse_ficha(session: requests.Session, url: str) -> dict:
    """
    Descarga y parsea una página de ficha individual.
    Devuelve un dict con todos los campos de metadatos.
    """
    resp = get_with_retry(
        session, url,
        extra_headers={"Referer": f"{BASE_URL}/sentencia/"}
    )
    if not resp:
        return {"url_ficha": url, "error": "petición fallida"}

    soup = BeautifulSoup(resp.text, "lxml")

    numero = ""
    for h2 in soup.find_all("h2", class_="elementor-heading-title"):
        txt = h2.get_text(strip=True)
        if txt.lower().startswith("sentencia"):
            numero = txt
            break

    fecha     = extract_field(soup, "fecha de dictación")
    caratula  = extract_field(soup, "carátula")
    rol       = extract_rol(soup)
    resultado = extract_field(soup, "resultado del tdlc")

    all_pdfs = extract_all_pdfs(soup)

    # Separar por tipo: el primero de cada tipo principal es el canónico
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
        "numero":                numero,
        "fecha":                 fecha,
        "caratula":              caratula,
        "rol":                   rol,
        "resultado_tdlc":        resultado,
        "url_pdf":               url_pdf,
        "url_pdf_cs":            url_pdf_cs,
        "urls_pdf_adicionales":  urls_pdf_adicionales,  # list[dict], no se escribe al CSV directamente
        "url_ficha":             url,
        "error":                 "",
    }


# ---------------------------------------------------------------------------
# Paso 3: Descargar PDFs
# ---------------------------------------------------------------------------

def download_pdf(session: requests.Session, pdf_url: str, dest_dir: Path,
                 numero: str) -> str:
    """
    Descarga un PDF del TDLC y lo guarda en dest_dir.
    Devuelve la ruta del archivo guardado, o "" si falla.
    """
    if not pdf_url:
        return ""

    base = safe_filename(numero.split(":")[0].strip()) if numero else \
           safe_filename(pdf_url.split("/")[-1].replace(".pdf", ""))
    dest = dest_dir / f"{base}.pdf"

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


def download_cs_pdf(session: requests.Session, pdf_url: str, cs_dir: Path,
                    numero: str) -> str:
    """
    Descarga la sentencia de la Corte Suprema y la guarda con sufijo "_CS".
    """
    if not pdf_url:
        return ""

    base = safe_filename(numero.split(":")[0].strip()) if numero else \
           safe_filename(pdf_url.split("/")[-1].replace(".pdf", ""))
    dest = cs_dir / f"{base}_CS.pdf"

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


def download_additional_pdf(session: requests.Session, pdf_url: str, dest_dir: Path,
                            numero: str, tipo: str, index: int) -> str:
    """
    Descarga un PDF adicional (rectificación u otro) en dest_dir.
    El nombre de archivo usa el número de sentencia + sufijo derivado del tipo.
    Devuelve la ruta del archivo guardado, o "" si falla.
    """
    if not pdf_url:
        return ""

    base = safe_filename(numero.split(":")[0].strip()) if numero else \
           safe_filename(pdf_url.split("/")[-1].replace(".pdf", ""))

    suffix = tipo if tipo != "desconocido" else f"adicional_{index}"
    dest = dest_dir / f"{base}_{suffix}.pdf"

    # Si ya existe con este nombre, añadir índice para no sobrescribir
    if dest.exists() and index > 0:
        dest = dest_dir / f"{base}_{suffix}_{index}.pdf"

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
        description="Descarga sentencias del TDLC (metadatos + PDFs)"
    )
    parser.add_argument(
        "--no-pdf", action="store_true",
        help="No descargar archivos PDF, sólo guardar metadatos en CSV"
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Limitar a las primeras N sentencias (0 = sin límite, útil para pruebas)"
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
    ficha_entries = collect_all_ficha_urls(session)

    if args.limit:
        ficha_entries = ficha_entries[: args.limit]
        print(f"Limitando a {args.limit} sentencias.")

    # --- Paso 2: Procesar fichas + Paso 3: Descargar PDFs ---
    print("\n=== Procesando fichas ===")
    rows = []
    csv_fields = [
        "numero", "fecha", "caratula", "rol",
        "resultado_tdlc", "url_pdf", "ruta_pdf",
        "url_pdf_cs", "ruta_pdf_cs",
        "ruta_pdfs_adicionales",
        "url_ficha", "error",
    ]

    # Control de duplicados por URL (evita doble descarga entre sentencias)
    cs_urls_descargadas:      set[str] = set()
    adicionales_descargadas:  set[str] = set()

    total_adicionales_detectados  = 0
    total_adicionales_descargados = 0

    for entry in tqdm(ficha_entries, desc="Sentencias"):
        data = parse_ficha(session, entry["url"])

        if not data.get("fecha") and entry.get("date_listing"):
            data["fecha"] = entry["date_listing"]

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
        pdfs_adicionales  = data.get("urls_pdf_adicionales", [])
        total_adicionales_detectados += len(pdfs_adicionales)

        if not args.no_pdf:
            tipo_counter: dict[str, int] = {}
            for pdf_info in pdfs_adicionales:
                url_adic = pdf_info["url"]
                tipo     = pdf_info["tipo"]

                tipo_counter[tipo] = tipo_counter.get(tipo, 0) + 1
                idx = tipo_counter[tipo]

                if url_adic in adicionales_descargadas:
                    # Buscar la ruta existente para registrarla
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

    # Resumen
    total        = len(rows)
    errors       = sum(1 for r in rows if r.get("error"))
    pdfs_ok      = sum(1 for r in rows if r.get("ruta_pdf"))
    cs_detectadas  = sum(1 for r in rows if r.get("url_pdf_cs"))
    cs_descargadas = sum(
        1 for r in rows
        if r.get("ruta_pdf_cs") and r["ruta_pdf_cs"] != "[duplicado, ya descargado]"
    )
    print(
        f"\nListo. {total} sentencias procesadas | {errors} errores\n"
        f"  PDFs TDLC:       {pdfs_ok} descargados\n"
        f"  PDFs CS:         {cs_detectadas} detectados | {cs_descargadas} descargados\n"
        f"  PDFs adicionales:{total_adicionales_detectados} detectados "
        f"| {total_adicionales_descargados} descargados"
    )
    print(f"CSV: {OUTPUT_CSV}")
    if not args.no_pdf:
        print(f"PDFs TDLC:      {PDF_DIR}")
        print(f"PDFs CS:        {CS_PDF_DIR}")
        print(f"PDFs adicionales: {OTROS_PDF_DIR}")


if __name__ == "__main__":
    main()
