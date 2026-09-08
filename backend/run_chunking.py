# STEP 4: chunk ocr_raw/ text into overlapping, metadata-tagged chunks.
#
# Important correctness note: curriculum.json's start_page_bn/start_page_en are
# the book's own PRINTED page numbers (chapter 1 always starts at printed page 1
# in this curriculum). ocr_raw/{file}/page_N.txt is numbered by raw PDF file page,
# which is offset from printed pages by however many front-matter pages (cover,
# preface, TOC) precede the real page 1 — a book-specific offset already proven to
# be nonzero elsewhere in this project (+5 for one book found earlier). So before
# assigning chapters to pages, we detect each file's real offset by finding where
# "অধ্যায় ১" / "Chapter 1" actually first appears in its own OCR'd text.
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ingestion.pdf_extractor import (
    _CHAPTER_RE_BN,
    _CHAPTER_RE_EN,
    _EXERCISE_RE_BN,
    _EXERCISE_RE_EN,
    _to_int,
)

BACKEND_DIR = Path(__file__).resolve().parent
CURRICULUM_PATH = BACKEND_DIR / "data" / "curriculum.json"
OCR_RAW_DIR = BACKEND_DIR / "data" / "ocr_raw"
OUTPUT_PATH = BACKEND_DIR / "data" / "approved" / "all_chunks.json"

CHUNK_SIZE = 1000
OVERLAP = 200

# The spec's given problem-number regexes only match a SINGLE leading digit
# (^[১-৯][।.] / ^\d+[.] applied loosely), which would miss any exercise with
# 10+ problems. Using full digit-run versions instead, matching the pattern
# already proven in ingestion/pdf_extractor.py for this exact project.
PROBLEM_RE_BN = re.compile(r"^\s*([০-৯]+)\s*[।.]\s+", re.MULTILINE)
PROBLEM_RE_EN = re.compile(r"^\s*(\d+)\s*\.\s+", re.MULTILINE)


def load_pages(stem: str) -> dict:
    raw_dir = OCR_RAW_DIR / stem
    pages = {}
    for f in raw_dir.glob("page_*.txt"):
        page_num = int(f.stem.split("_")[1])
        pages[page_num] = f.read_text(encoding="utf-8")
    return pages


def _looks_like_toc_row(text: str, match_end: int, other_titles: list, window: int = 300) -> bool:
    """True if another chapter's title shows up shortly after this match —
    a real chapter-heading page is followed by prose, not more chapter titles
    back-to-back, so this catches TOC-listing false positives."""
    following = text[match_end : match_end + window]
    return any(title and title in following for title in other_titles)


def detect_offset(pages: dict, language: str, chapters: list) -> int | None:
    """Find the raw file page where chapter 1's real content begins (not just
    its TOC mention), by locating chapter 1's own title text and requiring it
    NOT be immediately followed by another chapter's title (which would mean
    we're still reading a table-of-contents listing, not the real heading).
    Falls back to the numeric "chapter <N>" regex if the title-based approach
    finds nothing. Returns None (never guesses 0) if both fail."""
    title_key = f"title_{language}"
    chapter1_title = chapters[0].get(title_key)
    other_titles = [ch.get(title_key) for ch in chapters[1:]]

    if chapter1_title:
        for page_num in sorted(pages):
            text = pages[page_num]
            idx = text.find(chapter1_title)
            if idx == -1:
                continue
            if _looks_like_toc_row(text, idx + len(chapter1_title), other_titles):
                continue
            return page_num - 1

    chapter_re = _CHAPTER_RE_BN if language == "bn" else _CHAPTER_RE_EN
    for page_num in sorted(pages):
        for m in chapter_re.finditer(pages[page_num]):
            try:
                if _to_int(m.group(1)) == 1:
                    return page_num - 1
            except ValueError:
                continue

    return None


def chapter_for_printed_page(chapters: list, printed_page: int, lang_key: str):
    applicable = None
    for ch in chapters:
        start = ch.get(lang_key)
        if start is not None and start <= printed_page:
            applicable = ch
    return applicable


def find_boundary(text: str, target: int, window: int = 150) -> int:
    if target >= len(text):
        return len(text)
    search_start = max(0, target - window)
    segment = text[search_start:target]
    best = -1
    for ch in ("।", "\n"):
        idx = segment.rfind(ch)
        if idx > best:
            best = idx
    return target if best == -1 else search_start + best + 1


def chunk_file(book: dict, filename: str, language: str) -> list:
    stem = Path(filename).stem
    pages = load_pages(stem)
    if not pages:
        print(f"  WARNING: no OCR pages found for {stem}, skipping", flush=True)
        return []

    offset = detect_offset(pages, language, book["chapters"])
    if offset is None:
        print(f"  ⚠️  {stem}: COULD NOT DETECT offset, defaulting to 0 — verify chapters manually!", flush=True)
        offset = 0
    else:
        print(f"  {stem}: detected front-matter offset = {offset} pages", flush=True)

    lang_key = "start_page_bn" if language == "bn" else "start_page_en"
    chapters = book["chapters"]

    page_numbers = sorted(pages.keys())
    combined_parts = []
    page_offsets = []  # (raw_page_num, printed_page_num, start_char, end_char)
    cursor = 0
    for pn in page_numbers:
        text = pages[pn]
        printed_page = pn - offset
        page_offsets.append((pn, printed_page, cursor, cursor + len(text)))
        combined_parts.append(text)
        cursor += len(text) + 1
    full_text = "\n".join(combined_parts)

    def pages_overlapping(start_o: int, end_o: int) -> list:
        return [pn for pn, _pp, pstart, pend in page_offsets if pstart < end_o and pend >= start_o]

    def chapter_at_offset(o: int):
        for pn, printed_page, pstart, pend in page_offsets:
            if pstart <= o < pend + 1:
                return chapter_for_printed_page(chapters, printed_page, lang_key)
        return chapter_for_printed_page(chapters, page_offsets[-1][1], lang_key)

    exercise_re = _EXERCISE_RE_BN if language == "bn" else _EXERCISE_RE_EN
    exercise_matches = list(exercise_re.finditer(full_text))

    def exercise_at_offset(o: int):
        current = None
        for m in exercise_matches:
            if m.start() > o:
                break
            current = f"{_to_int(m.group(1))}.{_to_int(m.group(2))}"
        return current

    problem_re = PROBLEM_RE_BN if language == "bn" else PROBLEM_RE_EN
    header_marker = "অনুশীলনী" if language == "bn" else "Exercise"

    chunks = []
    chunk_idx = 0
    start = 0
    n = len(full_text)
    while start < n:
        target_end = min(start + CHUNK_SIZE, n)
        end = find_boundary(full_text, target_end) if target_end < n else n
        if end <= start:
            end = min(start + CHUNK_SIZE, n)

        chunk_text = full_text[start:end].strip()
        if chunk_text:
            chunk_idx += 1
            ch = chapter_at_offset(start)
            exercise = exercise_at_offset(start)
            pages_in_chunk = sorted(pages_overlapping(start, end)) or [page_offsets[0][0]]

            problem_number = None
            pm = problem_re.search(chunk_text)
            if pm:
                problem_number = _to_int(pm.group(1)) if language == "bn" else int(pm.group(1))

            # Always keep the exercise header visible in the chunk text itself.
            if exercise and header_marker not in chunk_text[:60]:
                header = f"[{'অনুশীলনী' if language == 'bn' else 'Exercise'} {exercise}]"
                chunk_text = f"{header}\n{chunk_text}"

            chunk_id = (
                f"class{book['class']}_{language}_ch{ch['number'] if ch else 0}"
                f"_p{pages_in_chunk[0]}_c{chunk_idx}"
            )

            chunks.append(
                {
                    "id": chunk_id,
                    "class": book["class"],
                    "book_type": book["book_type"],
                    "language": language,
                    "chapter": ch["number"] if ch else None,
                    "chapter_title": ch[f"title_{language}"] if ch else None,
                    "exercise": exercise,
                    "problem_number": problem_number,
                    "pages": pages_in_chunk,
                    "text": chunk_text,
                    "source_file": filename,
                }
            )

        if end >= n:
            break
        start = max(0, end - OVERLAP)

    return chunks


def main():
    curriculum = json.loads(CURRICULUM_PATH.read_text(encoding="utf-8"))
    all_chunks = []
    per_book_counts = {}

    for book in curriculum["books"]:
        for filename, language in ((book["bangla_file"], "bn"), (book["english_file"], "en")):
            print(f"Chunking {filename} ({language})...", flush=True)
            chunks = chunk_file(book, filename, language)
            all_chunks.extend(chunks)
            key = f"class{book['class']}_{book['book_type']}_{language}"
            per_book_counts[key] = len(chunks)
            print(f"  -> {len(chunks)} chunks", flush=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(all_chunks, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== SUMMARY ===")
    print(f"Total chunks: {len(all_chunks)}")
    for key, count in per_book_counts.items():
        print(f"  {key}: {count}")
    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
