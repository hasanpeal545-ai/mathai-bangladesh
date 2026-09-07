# STEP 2: OCR pages 1-8 of each of the 10 curriculum PDFs and try to parse a
# table-of-contents (chapter title + page number) out of them.
import json
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

CURRICULUM_PATH = BACKEND_DIR / "data" / "curriculum.json"
OUTPUT_PATH = BACKEND_DIR / "data" / "toc_extracted.json"
PDF_ROOT = BACKEND_DIR / "data" / "pdfs" / "2026"

BANGLA_DIGITS = "০১২৩৪৫৬৭৮৯"
_BANGLA_TO_ARABIC = str.maketrans(BANGLA_DIGITS, "0123456789")

# A TOC row looks like "<title text> <page number>" at the end of a line.
_TOC_ROW_RE = re.compile(r"^(.{3,90}?)[\s.]{1,}([0-9০-৯]{1,4})$")
_SKIP_LINE_RE = re.compile(
    r"^(20\d\d|২০২৬|CONTENTS|সূচিপত্র|Chapter\s*Title\s*Page|অধ্যায়\s*শিরোনাম\s*পৃষ্ঠা|Mathematics|গণিত)$",
    re.IGNORECASE,
)
_ANSWER_LINE_RE = re.compile(r"^(Answer|উত্তর)\b", re.IGNORECASE)


def to_page_number(token: str) -> int:
    return int(token.translate(_BANGLA_TO_ARABIC))


def ocr_pages_1_to_8(pdf_path: Path, language: str) -> str:
    lang_code = "ben" if language == "bn" else "eng"
    doc = fitz.open(str(pdf_path))
    page_count = min(8, doc.page_count)
    texts = []
    for i in range(page_count):
        pix = doc[i].get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        texts.append(pytesseract.image_to_string(img, lang=lang_code, config=TESS_CONFIG))
    return "\n".join(texts)


def parse_toc(raw_text: str) -> list:
    entries = []
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line or _SKIP_LINE_RE.match(line):
            continue
        if _ANSWER_LINE_RE.match(line):
            entries.append({"title": "__ANSWER__", "start_page": None})
            continue

        m = _TOC_ROW_RE.match(line)
        if not m:
            continue
        title, page_token = m.group(1).strip(), m.group(2)
        try:
            page_num = to_page_number(page_token)
        except ValueError:
            continue
        if page_num == 0 or page_num > 500:
            continue
        if len(title) < 3:
            continue
        entries.append({"title": title, "start_page": page_num})

    # Assign sequential chapter numbers to real (non-__ANSWER__) rows, and use
    # the next row's start_page (or the Answer marker's) as this chapter's end.
    chapters = []
    real_rows = [e for e in entries if e["title"] != "__ANSWER__"]
    for idx, row in enumerate(real_rows):
        end_page = None
        # find the next entry in the original sequence (chapter or Answer marker)
        pos = entries.index(row)
        for nxt in entries[pos + 1:]:
            if nxt["start_page"] is not None:
                end_page = nxt["start_page"] - 1
                break
            break  # __ANSWER__ marker has no page number here
        chapters.append(
            {
                "number": idx + 1,
                "title": row["title"],
                "start_page": row["start_page"],
                "end_page": end_page,
            }
        )
    return chapters


def main():
    curriculum = json.loads(CURRICULUM_PATH.read_text(encoding="utf-8"))
    results = {}

    files = []
    for book in curriculum["books"]:
        files.append((PDF_ROOT / "bangla" / book["bangla_file"], "bn"))
        files.append((PDF_ROOT / "english" / book["english_file"], "en"))

    for pdf_path, language in files:
        key = pdf_path.stem
        print(f"=== {key} ({language}) ===", flush=True)
        if not pdf_path.exists():
            print(f"  MISSING FILE: {pdf_path}")
            results[key] = {"error": "file not found", "chapters": []}
            continue

        raw_text = ocr_pages_1_to_8(pdf_path, language)
        chapters = parse_toc(raw_text)
        results[key] = {"chapters": chapters}

        if chapters:
            for ch in chapters:
                print(f"  {ch['number']}. {ch['title']!r} start={ch['start_page']} end={ch['end_page']}")
        else:
            print("  no TOC rows parsed")
        print(flush=True)

    OUTPUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
