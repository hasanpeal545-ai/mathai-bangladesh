# DAY 5 — Character Error Rate (CER) on the verified pages

Read paper/README.md first. Do not modify backend/, frontend/ or paper/ground_truth/*.txt (those are Peal's verified files — read only).

## Inputs (Bangla pages 30, 36, 44 — English pages later if Gemini quota allows and Peal verifies them)
- Ground truth (verified by Peal): paper/ground_truth/bn_page_{30,36,44}.txt
- M1 Tesseract raw: the "raw" field of backend/data/comparison/bn_page_N.json
  (use this, not ocr_raw/, so M1 and M2 come from the same run; ALSO compute M1b from backend/data/ocr_raw/class_9_General_math_bn/page_N.txt and report it separately as a check)
- M2 Tesseract + Groq LLM correction: the "fixed" field of the same JSON
- M3 Gemini Vision: paper/gemini_vision/bn_page_N.txt (the original Gemini output, NOT the ground truth)

## Task A — CER script (paper/scripts/day5_cer.py)
1. Normalisation (apply identically to every text): Unicode NFC; replace all runs of whitespace (spaces, tabs, newlines) with nothing, i.e. compare characters only. Also report a second variant that keeps single spaces between tokens, as a sensitivity check.
2. CER = Levenshtein edit distance(hyp, ref) / len(ref). Implement Levenshtein in pure Python (or use `rapidfuzz` / `editdistance` if already installed — do not pip install without asking Peal). Also report the counts of substitutions, insertions, deletions.
3. Output paper/results/day5_cer.csv with one row per page × method (page, method, ref_chars, hyp_chars, S, I, D, CER, CER_with_spaces) and a mean row per method (micro-average = total edits / total ref chars).

## Task B — Error breakdown by character class
For each method, align hyp to ref (difflib.SequenceMatcher on characters is fine) and count errors on reference characters in these classes:
- Bangla letters/vowel signs (U+0980–U+09FF except digits)
- Bangla digits (০-৯)
- Latin letters
- ASCII digits
- Math symbols (∈ ∉ ∪ ∩ ∅ ∴ ⊂ ⊆ × − ≤ ≥ ± ′ \ and superscripts ⁰-⁹ ⁿ)
- Brackets { } ( ) [ ] and other punctuation
Write paper/results/day5_error_by_class.csv (method, class, ref_count, errors, error_rate).

## Task C — Audit the Groq edits on these 3 pages
For each edit in backend/data/comparison/bn_page_N.json "changes" (before -> after), label it automatically:
- "fixed": `after` matches the ground truth at that place and `before` did not
- "harmful": `before` matched the ground truth and `after` does not
- "neutral/unclear": anything else
Use alignment of raw→GT and fixed→GT to decide; when uncertain choose "unclear" (never guess "fixed"). Save paper/results/day5_edit_audit.csv (page, before, after, label, note) and print the counts. Peal will spot-check 10 rows by eye.

## Finish
Write paper/results/DAY5_SUMMARY.md with: the main CER table (methods × pages + mean), the class breakdown table, the edit-audit counts, and 5 concrete example errors per method (ref vs hyp snippet). Keep numbers exactly as computed — no rounding beyond 2 decimals in %.
