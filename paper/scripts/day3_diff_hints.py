"""Day 3 / Task B: diff hints -- compare each page's Gemini transcription against the
Tesseract raw OCR text, and flag places where they differ a lot, as a hint for where
Peal should look hardest while building ground truth. This does NOT decide what is
correct -- Tesseract is often wrong, and so is Gemini. Kept simple, difflib only, per
DAY3.md.

Note on method: a naive LINE-level diff (difflib.SequenceMatcher on lines) was tried
first and discarded -- Tesseract and Gemini wrap the same paragraph into different
line lengths, so almost no line is byte-identical between the two, which makes a
line-level matcher treat nearly the whole page as one giant insert/delete block
(not useful: everything gets flagged, nothing is highlighted). Diffing at the WORD
level instead (same technique already used in backend/ingestion/pdf_extractor.py's
compute_changes() and paper/scripts/day1_correction_stats.py) is far more robust to
line-wrap differences, and still finds genuinely matching stretches of text. Each
flagged word-level change is then mapped back to the Gemini draft's line number so
Peal knows where to look.

For each page in TARGETS, reads:
  - paper/gemini_vision/{page}.txt            (Gemini Vision transcription)
  - backend/data/ocr_raw/class_9_General_math_{lang}/page_{N}.txt   (Tesseract raw)
and writes:
  - paper/ground_truth/{page}_CHECKLIST.md
"""
import difflib
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GEMINI_DIR = os.path.join(ROOT, "paper", "gemini_vision")
OCR_RAW_DIR = os.path.join(ROOT, "backend", "data", "ocr_raw", "class_9_General_math_{lang}")
OUT_DIR = os.path.join(ROOT, "paper", "ground_truth")

# Only pages that currently have a Gemini transcription (en_page_30 / en_page_38 are
# still blocked on Gemini's daily quota as of this run -- see RUN_LOG.md).
TARGETS = ["bn_page_30", "bn_page_36", "bn_page_44"]

# A word-level change is flagged as "differs a lot" if it touches at least this many
# words on the larger side, OR the before/after character-level similarity ratio is
# below RATIO_THRESHOLD (catches a single word swapped for a very different one).
WORD_COUNT_THRESHOLD = 3
RATIO_THRESHOLD = 0.5


def page_lang_and_number(page_name):
    m = re.match(r"^(bn|en)_page_(\d+)$", page_name)
    if not m:
        raise ValueError(f"Unrecognised page name format: {page_name}")
    return m.group(1), int(m.group(2))


def read_text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def words_with_line_numbers(text):
    """Flattens text into a word list (same tokenisation as .split()) alongside a
    parallel list giving each word's 1-based source line number, so a word-index
    range can be mapped back to "which line was this in"."""
    words, line_nos = [], []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for w in line.split():
            words.append(w)
            line_nos.append(line_no)
    return words, line_nos


def find_big_changes(tess_text, gemini_text):
    tess_words = tess_text.split()
    gemini_words, gemini_line_nos = words_with_line_numbers(gemini_text)

    matcher = difflib.SequenceMatcher(None, tess_words, gemini_words)
    flagged = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        before = " ".join(tess_words[i1:i2])
        after = " ".join(gemini_words[j1:j2])
        word_count = max(i2 - i1, j2 - j1)
        ratio = difflib.SequenceMatcher(None, before, after).ratio()
        if word_count < WORD_COUNT_THRESHOLD and ratio >= RATIO_THRESHOLD:
            continue  # small, easy-to-spot edit -- not worth flagging

        if j1 < len(gemini_line_nos):
            gemini_line_no = gemini_line_nos[j1]
        elif gemini_line_nos:
            gemini_line_no = gemini_line_nos[-1]
        else:
            gemini_line_no = 1

        flagged.append(
            {
                "gemini_line_no": gemini_line_no,
                "tess_text": before,
                "gemini_text": after,
                "ratio": ratio,
            }
        )
    flagged.sort(key=lambda x: x["gemini_line_no"])
    return flagged


def write_checklist(page_name, flagged, tess_path_rel, gemini_path_rel, tess_missing):
    out_path = os.path.join(OUT_DIR, f"{page_name}_CHECKLIST.md")
    lines = []
    lines.append(f"# Checklist — {page_name}\n")
    if tess_missing:
        lines.append(
            f"**Tesseract raw file not found** ({tess_path_rel}) — could not generate diff hints "
            "for this page. Check every line by eye; no shortcut available.\n"
        )
    else:
        lines.append(
            f"Compared `{gemini_path_rel}` (Gemini draft) against `{tess_path_rel}` "
            f"(Tesseract raw) word by word (see the script's docstring for why word-level, "
            f"not line-level). Lines below point to where the Gemini draft's wording "
            f"disagrees a lot with Tesseract's — look hardest here, but still check "
            "**every** line in the draft against the printed page, since Tesseract and "
            "Gemini can both be wrong (sometimes in the same way, which this diff cannot "
            "catch).\n"
        )
        if not flagged:
            lines.append("_No word-level changes crossed the flagging threshold for this page._\n")
        else:
            lines.append(f"**{len(flagged)} flagged change(s):**\n")
            for item in flagged:
                lines.append(f"## Draft line {item['gemini_line_no']} (similarity {item['ratio']:.2f})")
                lines.append(f"- Tesseract raw said: `{item['tess_text']}`")
                lines.append(f"- Gemini draft says:  `{item['gemini_text']}`")
                lines.append("")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"Wrote {os.path.relpath(out_path, ROOT)} ({len(flagged)} flagged change(s))")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for page_name in TARGETS:
        lang, number = page_lang_and_number(page_name)
        gemini_path = os.path.join(GEMINI_DIR, f"{page_name}.txt")
        tess_path = os.path.join(OCR_RAW_DIR.format(lang=lang), f"page_{number}.txt")

        if not os.path.exists(gemini_path):
            print(f"[SKIP] {page_name}: no Gemini transcription at {gemini_path}")
            continue

        gemini_text = read_text(gemini_path)
        tess_missing = not os.path.exists(tess_path)
        tess_text = "" if tess_missing else read_text(tess_path)

        flagged = [] if tess_missing else find_big_changes(tess_text, gemini_text)
        write_checklist(
            page_name,
            flagged,
            os.path.relpath(tess_path, ROOT),
            os.path.relpath(gemini_path, ROOT),
            tess_missing,
        )


if __name__ == "__main__":
    main()
