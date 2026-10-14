# Step 4 — Current batch for review

**Book:** class_9_General_math_bn (book 1/10 in BOOK_ORDER)
**Pages:** 121–130 (of 362) — batch 13. Batch 12's images cleared (text files untouched).
**Settings:** all prior accumulated fixes, plus **FIX_BATCH12**: a new escalation-ladder step `escalate_split` (split page top/bottom, ~5% overlap, before the Tesseract fallback) and a prompt addition against word substitution.

## Task 1 — escalation ladder: new `escalate_split` step

Added `split_page_image()` (crops a page into top/bottom halves with a ~5%-of-height overlap band around the midpoint), `merge_split_halves()` (aligns the two readings on their longest shared run of lines via `difflib.SequenceMatcher.find_longest_match` and drops the duplicated overlap, same "align on real anchors" approach already used by `find_digit_disagreements()`), and `escalate_split_page()` (reads each half separately with `GEMINI_MODEL` at temp 0, merges). Wired into `process_page()` as a new step tried after `escalate_blocked_page()`'s 3 strategies fail and before the Tesseract fallback — labeled `escalate_split` in RUN_LOG/`blocked_pages.csv` when it recovers a page.

**Real bug found and fixed before any real test:** the first version of `split_page_image()` cropped the bottom half with `image.crop((max(0, mid - half_overlap), 0, width, height))` — passing `mid - half_overlap` as the crop box's **left (x)** coordinate instead of its **top (y)** coordinate (crop box is `(left, upper, right, lower)`). Caught immediately by a local sanity test (synthetic 800×1000 image): bottom half came back `325×1000` instead of `800×525`. Fixed to `(0, max(0, mid - half_overlap), width, height)`; re-ran the same sanity test plus a synthetic-text test of `merge_split_halves()` (shared lines deduped correctly; a no-overlap case falls back to plain concatenation) — both pass.

**Live test, since every existing blocked page is already in MANUAL_PAGES.txt (so the pipeline will never overwrite it) and batch 13 itself had zero blocked pages (see below) — per the task's own fallback ("না পেলে" = if none found), called `escalate_split_page()` directly (read-only: it only returns text, never writes a file) against the 3 pages from batch 12 that had exhausted the *entire* existing ladder and fallen back to Tesseract (117, 119, 120 — see `blocked_pages.csv`):**

| Page | Old result (batch 12) | `escalate_split` result |
|---|---|---|
| 117 | tesseract-fallback (every Gemini reading blocked) | **recovered**, 771–773 chars |
| 119 | tesseract-fallback (every Gemini reading blocked) | **recovered**, 1233–2291 chars |
| 120 | tesseract-fallback (every Gemini reading blocked) | **recovered**, 2097–2268 chars |

All 3 confirmed recovered — Peal's hypothesis ("ছোট টুকরো সাধারণত RECITATION এড়ায়") held on every page it was tried on. These 6 real API calls (2/page: top+bottom) were logged into RUN_LOG.csv with a note explaining they're a standalone verification call, not a page re-process (the pages' actual output files — manually fixed, per MANUAL_PAGES.txt — were not touched). Cumulative cost after this test: $0.5271 of the $7.00 stop.

## Task 2 — prompt addition

Appended to `PROMPT` (nothing else changed): "Transcribe exactly as printed -- do not replace any word with a synonym or 'correct' the book's wording." Motivated by Claude (chat)'s batch-12 review finding a recurring word substitution (প্রত্যেকটি→প্রতিটি, page 29) — the model paraphrasing instead of transcribing verbatim.

## Task 3 — batch 13 (pages 121-130)

**No RECITATION blocking at all this batch** — all 20 calls (10 pages × primary+secondary) returned `OK ... finish_reason=STOP` on the first attempt; the new `escalate_split` step was not needed live (see Task 1's standalone test instead).

| Page | Image | Text | Chars | Note |
|---|---|---|---|---|
| 121 | paper/check/class_9_General_math_bn/page_121.png | backend/data/ocr_gemini/class_9_General_math_bn/page_121.txt | 1876 | 2 typo fixes; `script_digit_mismatch` flagged (1 Bangla digit on a math-like line, likely a page-local artifact, not corrected automatically) |
| 122 | paper/check/class_9_General_math_bn/page_122.png | backend/data/ocr_gemini/class_9_General_math_bn/page_122.txt | 1551 | clean |
| 123 | paper/check/class_9_General_math_bn/page_123.png | backend/data/ocr_gemini/class_9_General_math_bn/page_123.txt | 1512 | 1 typo fix; `stacked_fraction` flagged on several lines (flag only, not auto-fixed) |
| 124 | paper/check/class_9_General_math_bn/page_124.png | backend/data/ocr_gemini/class_9_General_math_bn/page_124.txt | 1591 | 7 typo fixes; `stacked_fraction: L2` |
| 125 | paper/check/class_9_General_math_bn/page_125.png | backend/data/ocr_gemini/class_9_General_math_bn/page_125.txt | 1423 | clean |
| 126 | paper/check/class_9_General_math_bn/page_126.png | backend/data/ocr_gemini/class_9_General_math_bn/page_126.txt | 1369 | secondary (temp 0.4) promoted over primary (fewer issues); primary alone had a leftover `\angle` |
| 127 | paper/check/class_9_General_math_bn/page_127.png | backend/data/ocr_gemini/class_9_General_math_bn/page_127.txt | 1381 | 2 typo fixes |
| 128 | paper/check/class_9_General_math_bn/page_128.png | backend/data/ocr_gemini/class_9_General_math_bn/page_128.txt | 1379 | `stacked_fraction` flagged on 3 lines |
| 129 | paper/check/class_9_General_math_bn/page_129.png | backend/data/ocr_gemini/class_9_General_math_bn/page_129.txt | 1341 | `page_number_mismatch`: header read as '১২৮' (128) but expected ১২৪ (124) for this PDF page — flag only, needs a human check against the image |
| 130 | paper/check/class_9_General_math_bn/page_130.png | backend/data/ocr_gemini/class_9_General_math_bn/page_130.txt | 1440 | 4 typo fixes; heavy `stacked_fraction` flagging (many lines) — likely a fraction-heavy page, worth a visual check |

## Cost

Batch 13: 20 Gemini calls (10 pages × primary+secondary), no escalation needed. Plus Task 1's 6-call standalone `escalate_split` verification test (logged separately, see above).
**Cumulative gemini-3.5-flash-lite spend (Step 4 total so far): $0.5271** (441,001 in / 157,931 out tokens) of the $7.00 stop.

---

**Batch ready: class_9_General_math_bn pages 121-130.**
