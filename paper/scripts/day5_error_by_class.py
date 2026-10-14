"""Day 5 / Task B: error breakdown by character class, for each method, on the 3
verified Bangla pages. Reuses the same read-only inputs and no-whitespace NFC
normalisation as day5_cer.py (the "characters only" primary comparison).

Alignment method: difflib.SequenceMatcher on characters (hyp vs ref), as DAY5.md
explicitly allows ("difflib.SequenceMatcher on characters is fine") -- this is a
different alignment from day5_cer.py's true-minimum-edit-distance Levenshtein, so
the per-class error counts below may not sum to exactly day5_cer.py's S+I+D for the
same method/page; both are valid alignments of the same two strings and either is
an acceptable choice for *classifying* where errors land (DAY5.md names Levenshtein
for the headline CER number specifically, and difflib for this classification task).

Classes and how an error is attributed:
  - For an 'equal' opcode: no error.
  - For a 'replace' or 'delete' opcode: every ref character in that opcode's ref
    range is an error, classified by *that ref character's own* class.
  - For an 'insert' opcode: these are hyp characters with NO ref counterpart, so
    DAY5.md's phrasing ("count errors on reference characters") does not assign
    them to any ref class. They are still real errors (included in the overall
    CER in day5_cer.py) -- here they're tallied separately per method as
    "insertion (extra char, no ref class)" so nothing is silently dropped, but they
    do not count against any of the 6 ref-character classes' error_rate.

ref_count for a class = how many characters of the (whole, not just erroring)
reference text fall into that class -- i.e. the class's share of the page, used as
the error_rate denominator.
"""
import csv
import json
import difflib
import os
import re
import sys
import unicodedata

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GT_DIR = os.path.join(ROOT, "paper", "ground_truth")
COMPARISON_DIR = os.path.join(ROOT, "backend", "data", "comparison")
OCR_RAW_DIR = os.path.join(ROOT, "backend", "data", "ocr_raw", "class_9_General_math_bn")
GEMINI_DIR = os.path.join(ROOT, "paper", "gemini_vision")
OUT_CSV = os.path.join(ROOT, "paper", "results", "day5_error_by_class.csv")

PAGES = [30, 36, 44]
METHODS = ["M1_tesseract_raw", "M1b_tesseract_raw_altrun", "M2_tesseract_groq_fixed", "M3_gemini_vision"]

MATH_SYMBOLS = set("∈∉∪∩∅∴⊂⊆×−≤≥±′\\") | set("⁰¹²³⁴⁵⁶⁷⁸⁹ⁿ")
BRACKETS = set("{}()[]")
BANGLA_DIGITS = set("০১২৩৪৫৬৭৮৯")


def char_class(ch):
    if ch in BANGLA_DIGITS:
        return "Bangla digit"
    if "ঀ" <= ch <= "৿":  # Bangla block, digits already excluded above
        return "Bangla letter/vowel sign"
    if ch.isascii() and ch.isdigit():
        return "ASCII digit"
    if ch.isascii() and ch.isalpha():
        return "Latin letter"
    if ch in MATH_SYMBOLS:
        return "Math symbol"
    # Catch-all per DAY5.md: brackets + "other punctuation"
    return "Bracket/other punctuation"


CLASSES = [
    "Bangla letter/vowel sign",
    "Bangla digit",
    "Latin letter",
    "ASCII digit",
    "Math symbol",
    "Bracket/other punctuation",
]


def normalise_nospace(text):
    return re.sub(r"\s+", "", unicodedata.normalize("NFC", text))


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def load_methods(page):
    gt = read(os.path.join(GT_DIR, f"bn_page_{page}.txt"))
    cmp_json = json.load(open(os.path.join(COMPARISON_DIR, f"bn_page_{page}.json"), encoding="utf-8"))
    m1b = read(os.path.join(OCR_RAW_DIR, f"page_{page}.txt"))
    m3 = read(os.path.join(GEMINI_DIR, f"bn_page_{page}.txt"))
    return {
        "ref": gt,
        "M1_tesseract_raw": cmp_json["raw"],
        "M1b_tesseract_raw_altrun": m1b,
        "M2_tesseract_groq_fixed": cmp_json["fixed"],
        "M3_gemini_vision": m3,
    }


def classify_errors(ref, hyp):
    """Returns (ref_count_by_class, error_count_by_class, insertion_count)."""
    ref_count = {c: 0 for c in CLASSES}
    for ch in ref:
        ref_count[char_class(ch)] += 1

    error_count = {c: 0 for c in CLASSES}
    insertions = 0

    matcher = difflib.SequenceMatcher(None, ref, hyp, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag in ("replace", "delete"):
            for ch in ref[i1:i2]:
                error_count[char_class(ch)] += 1
        if tag == "insert":
            insertions += j2 - j1
        # Note: 'replace' opcodes where len(ref range) < len(hyp range) also carry
        # some "extra" hyp characters beyond the 1:1 portion -- difflib's opcode
        # model doesn't split that out, so DAY5's "errors on reference characters"
        # rule is applied exactly as stated: every ref char in a replace/delete
        # range is one error, full stop, regardless of how many hyp chars it was
        # replaced by.
    return ref_count, error_count, insertions


def main():
    rows = []
    # method -> class -> {ref_count, errors}; plus method -> insertions (page-summed)
    totals = {m: {c: {"ref_count": 0, "errors": 0} for c in CLASSES} for m in METHODS}
    totals_insertions = {m: 0 for m in METHODS}

    for page in PAGES:
        texts = load_methods(page)
        ref_ns = normalise_nospace(texts["ref"])

        for method in METHODS:
            hyp_ns = normalise_nospace(texts[method])
            ref_count, error_count, insertions = classify_errors(ref_ns, hyp_ns)
            totals_insertions[method] += insertions

            for c in CLASSES:
                rows.append(
                    {
                        "page": page,
                        "method": method,
                        "class": c,
                        "ref_count": ref_count[c],
                        "errors": error_count[c],
                        "error_rate": round(error_count[c] / ref_count[c], 4) if ref_count[c] else "",
                    }
                )
                totals[method][c]["ref_count"] += ref_count[c]
                totals[method][c]["errors"] += error_count[c]

    for method in METHODS:
        for c in CLASSES:
            rc = totals[method][c]["ref_count"]
            er = totals[method][c]["errors"]
            rows.append(
                {
                    "page": "ALL_PAGES",
                    "method": method,
                    "class": c,
                    "ref_count": rc,
                    "errors": er,
                    "error_rate": round(er / rc, 4) if rc else "",
                }
            )
        rows.append(
            {
                "page": "ALL_PAGES",
                "method": method,
                "class": "(insertions, no ref class -- not in error_rate above)",
                "ref_count": "",
                "errors": totals_insertions[method],
                "error_rate": "",
            }
        )

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    fieldnames = ["page", "method", "class", "ref_count", "errors", "error_rate"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {os.path.relpath(OUT_CSV, ROOT)} ({len(rows)} rows)")
    for method in METHODS:
        print(f"  -- {method} --")
        for c in CLASSES:
            rc = totals[method][c]["ref_count"]
            er = totals[method][c]["errors"]
            rate = f"{er/rc:.4f}" if rc else "n/a"
            print(f"    {c:<30} ref={rc:<5} errors={er:<5} rate={rate}")
        print(f"    insertions (no ref class): {totals_insertions[method]}")


if __name__ == "__main__":
    main()
