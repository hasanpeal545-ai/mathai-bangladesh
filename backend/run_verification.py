# Double Verification pipeline: for each already-OCR'd (Tesseract) page, get a
# second opinion from Gemini Vision, then merge — Gemini's prose as the base,
# with Tesseract's numbers substituted in wherever we can confidently align them
# (Tesseract proved more reliable on digits in earlier manual comparisons this
# project ran; Gemini reads noisy/garbled words better).
import difflib
import io
import json
import re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import fitz
from PIL import Image
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

from config import settings

BACKEND_DIR = Path(__file__).resolve().parent
CURRICULUM_PATH = BACKEND_DIR / "data" / "curriculum.json"
PDF_ROOT = BACKEND_DIR / "data" / "pdfs" / "2026"
OCR_RAW_DIR = BACKEND_DIR / "data" / "ocr_raw"
OCR_VERIFIED_DIR = BACKEND_DIR / "data" / "ocr_verified"

REQUESTS_PER_MINUTE = 14
SLEEP_BETWEEN_REQUESTS = 60.0 / REQUESTS_PER_MINUTE  # ~4.3s
DAILY_LIMIT = 1500

# Matches a run of digits (Bangla or Arabic), optionally with one "." or "/"
# joining a second run — covers plain integers, decimals, and fractions
# ("৩৬৭", "৩.৪", "১/২", "৮৭৪৩২০").
NUMBER_RE = re.compile(r"[০-৯0-9]+(?:[./][০-৯0-9]+)?")

GEMINI_PROMPT = (
    "এটি বাংলাদেশের NCTB গণিত পাঠ্যবইয়ের একটি পৃষ্ঠা।\n"
    "এই পৃষ্ঠার সম্পূর্ণ টেক্সট হুবহু বের করো।\n"
    "নিয়ম:\n"
    "- বাংলা text সঠিকভাবে লেখো\n"
    "- গণিত চিহ্ন সঠিক রাখো: × ÷ = > < ≥ ≤ ∈ ∪ ∩ ∅ ∴\n"
    "- কোনো markdown বা table করবে না\n"
    "- শুধু plain text দাও"
)

genai.configure(api_key=settings.gemini_api_key)
_model = genai.GenerativeModel("gemini-1.5-flash")

_daily_request_count = 0
_daily_window_start = time.time()


def throttle_daily_limit() -> None:
    """Proactively pace requests to the 1,500/day free-tier budget for
    gemini-1.5-flash, independent of the reactive ResourceExhausted retry
    below (that one handles transient/per-minute errors on top of this)."""
    global _daily_request_count, _daily_window_start
    now = time.time()
    if now - _daily_window_start >= 86400:
        _daily_request_count = 0
        _daily_window_start = now
    if _daily_request_count >= DAILY_LIMIT:
        wait_s = 86400 - (now - _daily_window_start)
        print(f"  daily limit of {DAILY_LIMIT} reached, sleeping {wait_s / 3600:.1f}h", flush=True)
        time.sleep(max(wait_s, 1))
        _daily_request_count = 0
        _daily_window_start = time.time()
    _daily_request_count += 1


def merge_texts(gemini_text: str, tesseract_text: str) -> str:
    """Gemini text is the base. Numbers found in Gemini are swapped for the
    positionally-corresponding Tesseract number wherever difflib can align
    the two number sequences with confidence (equal/replace blocks). Where
    Gemini has a number with no confident Tesseract counterpart, Gemini's own
    number is kept (nothing trustworthy to substitute). Extra Tesseract
    numbers with no slot in Gemini's text have nowhere to go and are dropped
    — this only rewrites numbers already present in the Gemini text.
    """
    tess_numbers = NUMBER_RE.findall(tesseract_text)
    gemini_matches = list(NUMBER_RE.finditer(gemini_text))
    gemini_numbers = [m.group() for m in gemini_matches]

    replacement = {}
    matcher = difflib.SequenceMatcher(None, gemini_numbers, tess_numbers)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("equal", "replace"):
            length = min(i2 - i1, j2 - j1)
            for k in range(length):
                replacement[i1 + k] = tess_numbers[j1 + k]

    pieces = []
    last_end = 0
    for idx, m in enumerate(gemini_matches):
        pieces.append(gemini_text[last_end : m.start()])
        pieces.append(replacement.get(idx, m.group()))
        last_end = m.end()
    pieces.append(gemini_text[last_end:])
    return "".join(pieces)


def page_image(pdf_path: Path, page_index: int) -> Image.Image:
    doc = fitz.open(str(pdf_path))
    page = doc[page_index]
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    img_bytes = pix.tobytes("png")
    return Image.open(io.BytesIO(img_bytes))


def call_gemini(image: Image.Image) -> str:
    while True:
        throttle_daily_limit()
        try:
            response = _model.generate_content([GEMINI_PROMPT, image])
            return response.text
        except ResourceExhausted as e:
            print(f"  quota exceeded, waiting 60s, retrying same page: {e}", flush=True)
            time.sleep(60)
        except Exception as e:
            print(f"  gemini error ({type(e).__name__}), waiting 60s, retrying same page: {e}", flush=True)
            time.sleep(60)


def verify_file(stem: str, pdf_path: Path) -> None:
    raw_dir = OCR_RAW_DIR / stem
    out_dir = OCR_VERIFIED_DIR / stem
    out_dir.mkdir(parents=True, exist_ok=True)

    page_files = sorted(raw_dir.glob("page_*.txt"), key=lambda p: int(p.stem.split("_")[1]))
    total = len(page_files)

    for page_file in page_files:
        page_num = int(page_file.stem.split("_")[1])
        out_path = out_dir / f"page_{page_num}.txt"
        if out_path.exists():
            continue

        tesseract_text = page_file.read_text(encoding="utf-8")
        image = page_image(pdf_path, page_num - 1)
        gemini_text = call_gemini(image)
        merged = merge_texts(gemini_text, tesseract_text)
        out_path.write_text(merged, encoding="utf-8")

        time.sleep(SLEEP_BETWEEN_REQUESTS)

        if page_num % 50 == 0 or page_num == total:
            print(f"{stem}: {page_num}/{total} verified", flush=True)

    print(f"✅ {stem} DONE", flush=True)


def main():
    curriculum = json.loads(CURRICULUM_PATH.read_text(encoding="utf-8"))
    jobs = []
    for book in curriculum["books"]:
        jobs.append(PDF_ROOT / "bangla" / book["bangla_file"])
        jobs.append(PDF_ROOT / "english" / book["english_file"])

    for pdf_path in jobs:
        stem = pdf_path.stem
        try:
            verify_file(stem, pdf_path)
        except Exception as e:
            print(f"❌❌ {stem} FILE-LEVEL FAILURE: {type(e).__name__}: {e}", flush=True)

    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
