# Step 4 — Current batch for review

**Book:** class_9_General_math_bn (book 1/10 in BOOK_ORDER)
**Pages:** 161–170 (of 362) — batch 17. Batch 16's images cleared (text files untouched).
**Settings:** all prior accumulated fixes, plus **FIX_BATCH16**: `\Delta`→Δ, "/"→"∠" angle-slash fix, heading Latin-digit fix, 2-column MCQ reordering. **No RECITATION this batch.**

## Task 1 — `\Delta` → `Δ`

Added to `latex_to_plain()` via its own space-swallowing regex (`_LATEX_DELTA_RE`), same treatment as `\angle` from FIX_BATCH15 — this book always writes `ΔABC`/`ΔOAE` glued directly to the point letters (confirmed by grepping the whole corpus's existing Δ usage, already produced via `\triangle`), never `Δ ABC`. Test passes: `"\Delta OAE \cong \Delta OCF"` → `"ΔOAE ≅ ΔOCF"`. Per Peal's confirmation, `\Delta` is always the triangle symbol in this book (never "change in x"); left unguarded against that other meaning since it hasn't come up — Claude (chat) will catch it in review if it ever does.

## Task 2 — ∠ written as "/"

New `fix_angle_slash()`: `"/"` becomes `"∠"` when immediately preceded by a space, start-of-line, or `"("`, AND immediately followed by 1-3 **uppercase** Latin letters then a non-letter — qc note `angle_slash_fixed: N`. Fraction safety confirmed with the task's own tests (`"a/2 = OC"`, `"AB/CD"`, `"p/3"`, `"(1/2)AB"` all unchanged — every one of those has a letter/digit/`")"` right before the `"/"`, which the rule excludes) plus two extra edge cases I added: a `"("`-preceded match (`"(/ABC এর সমান)"` → `"(∠ABC এর সমান)"`) and a 4+-letter run correctly NOT matching (`"/ABCD"` stays untouched, outside the 1-3 letter scope).

**Fired live on p154's real text**: `angle_slash_fixed: 3` — all three of the task's cited instances (`"কোণ /B"`, `"/ABE"`, `"/ABC"`) now correctly read `∠B`/`∠ABE`/`∠ABC`.

## Task 3 — heading number in Latin digits

New `fix_heading_latin_digits()`: a Latin digit (or `digit.digit`) right after `উদাহরণ`/`অনুশীলনী`/`উপপাদ্য`/`সম্পাদ্য`/`অনুসিদ্ধান্ত`/`অধ্যায়` at the start of a line converts to Bangla digits — qc note `heading_digit_fixed: N`. Every digit transliterates at face value EXCEPT `"8"`, which maps to `"৪"` instead of the literal `"৮"`: this book's own well-documented ৪/৮ visual mix-up (every recorded instance anywhere in this corpus, across FIX_BATCH5/14/15, is a real printed ৪ misread as ৮, never the reverse) turned out to apply across scripts too, not just within Bangla digits. Test passes: `"উদাহরণ 8."` → `"উদাহরণ ৪."`. Scoped tightly to right after these 6 exact words — the prompt's own "same script" rule stays in force everywhere else on the page.

**Fired live on p153's real text**: `heading_digit_fixed: 1` — `"উদাহরণ 8. ABC ত্রিভুজের..."` → `"উদাহরণ ৪. ABC ত্রিভুজের..."`.

## Task 4 — two-column MCQ order

New `fix_mcq_order()`: scans every 4 *literally* consecutive lines (no blank-line tolerance, unlike the figure-label/ASCII-art run logic — a real MCQ's options are always printed back-to-back); a block already in `ক) খ) গ) ঘ)` order is left alone and not flagged; a block read column-by-column as `ক) গ) খ) ঘ)` gets its middle two lines swapped back into the correct order — qc note `mcq_reordered: N`; any other 4-marker order is left untouched, only flagged (`mcq_order_suspect`).

**Fired live on p154's real text**: `mcq_reordered: 1` — the first option block (`"ক) 60° ও 36°" / "গ) 30° ও 70°" / "খ) 40° ও 50°" / "ঘ) 80° ও 20°"`) is now correctly ordered `ক, খ, গ, ঘ`. The page's other two option blocks were already in the correct order and were correctly left untouched (confirmed: neither appears in the swap count nor the suspect flag).

**Regression swept the whole already-OCR'd book (162 pages) for all 4 tasks**: zero crashes, zero false positives — `angle_slash_fixed`/`heading_digit_fixed`/`mcq_reordered`/`mcq_order_suspect` fired on exactly p154/p153/p154 (nowhere else).

## Task 5 — batch 17 (pages 161-170)

**No RECITATION, no escalation needed.** Still in Chapter 7 (ব্যবহারিক জ্যামিতি, practical geometry).

| Page | Chars | Note |
|---|---|---|
| 161 | 2809 | 10 typo fixes (both readings) |
| 162 | 4263 | 7 typo fixes; secondary (discarded alt) had `devanagari_leak: 3` |
| 163 | 4002 | clean primary; secondary (discarded alt) had 1 typo fix + `devanagari_leak: 4` |
| 164 | 2942 | 1 typo fix |
| 165 | 2687 | 7 typo fixes; `stacked_fraction: L1` |
| **166** | 2808 | **`ascii_figure_removed: 6`** (both readings) — Task 2 from FIX_BATCH15, not this batch's own tasks, but a nice live confirmation it's still catching real pages |
| 167 | 3859 | 5 typo fixes; secondary (discarded alt) had 3 |
| 168 | 4630 | `figure_labels_suspect: L29`, `stacked_fraction: L29` (flag only, not removed — single line) |
| **169** | 4660 | **`page_number_fixed: ১৬৮->১৬৪`** (FIX_BATCH15's ৪↔৮ self-fix, still firing correctly on new pages) |
| 170 | 3331 | 4 typo fixes; `script_digit_mismatch` flagged (both readings) |

This batch's own FIX_BATCH16 tasks (1-4) did not fire live on these specific 10 pages (no `\Delta`, angle-slash, heading-Latin-digit, or MCQ-column content on them) — all four are verified against real p153/p154 data from the prior batch instead (see their sections above).

## Cost

Batch 17: 20 Gemini calls (10 pages × primary+secondary, no escalation needed).
**Cumulative gemini-3.5-flash-lite spend (Step 4 total so far): $0.6537** (565,161 in / 193,659 out tokens) of the $7.00 stop.

## Task 6 — commit + push

`git status` checked first: no `.env`/API keys/`venv` in the diff (only `full_gemini_ocr.py`, `RUN_LOG.csv`, `digit_disagreements.csv`, this file, and this batch's new `backend/data/ocr_gemini/class_9_General_math_bn/page_161..170.*` + `paper/check/class_9_General_math_bn/page_161..170.png` files).

**Push result:** committed as `3dca08b` ("Batch 17: OCR p161-170 + FIX_BATCH16 (angle slash, heading digits, MCQ order, \Delta)") and pushed to `origin/main` successfully (`d06ae6f..3dca08b`) -- this push also carried up an earlier unpushed commit (`ac3f3dd`, the Batch 16 human-review commit that produced FIX_BATCH16.md itself, made by a separate session, not this one).

---

**Batch ready: class_9_General_math_bn pages 161-170.**
