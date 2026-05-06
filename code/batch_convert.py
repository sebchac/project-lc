# batch_convert.py
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from markitdown import MarkItDown

INPUT_DIR = Path('raw/sentencias-tdlc/') # CHANGE WHEN USED 
OUTPUT_DIR = Path('build/sentencias-tdlc-md/') # <- CHANGE WHEN USED
WORKERS = 4 
SKIP_DONE = True

logging.basicConfig(filename='conversion_errors.log',
                    level=logging.ERROR,
                    format='%(asctime)s %(message)s')

def convert_one(pdf_path):
    relative = pdf_path.relative_to(INPUT_DIR)
    out_path = OUTPUT_DIR / relative.with_suffix('.md')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if SKIP_DONE and out_path.exists():
        return pdf_path, True, 'skipped'
    try:
        result = MarkItDown(enable_plugins=False).convert(str(pdf_path))
        out_path.write_text(result.text_content, encoding='utf-8')
        return pdf_path, True, 'ok'
    except Exception as e:
        logging.error(f'{pdf_path}: {e}')
        return pdf_path, False, str(e)
    
def main(): 
    pdfs = sorted(INPUT_DIR.rglob('*.pdf')) 
    total = len(pdfs) 
    if total == 0: 
        print('No PDFs found.') 
        return 
    done = skipped = failed = 0 
    with ThreadPoolExecutor(max_workers=WORKERS) as pool: 
        futures = {pool.submit(convert_one, p): p for p in pdfs} 
        for i, future in enumerate(as_completed(futures), 1): 
            _, ok, status = future.result() 
            if status == 'skipped': skipped += 1 
            elif ok: done += 1 
            else: failed += 1 
            bar = '█'*int(30*i/total) + '░'*(30-int(30*i/total)) 
            print(f'\r[{bar}] {i}/{total} '
                    f'done={done} skipped={skipped} failed={failed}',
                    end='', flush=True)
    print(f'\nDone. {done} converted, {skipped} skipped, {failed} failed')

if __name__ == '__main__':
    main()