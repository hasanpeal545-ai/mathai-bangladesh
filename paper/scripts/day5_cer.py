"""Day 5 / Task A: Character Error Rate (CER) for the 3 verified Bangla pages,
across every OCR/correction method, against Peal's hand-verified ground truth.

Methods compared (all read-only inputs, nothing here is modified):
  M1  Tesseract raw         -- the "raw" field of backend/data/comparison/bn_page_N.json
  M1b Tesseract raw (alt)   -- backend/data/ocr_raw/class_9_General_math_bn/page_N.txt
                               (a DIFFERENT OCR run than M1 -- reported separately as a
                               cross-check, per DAY5.md; not averaged together with M1)
  M2  Tesseract + Groq fix  -- the "fixed" field of the same comparison JSON (same run as M1)
  M3  Gemini Vision         -- paper/gemini_vision/bn_page_N.txt (the RAW Gemini output,
                               not the ground truth -- ground truth started as a copy of
                               this file but Peal hand-edited it, so the two now differ)

rapidfuzz / editdistance are NOT installed in backend/venv (checked before writing this),
and DAY5.md says not to pip install without asking Peal -- so Levenshtein distance with
substitution/insertion/deletion counts is implemented here in pure Python (full O(len(ref)
x len(hyp)) dynamic-programming matrix with backtrace; all 15 ref/hyp texts here are under
~2000 characters, so this comfortably fits in memory and runs in well under a second each).

Normalisation (applied identically to every text, per DAY5.md):
  - Unicode NFC.
  - Primary comparison: ALL whitespace removed (characters only, no spaces/tabs/newlines).
  - Sensitivity-check variant ("with_spaces"): runs of whitespace collapsed to one space.
CER = Levenshtein(hyp, ref) / len(ref), using the no-whitespace normalisation as primary.
"""
import csv
import json
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
OUT_CSV = os.path.join(ROOT, "paper", "results", "day5_cer.csv")

PAGES = [30, 36, 44]


def normalise(text, keep_single_spaces=False):
    text = unicodedata.normalize("NFC", text)
    if keep_single_spaces:
        return re.sub(r"\s+", " ", text).strip()
    return re.sub(r"\s+", "", text)


def levenshtein_ops(ref, hyp):
    """Full DP matrix + backtrace. Returns (distance, S, I, D).
    Insertions = extra chars in hyp with no counterpart in ref.
    Deletions  = ref chars missing from hyp.
    Substitutions = ref chars replaced by a different hyp char."""
    n, m = len(ref), len(hyp)
    # dp[i][j] = edit distance between ref[:i] and hyp[:j]
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        ri = ref[i - 1]
        row, prev_row = dp[i], dp[i - 1]
        for j in range(1, m + 1):
            if ri == hyp[j - 1]:
                row[j] = prev_row[j - 1]
            else:
                row[j] = min(prev_row[j - 1] + 1, prev_row[j] + 1, row[j - 1] + 1)

    # Backtrace from (n, m) to (0, 0)
    i, j = n, m
    S = I = D = 0
    while i > 0 or j > 0:
        if i > 0 and j > 0 and ref[i - 1] == hyp[j - 1] and dp[i][j] == dp[i - 1][j - 1]:
            i, j = i - 1, j - 1
            continue
        if i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
            S += 1
            i, j = i - 1, j - 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            D += 1
            i -= 1
        elif j > 0 and dp[i][j] == dp[i][j - 1] + 1:
            I += 1
            j -= 1
        else:
            raise AssertionError("backtrace got stuck -- DP matrix inconsistent")
    return dp[n][m], S, I, D


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def load_methods(page):
    gt = read(os.path.join(GT_DIR, f"bn_page_{page}.txt"))
    cmp_json = json.load(open(os.path.join(COMPARISON_DIR, f"bn_page_{page}.json"), encoding="utf-8"))
    m1 = cmp_json["raw"]
    m2 = cmp_json["fixed"]
    m1b = read(os.path.join(OCR_RAW_DIR, f"page_{page}.txt"))
    m3 = read(os.path.join(GEMINI_DIR, f"bn_page_{page}.txt"))
    return {
        "ref": gt,
        "M1_tesseract_raw": m1,
        "M1b_tesseract_raw_altrun": m1b,
        "M2_tesseract_groq_fixed": m2,
        "M3_gemini_vision": m3,
    }


def main():
    rows = []
    totals = {}  # method -> {ref_chars, S, I, D, ref_chars_ws, S_ws, I_ws, D_ws}

    for page in PAGES:
        texts = load_methods(page)
        ref_ns = normalise(texts["ref"])
        ref_ws = normalise(texts["ref"], keep_single_spaces=True)

        for method in ["M1_tesseract_raw", "M1b_tesseract_raw_altrun", "M2_tesseract_groq_fixed", "M3_gemini_vision"]:
            hyp_ns = normalise(texts[method])
            hyp_ws = normalise(texts[method], keep_single_spaces=True)

            dist, S, I, D = levenshtein_ops(ref_ns, hyp_ns)
            dist_ws, S_ws, I_ws, D_ws = levenshtein_ops(ref_ws, hyp_ws)

            cer = dist / len(ref_ns) if ref_ns else 0.0
            cer_ws = dist_ws / len(ref_ws) if ref_ws else 0.0

            rows.append(
                {
                    "page": page,
                    "method": method,
                    "ref_chars": len(ref_ns),
                    "hyp_chars": len(hyp_ns),
                    "S": S,
                    "I": I,
                    "D": D,
                    "CER": round(cer, 4),
                    "CER_with_spaces": round(cer_ws, 4),
                }
            )

            t = totals.setdefault(
                method, {"ref_chars": 0, "S": 0, "I": 0, "D": 0, "ref_chars_ws": 0, "S_ws": 0, "I_ws": 0, "D_ws": 0}
            )
            t["ref_chars"] += len(ref_ns)
            t["S"] += S
            t["I"] += I
            t["D"] += D
            t["ref_chars_ws"] += len(ref_ws)
            t["S_ws"] += S_ws
            t["I_ws"] += I_ws
            t["D_ws"] += D_ws

    # Mean rows: micro-average = total edits / total ref chars, across the 3 pages.
    for method, t in totals.items():
        total_edits = t["S"] + t["I"] + t["D"]
        total_edits_ws = t["S_ws"] + t["I_ws"] + t["D_ws"]
        rows.append(
            {
                "page": "MEAN(micro)",
                "method": method,
                "ref_chars": t["ref_chars"],
                "hyp_chars": "",
                "S": t["S"],
                "I": t["I"],
                "D": t["D"],
                "CER": round(total_edits / t["ref_chars"], 4) if t["ref_chars"] else 0.0,
                "CER_with_spaces": round(total_edits_ws / t["ref_chars_ws"], 4) if t["ref_chars_ws"] else 0.0,
            }
        )

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    fieldnames = ["page", "method", "ref_chars", "hyp_chars", "S", "I", "D", "CER", "CER_with_spaces"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {os.path.relpath(OUT_CSV, ROOT)} ({len(rows)} rows)")
    for r in rows:
        print(
            f"  page={r['page']:<12} method={r['method']:<28} "
            f"ref={r['ref_chars']:<5} S={r['S']:<4} I={r['I']:<4} D={r['D']:<4} "
            f"CER={r['CER']:.4f} CER_ws={r['CER_with_spaces']:.4f}"
        )


if __name__ == "__main__":
    main()
