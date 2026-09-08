# STEP 3: Full OCR of all 10 curriculum PDFs (bangla lang="ben", english lang="eng"),
# 2x zoom, one .txt file per page under data/ocr_raw/{filename}/page_{n}.txt.
import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import fitz
import pytesseract
from PIL import Image

PAGE_RETRY_ATTEMPTS = 2
PAGE_RETRY_DELAY_S = 3

BACKEND_DIR = Path(__file__).resolve().parent
TESSDATA_DIR = BACKEND_DIR / "data" / "tessdata"
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
TESS_CONFIG = f"--tessdata-dir {TESSDATA_DIR} --psm 3"

PDF_ROOT = BACKEND_DIR / "data" / "pdfs" / "2026"
OCR_RAW_DIR = BACKEND_DIR / "data" / "ocr_raw"
CURRICULUM_PATH = BACKEND_DIR / "data" / "curriculum.json"

# Legacy/alternate folder names to also check for the "already processed, skip" rule.
ALT_NAMES = {
    "class_9_General_math_bn": ["class_9_math_bn"],
}


def already_done(stem: str, expected_pages: int) -> bool:
    for name in [stem] + ALT_NAMES.get(stem, []):
        folder = OCR_RAW_DIR / name
        if folder.is_dir() and len(list(folder.glob("page_*.txt"))) >= expected_pages:
            return True
    return False


def ocr_pdf(pdf_path: Path, language: str, stem: str) -> int:
    lang_code = "ben" if language == "bn" else "eng"
    doc = fitz.open(str(pdf_path))
    total = doc.page_count
    out_dir = OCR_RAW_DIR / stem
    out_dir.mkdir(parents=True, exist_ok=True)

    done_count = 0
    for i in range(total):
        page_num = i + 1
        out_path = out_dir / f"page_{page_num}.txt"
        if not out_path.exists():
            pix = doc[i].get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            text = None
            last_error = None
            for attempt in range(1, PAGE_RETRY_ATTEMPTS + 1):
                try:
                    text = pytesseract.image_to_string(img, lang=lang_code, config=TESS_CONFIG)
                    break
                except Exception as e:
                    last_error = e
                    print(
                        f"  ⚠️ {stem} page {page_num}: OCR failed (attempt {attempt}/{PAGE_RETRY_ATTEMPTS}): "
                        f"{type(e).__name__}",
                        flush=True,
                    )
                    time.sleep(PAGE_RETRY_DELAY_S)

            if text is None:
                text = f"[OCR_FAILED: {type(last_error).__name__}: {last_error}]"
                print(f"  ❌ {stem} page {page_num}: giving up, wrote error placeholder", flush=True)

            out_path.write_text(text, encoding="utf-8")
        done_count += 1

        if page_num % 10 == 0 or page_num == total:
            print(f"{stem}: {page_num}/{total} pages done", flush=True)
        if page_num % 50 == 0:
            print(f"CHECKPOINT {stem}: {page_num}/{total}", flush=True)

    print(f"\u2705 {stem} DONE \u2014 {total} pages", flush=True)
    return done_count


def main():
    curriculum = json.loads(CURRICULUM_PATH.read_text(encoding="utf-8"))
    jobs = []
    for book in curriculum["books"]:
        jobs.append((PDF_ROOT / "bangla" / book["bangla_file"], "bn"))
        jobs.append((PDF_ROOT / "english" / book["english_file"], "en"))

    start_time = time.time()
    files_processed = 0
    files_skipped = 0
    total_pages_processed = 0

    for pdf_path, language in jobs:
        stem = pdf_path.stem
        doc = fitz.open(str(pdf_path))
        expected_pages = doc.page_count

        if already_done(stem, expected_pages):
            print(f"\u23ed\ufe0f  {stem} SKIPPED \u2014 already has {expected_pages}+ pages in ocr_raw", flush=True)
            files_skipped += 1
            continue

        print(f"--- starting {stem} ({language}, {expected_pages} pages) ---", flush=True)
        try:
            pages_done = ocr_pdf(pdf_path, language, stem)
            files_processed += 1
            total_pages_processed += pages_done
        except Exception as e:
            print(f"❌❌ {stem} FILE-LEVEL FAILURE: {type(e).__name__}: {e}", flush=True)
            print(f"--- skipping to next file ---", flush=True)

    elapsed_min = (time.time() - start_time) / 60
    print("\n=== SUMMARY ===", flush=True)
    print(f"Total files: {len(jobs)}", flush=True)
    print(f"Files newly processed: {files_processed}", flush=True)
    print(f"Files skipped (already done): {files_skipped}", flush=True)
    print(f"Total pages processed: {total_pages_processed}", flush=True)
    print(f"Time taken: {elapsed_min:.1f} minutes", flush=True)


if __name__ == "__main__":
    main()
