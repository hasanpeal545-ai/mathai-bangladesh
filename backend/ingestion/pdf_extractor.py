# NCTB PDF text extraction
#
# The NCTB PDFs are scanned page images with no embedded text layer (verified: 0 extractable
# characters across every page tested). Text must come from OCR (Tesseract), which is good on
# plain paragraph text (~95%+) but noticeably degrades on math notation (fractions, set symbols
# like ∈/∩/∪, some digits) — see CLAUDE.md "Known Issues" for the measured before/after examples.
import difflib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import fitz
import pytesseract
from groq import Groq
from PIL import Image

from config import settings

_BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = _BACKEND_DIR / "data"
TESSDATA_DIR = DATA_DIR / "tessdata"
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

OCR_RAW_DIR = DATA_DIR / "ocr_raw"
OCR_FIXED_DIR = DATA_DIR / "ocr_fixed"
COMPARISON_DIR = DATA_DIR / "comparison"
APPROVED_DIR = DATA_DIR / "approved"

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
_groq_client = Groq(api_key=settings.groq_api_key)

_MATH_FIX_PROMPT = (
    "তুমি Bangladesh SSC Math expert। এই OCR text এ শুধু math notation ঠিক করো। যেমন:\n"
    "x2 → x²\n"
    "l → 1 (যদি সংখ্যা হয়)\n"
    "1/2 → ½\n"
    "sqrt → √\n"
    "... → ∴\n"
    "শুধু corrected text দাও। অন্য কিছু লিখবে না।\n\n"
)

_BANGLA_TO_ARABIC_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

# Bangla (folder: bangla/)
_CHAPTER_RE_BN = re.compile(r"অধ্যায়\s*[:.,।]?\s*([০-৯]+|\d+)")
_EXERCISE_RE_BN = re.compile(r"অনুশীলনী\s*([০-৯]+|\d+)\s*[.।]\s*([০-৯]+|\d+)")
_PROBLEM_RE_BN = re.compile(r"^\s*(?:উদাহরণ\s*)?([০-৯]+|\d+)\s*[.।:]\s+", re.MULTILINE)

# English (folder: english/)
_CHAPTER_RE_EN = re.compile(r"Chapter\s*[:.,]?\s*(\d+)", re.IGNORECASE)
_EXERCISE_RE_EN = re.compile(r"Exercise\s*(\d+)\s*\.\s*(\d+)", re.IGNORECASE)
_PROBLEM_RE_EN = re.compile(r"^\s*(?:Example\s*)?(\d+)\s*[.:]\s+", re.MULTILINE)


def detect_language(pdf_path: Path) -> str:
    parts = [p.lower() for p in pdf_path.parts]
    if "bangla" in parts:
        return "bn"
    if "english" in parts:
        return "en"
    raise ValueError(f"cannot detect language from path (expected a 'bangla' or 'english' folder): {pdf_path}")


def detect_class_number(pdf_path: Path) -> Optional[int]:
    match = re.search(r"class_(\d+)", pdf_path.name)
    return int(match.group(1)) if match else None


def _to_int(number_text: str) -> int:
    return int(number_text.translate(_BANGLA_TO_ARABIC_DIGITS))


def ocr_page(page: "fitz.Page", language: str, dpi: int = 300) -> str:
    lang_code = "ben" if language == "bn" else "eng"
    pix = page.get_pixmap(dpi=dpi)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    tess_config = f"--tessdata-dir {TESSDATA_DIR} --psm 3"
    return pytesseract.image_to_string(img, lang=lang_code, config=tess_config)


def extract_all_text(pdf_path: Path, language: str, dpi: int = 300, max_pages: Optional[int] = None) -> str:
    doc = fitz.open(str(pdf_path))
    page_count = doc.page_count if max_pages is None else min(max_pages, doc.page_count)
    pages_text = [ocr_page(doc[i], language, dpi=dpi) for i in range(page_count)]
    return "\n".join(pages_text)


@dataclass
class MathChunk:
    class_number: Optional[int]
    chapter: Optional[int]
    exercise: Optional[str]  # e.g. "2.2"
    language: str
    content: str


def chunk_text(full_text: str, language: str, class_number: Optional[int]) -> List[MathChunk]:
    if language == "bn":
        chapter_re, exercise_re, problem_re = _CHAPTER_RE_BN, _EXERCISE_RE_BN, _PROBLEM_RE_BN
    else:
        chapter_re, exercise_re, problem_re = _CHAPTER_RE_EN, _EXERCISE_RE_EN, _PROBLEM_RE_EN

    markers = (
        [(m.start(), "chapter", _to_int(m.group(1))) for m in chapter_re.finditer(full_text)]
        + [
            (m.start(), "exercise", f"{_to_int(m.group(1))}.{_to_int(m.group(2))}")
            for m in exercise_re.finditer(full_text)
        ]
        + [(m.start(), "problem", None) for m in problem_re.finditer(full_text)]
    )
    markers.sort(key=lambda item: item[0])

    chunks: List[MathChunk] = []
    current_chapter: Optional[int] = None
    current_exercise: Optional[str] = None
    pending_start: Optional[int] = None
    pending_chapter: Optional[int] = None
    pending_exercise: Optional[str] = None

    def flush(end_pos: int) -> None:
        nonlocal pending_start
        if pending_start is not None:
            content = full_text[pending_start:end_pos].strip()
            if len(content) >= 5:
                chunks.append(
                    MathChunk(
                        class_number=class_number,
                        chapter=pending_chapter,
                        exercise=pending_exercise,
                        language=language,
                        content=content,
                    )
                )
        pending_start = None

    for pos, kind, value in markers:
        if kind == "chapter":
            if value != current_chapter:
                flush(pos)
                current_chapter = value
                current_exercise = None
        elif kind == "exercise":
            if value != current_exercise:
                flush(pos)
                current_exercise = value
        else:  # "problem"
            flush(pos)
            pending_start = pos
            pending_chapter = current_chapter
            pending_exercise = current_exercise

    flush(len(full_text))
    return chunks


def extract_chunks(pdf_path: Path, dpi: int = 300, max_pages: Optional[int] = None) -> List[MathChunk]:
    language = detect_language(pdf_path)
    class_number = detect_class_number(pdf_path)
    full_text = extract_all_text(pdf_path, language, dpi=dpi, max_pages=max_pages)
    return chunk_text(full_text, language, class_number)


# ---- Feature 1: OCR raw + LLM-fixed dual output, with a comparison report ----


def fix_math_notation(raw_text: str) -> str:
    completion = _groq_client.chat.completions.create(
        model=settings.groq_model,
        messages=[{"role": "user", "content": _MATH_FIX_PROMPT + raw_text}],
        max_tokens=3000,
    )
    return completion.choices[0].message.content.strip()


def compute_changes(raw_text: str, fixed_text: str) -> List[dict]:
    """Word-level diff between raw and fixed text (not character-level, to keep each
    change a readable "before/after" pair instead of noisy single-character fragments)."""
    raw_words = raw_text.split()
    fixed_words = fixed_text.split()
    matcher = difflib.SequenceMatcher(None, raw_words, fixed_words)

    changes = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        changes.append(
            {
                "before": " ".join(raw_words[i1:i2]),
                "after": " ".join(fixed_words[j1:j2]),
            }
        )
    return changes


def save_page_outputs(page_number: int, chapter: Optional[int], raw_text: str, fixed_text: str) -> dict:
    for directory in (OCR_RAW_DIR, OCR_FIXED_DIR, COMPARISON_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    (OCR_RAW_DIR / f"page_{page_number}.txt").write_text(raw_text, encoding="utf-8")
    (OCR_FIXED_DIR / f"page_{page_number}.txt").write_text(fixed_text, encoding="utf-8")

    changes = compute_changes(raw_text, fixed_text)
    word_count = max(1, len(raw_text.split()))
    # improvement_score: fraction of the page's words touched by a correction (our own
    # definition — the spec's example number wasn't accompanied by an exact formula).
    comparison = {
        "page": page_number,
        "chapter": chapter,
        "raw": raw_text,
        "fixed": fixed_text,
        "changes_count": len(changes),
        "changes": changes,
        "improvement_score": round(len(changes) / word_count, 4),
    }

    (COMPARISON_DIR / f"page_{page_number}.json").write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return comparison


def process_page_with_llm_fix(pdf_path: Path, page_number: int, dpi: int = 300) -> dict:
    language = detect_language(pdf_path)
    doc = fitz.open(str(pdf_path))
    raw_text = ocr_page(doc[page_number - 1], language, dpi=dpi)

    chapter_re = _CHAPTER_RE_BN if language == "bn" else _CHAPTER_RE_EN
    chapter_match = chapter_re.search(raw_text)
    chapter = _to_int(chapter_match.group(1)) if chapter_match else None

    fixed_text = fix_math_notation(raw_text)
    return save_page_outputs(page_number, chapter, raw_text, fixed_text)


def build_summary() -> dict:
    comparison_files = sorted(COMPARISON_DIR.glob("page_*.json"))

    total_pages = 0
    total_corrections = 0
    correction_counts: dict = {}

    for f in comparison_files:
        data = json.loads(f.read_text(encoding="utf-8"))
        total_pages += 1
        total_corrections += data["changes_count"]
        for change in data["changes"]:
            key = (change["before"], change["after"])
            correction_counts[key] = correction_counts.get(key, 0) + 1

    avg_changes = round(total_corrections / total_pages, 2) if total_pages else 0.0
    most_common = sorted(
        ({"before": b, "after": a, "count": c} for (b, a), c in correction_counts.items()),
        key=lambda item: -item["count"],
    )[:20]

    summary = {
        "total_pages": total_pages,
        "avg_changes_per_page": avg_changes,
        "total_corrections": total_corrections,
        "most_common_corrections": most_common,
    }

    COMPARISON_DIR.mkdir(parents=True, exist_ok=True)
    (COMPARISON_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary
