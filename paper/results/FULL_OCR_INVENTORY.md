# Full OCR — PDF inventory

Checked every PDF in `backend/data/pdfs/2026/bangla/` and `backend/data/pdfs/2026/english/` (14 files total) for page count and exact duplicates, by computing the full file's SHA-256 (not just size — size alone matching is a hint, SHA-256 confirms byte-for-byte identity) and cross-referencing against `backend/data/curriculum.json`, which the project's existing pipeline (`backend/run_full_ocr.py`, `backend/extract_toc.py`) already treats as the source of truth for "which PDFs are the real distinct books."

## Result: 14 files, 10 distinct books, 4 exact duplicates

| # | Book (canonical stem) | Class | Type | Language | Pages | Duplicate of |
|---|---|---|---|---|---|---|
| 1 | class_6_math_bn | 6 | general | bn | 161 | — |
| 2 | class_6_math_en | 6 | general | en | 182 | — |
| 3 | class_7_math_bn | 7 | general | bn | 181 | — |
| 4 | class_7_math_en | 7 | general | en | 198 | — |
| 5 | class_8_math_bn | 8 | general | bn | 190 | — |
| 6 | class_8_math_en | 8 | general | en | 202 | — |
| 7 | class_9_General_math_bn | 9 | general | bn | 362 | — |
| 8 | class_9_General_math_en | 9 | general | en | 390 | — |
| 9 | class_9_Hiher_math_bn *(sic — filename typo, kept as-is for consistency with existing `ocr_raw/` folder name)* | 9 | higher | bn | 342 | — |
| 10 | class_9_Higher_math_en | 9 | higher | en | 354 | — |
| — | class_10_General_math_bn.pdf | 10 | general | bn | 362 | **class_9_General_math_bn.pdf** (SHA-256 identical) |
| — | class_10_Hiher_math_bn.pdf | 10 | higher | bn | 342 | **class_9_Hiher_math_bn.pdf** (SHA-256 identical) |
| — | class_10_General_math_en.pdf | 10 | general | en | 390 | **class_9_General_math_en.pdf** (SHA-256 identical) |
| — | class_10_Higher_math_en.pdf | 10 | higher | en | 354 | **class_9_Higher_math_en.pdf** (SHA-256 identical) |

**Total pages across the 10 distinct books: 2,562** (161+182+181+198+190+202+362+390+342+354).

## Why the duplicates exist (not a data error)

Bangladesh's NCTB curriculum teaches Class 9 and Class 10 General Math (and, separately, Higher Math) from **one combined textbook** covering both years — this is also directly visible on the pages themselves: the footer on every General Math page reads `"গণিত- ৯ম-১০ম শ্রেণি"` ("Math — 9th-10th grade"), confirmed from `backend/data/ocr_raw/class_9_General_math_bn/page_30.txt` during the Day 2/3/5 work on this same book. So `class_9_General_math_bn.pdf` and `class_10_General_math_bn.pdf` being byte-identical is expected, not a mistake — someone simply placed a second copy of the same file under both class folders. `backend/data/curriculum.json` already only lists the `class_9_*` filenames (5 books: class 6, 7, 8, 9-general, 9-higher, each with a `bangla_file`/`english_file` pair) and `backend/run_full_ocr.py` iterates only over `curriculum["books"]` — meaning **the existing Tesseract OCR pipeline already silently ignored the 4 `class_10_*.pdf` duplicate files**, and `backend/data/ocr_raw/` already has complete Tesseract text for exactly these same 10 distinct books (verified: every one of the 10 `ocr_raw/<book>/` folders has a `page_N.txt` count matching that book's PDF page count exactly).

## What this means for the full Gemini re-OCR

Per DAY2.md/FULL_OCR.md's duplicate-skipping instruction, **the 4 `class_10_*.pdf` files are skipped entirely** — re-OCR'ing them would just reprocess the exact same bytes as their `class_9_*` counterpart and double the cost for zero new content. `paper/scripts/full_gemini_ocr.py` (Step 2) only ever reads `backend/data/curriculum.json`'s book list, so it never touches the 4 duplicate files in the first place.
