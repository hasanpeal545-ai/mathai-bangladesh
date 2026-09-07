# One-off diagnostic: for every PDF in data/pdfs/2026/{bangla,english}/, OCR page 10
# and report whether the text is actually Bangla script or English.
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import fitz
import pytesseract
from PIL import Image

BACKEND_DIR = Path(__file__).resolve().parent
TESSDATA_DIR = BACKEND_DIR / "data" / "tessdata"
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
TESS_CONFIG = f"--tessdata-dir {TESSDATA_DIR} --psm 3"

BENGALI_RE = re.compile(r"[\u0980-\u09FF]")
LATIN_RE = re.compile(r"[A-Za-z]")

PDF_DIRS = [
    BACKEND_DIR / "data" / "pdfs" / "2026" / "bangla",
    BACKEND_DIR / "data" / "pdfs" / "2026" / "english",
]

for folder in PDF_DIRS:
    print(f"=== {folder.relative_to(BACKEND_DIR)} ===")
    pdf_files = sorted(folder.glob("*.pdf"))
    for pdf_path in pdf_files:
        try:
            doc = fitz.open(str(pdf_path))
            if doc.page_count < 10:
                print(f"{pdf_path.name}: only {doc.page_count} pages, no page 10")
                continue
            page = doc[9]  # page 10
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = pytesseract.image_to_string(img, lang="ben+eng", config=TESS_CONFIG)

            bengali_count = len(BENGALI_RE.findall(text))
            latin_count = len(LATIN_RE.findall(text))
            language = "Bangla script" if bengali_count > latin_count else "English"

            snippet = text.strip().replace("\n", " ")[:100]
            print(f"{pdf_path.name}: {language} (bn_chars={bengali_count}, latin_chars={latin_count})")
            print(f"  page 10 snippet: {snippet!r}")
        except Exception as e:
            print(f"{pdf_path.name}: ERROR - {type(e).__name__}: {e}")
    print()
