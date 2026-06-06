# batch_convert_ocr.py
"""
Conversor OCR para PDFs escaneados que MarkItDown no pudo procesar.

Requisitos (instalar antes de ejecutar):
    brew install tesseract tesseract-lang
    pip install pymupdf pytesseract

Uso:
    cd /Users/chac/Documents/GitHub/project-lc
    python3 code/batch_convert_ocr.py

Por defecto solo procesa el corpus judicial (TDLC + CS).
Para incluir FNE, descomentar las líneas correspondientes en TARGET_PAIRS.
"""

import io
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

RAW_DIR     = Path('raw')
RAW_MD_DIR  = Path('raw-md')

# Pares (subcarpeta en raw/, subcarpeta en raw-md/) a procesar.
# Comentar los que no quieras incluir.
TARGET_PAIRS = [
    ('sentencias-tdlc',   'sentencias-tdlc-md'),
    ('sentencias-cs',     'sentencias-cs-md'),
    ('resoluciones-tdlc', 'resoluciones-tdlc-md'),
    ('resoluciones-cs',   'resoluciones-cs-md'),
    ('normativa-fusiones-fne', 'normativa-fusiones-fne-md')
    # ('investigaciones-fne', 'investigaciones-fne-md'),  # desactivado por ahora
]

MIN_WORDS  = 50   # archivos con menos palabras se consideran fallidos
DPI        = 300  # resolución de renderizado de páginas (mayor = mejor OCR, más lento)
OCR_LANG   = 'spa'
WORKERS    = 2    # OCR es intensivo en CPU; no subir mucho

logging.basicConfig(
    filename='ocr_errors.log',
    level=logging.ERROR,
    format='%(asctime)s %(levelname)s %(message)s'
)

# ---------------------------------------------------------------------------
# Funciones
# ---------------------------------------------------------------------------

def word_count(path: Path) -> int:
    try:
        return len(path.read_text(encoding='utf-8', errors='ignore').split())
    except Exception:
        return 0


def needs_ocr(md_path: Path) -> bool:
    if not md_path.exists() or md_path.stat().st_size == 0:
        return True
    return word_count(md_path) < MIN_WORDS


def ocr_pdf(pdf_path: Path) -> str:
    import fitz          # pymupdf
    import pytesseract
    from PIL import Image

    doc = fitz.open(str(pdf_path))
    pages = []
    mat = fitz.Matrix(DPI / 72, DPI / 72)

    for i, page in enumerate(doc, 1):
        pix  = page.get_pixmap(matrix=mat)
        img  = Image.open(io.BytesIO(pix.tobytes('png')))
        text = pytesseract.image_to_string(img, lang=OCR_LANG, config='--psm 1')
        if text.strip():
            pages.append(text.strip())

    doc.close()
    return '\n\n---\n\n'.join(pages)


def convert_one(pdf_path: Path, md_path: Path):
    try:
        text = ocr_pdf(pdf_path)
        if not text.strip():
            return pdf_path, False, 'OCR sin resultado'
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(text, encoding='utf-8')
        return pdf_path, True, f'{len(text.split())} palabras'
    except Exception as e:
        logging.error(f'{pdf_path}: {e}')
        return pdf_path, False, str(e)


def find_candidates():
    candidates = []
    for raw_sub, md_sub in TARGET_PAIRS:
        for pdf_path in sorted((RAW_DIR / raw_sub).rglob('*.pdf')):
            relative = pdf_path.relative_to(RAW_DIR / raw_sub)
            md_path  = RAW_MD_DIR / md_sub / relative.with_suffix('.md')
            if needs_ocr(md_path):
                candidates.append((pdf_path, md_path))
    return candidates


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Verificar dependencias antes de empezar
    try:
        import fitz
        import pytesseract
        pytesseract.get_tesseract_version()
    except ImportError as e:
        print(f"Falta una dependencia Python: {e}")
        print("Instala con: pip install pymupdf pytesseract")
        return
    except Exception:
        print("Tesseract no encontrado. Instala con: brew install tesseract tesseract-lang")
        return

    print("Detectando archivos que necesitan OCR...")
    candidates = find_candidates()

    if not candidates:
        print("No se encontraron archivos que necesiten OCR en los directorios configurados.")
        return

    print(f"\n{len(candidates)} archivo(s) a procesar:\n")
    for pdf, md in candidates:
        if not md.exists():
            estado = 'no existe'
        elif md.stat().st_size == 0:
            estado = 'vacío'
        else:
            estado = f'{word_count(md)} palabras (insuficiente)'
        print(f"  {pdf.parent.name}/{pdf.name}  [{estado}]")

    print()
    confirm = input(f"¿Proceder con OCR en {len(candidates)} archivos? (s/n): ").strip().lower()
    if confirm != 's':
        print("Cancelado.")
        return

    done = failed = 0
    total = len(candidates)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(convert_one, pdf, md): pdf for pdf, md in candidates}
        for i, future in enumerate(as_completed(futures), 1):
            _, ok, status = future.result()
            if ok:
                done += 1
            else:
                failed += 1
                logging.error(f'failed: {status}')
            bar = '█' * int(30 * i / total) + '░' * (30 - int(30 * i / total))
            print(f'\r[{bar}] {i}/{total}  ok={done}  fallidos={failed}', end='', flush=True)

    print(f'\n\nListo. {done} convertidos, {failed} fallidos.')
    if failed:
        print('Ver detalles en ocr_errors.log')


if __name__ == '__main__':
    main()
