# Step 4 — Current batch for review

**Book:** class_9_General_math_bn (book 1/10 in BOOK_ORDER)
**Pages:** 141–150 (of 362) — batch 15. Batch 14's images cleared (text files untouched).
**Settings:** all prior accumulated fixes, plus **FIX_BATCH14**: নির্বচন/উপপাদ্য heading typo fixes, blank-line-tolerant figure-label-run removal, a `figure_values_lost` flag, and a `margin_year_tail` rule for unknown rotated-margin years. **No RECITATION this batch — `escalate_split` not exercised live again.**

## Task 1 — নির্বচন (rare word → common word)

Added to `fix_known_bangla_typos()`: `"বিশেষ নির্বাচন"` → `"বিশেষ নির্বচন"`, `"সাধারণ নির্বাচন"` → `"সাধারণ নির্বচন"` -- scoped to exactly these two 2-word phrases (not a bare `"নির্বাচন"` rule), since `"নির্বাচন"` ("election") is also a real, common, unrelated word, and `"বহুনির্বাচনি"` ("multiple-choice") contains it as a literal substring too. Test: `"বহুনির্বাচনি প্রশ্ন"` unchanged; `"বিশেষ নির্বাচন:"` → `"বিশেষ নির্বচন:"`; also checked `"ছাত্র সংসদ নির্বাচন..."` (a real, unrelated election) stays untouched. All pass. **Did not fire live in batch 15** (pages 141-150 are Chapter 7's practical-geometry constructions, not yet back in theorem-heavy Chapter 6 content) -- ready for when it reappears.

## Task 2 — উপপাদ্য heading

(a) Added `"উপপাদ্য"` into the existing `_SUTRO_ANUSIDDHANTO_PERIOD_RE` (now fixes `"উপপাদ্য N।"` → `"...N."` too, same as `"সূত্র"`/`"অনুসিদ্ধান্ত"`).
(b) New `_UPOPADDO_MISSING_PHOLA_RE = re.compile(r"(?<![ঀ-৿])উপপাদ(?=\s+[০-৯])")` fixes `"উপপাদ N."` (missing্য) → `"উপপাদ্য N."`. Needed the lookahead guard since `"উপপাদ"` is a literal prefix of the already-correct `"উপপাদ্য"` -- without it, a correct heading would double up into `"উপপাদ্য্য"`. Runs BEFORE the period-fix (same ordering reason as the existing `_UDAAHARON_RE`/`_UDAHARON_PERIOD_RE` pair) so a hypothetical page with both bugs together gets both fixed in one pass. Tests: `"উপপাদ ১৫."` → `"উপপাদ্য ১৫."`; `"উপপাদ্য ১৫."` unchanged (no double-up); `"উপপাদ ১৫।"` (both bugs at once) → `"উপপাদ্য ১৫."`. All pass. **Also did not fire live in batch 15** (same reason as Task 1 -- this batch is Chapter 7 constructions, no numbered theorems on these 10 pages).

## Task 3 — figure labels across a blank line

`find_figure_label_runs()` no longer requires LITERAL consecutiveness: a blank line now keeps a run open (without counting toward its length) instead of ending it. A removed run's span (first label line to last, interior blanks included) collapses to exactly ONE blank line in the output rather than deleting outright, so two real paragraphs on either side of a stripped figure don't get mashed together. Tests: `"P\n\nC\n\nB\n\nQ"` (as a whole text) → collapses to empty; `"(i)\n\nকোনো লেখা"` stays untouched (only 1 label, flagged suspect, not removed); `"∴ x = 5"` stays (not a label line at all).

**Fired live, twice, in this very batch:**
- **Page 142** (`figure_labels_removed: 25`, on the reading that was NOT chosen as the final output -- see its `.alt.raw.txt`): six small construction diagrams' point labels (`a`,`b`,`x`,`E`,`A`,`C`,`B`,`y`,`F`,`G`,`D`,`c`...) were scattered through a numbered list of triangle-construction cases. These particular clusters turned out to already be literally consecutive (no blank lines needed) -- so this specific instance would have fired under the OLD rule too -- but confirms the removal logic handles a real, dense, multi-cluster page correctly without touching the list's own numbered headings or the closing paragraph.
- **Page 148** (`figure_labels_removed: 6`, chosen output): two separate 3-line clusters of stray `X`/`4`/page-number removed from around a square-construction diagram. **This one DOES exercise the new blank-line-tolerance** -- line 2 (`"১৪৩"`, directly adjacent) + line 3 (`"X"`) + a blank line + line 5 (`"X"`) form one cluster only because the blank line no longer breaks it.

## Task 4 — figure value loss flag

New: any removed run's label lines that are purely a number (optionally with ° / ⁰) are called out by value in `figure_values_lost`, never reconstructed. Test: a run of `"30°"`, `"40°"`, `"A"` → removed, `figure_values_lost: "30°, 40°"` (the `"A"` itself isn't a value, correctly excluded).

**Fired live on page 148**: `figure_values_lost: ১৪৩, 4`. **Worth flagging honestly**: `"১৪৩"` here is actually just this page's own running-header PAGE NUMBER (PDF page 148 − offset 5 = printed ১৪৩ -- confirmed via `detect_page_number_mismatch`'s own offset table) -- it happened to sit immediately next to the real stray `"X"` labels and got swept into the same cluster. The other value, `"4"`, came from a broken diagram fraction (`"1/4p"` split across lines near `"2 s"` / `"P 1"` / `"--- p"`, themselves NOT label-shaped so left untouched) -- also not a clean "angle value" in the sense Task 4's own examples (p137/p139's 30°/40°/120°/150°) described. **Not fixed or filtered out** -- the task said flag, not judge, so both are reported as-is; a human checking page 148's image should expect one of the two flagged values to just be page-number noise.

## Task 5 — margin year (unknown year)

New `strip_margin_year_tail()`: if a page's LAST non-empty line is exactly 4 digits (Bangla or Latin) starting with ২০/20, it's stripped regardless of which specific digits (catches a misread year like page 137's "২০২৯" that the fixed `MARGIN_YEAR_TOKENS` list can't name in advance), noted as `margin_year_tail: <year>`. Scoped to only the last line -- never a middle one. Tests: `"...\n২০২৯"` → year stripped, noted; `"...\n2029"` → same for Latin digits; a 4-digit token in the MIDDLE of the page → untouched; a non-২০/20-prefixed 4-digit tail (`"১২৩৪"`) → untouched. All pass. **Did not fire in batch 15** (no page in this batch had a stray year at the very end) -- its only real-page confirmation so far remains page 137 (re-tested directly against its raw text, read-only, not reprocessed since that page is in MANUAL_PAGES.txt).

## Task 6 — batch 15 (pages 141-150)

**No RECITATION at all this batch.** Already in **Chapter 7** (ব্যবহারিক জ্যামিতি, practical/construction geometry) as of page 142.

| Page | Chars | Note |
|---|---|---|
| 141 | 1426 | 1 typo fix |
| 142 | 565 | **`figure_labels_removed: 25`** on the non-chosen reading (see Task 3) -- chosen reading itself clean |
| 143 | 1014 | 4 typo fixes (secondary); 1 line flagged `figure_labels_suspect` |
| 144 | 1163 | 7 typo fixes (Chapter 7 opening page) |
| 145 | 1200 | `page_number_mismatch` flagged (header read as ১৮০, expected ১৪০) -- flag only |
| 146 | 800 | clean (secondary has 1 flagged line) |
| 147 | 1854 | `latex_left: \angle,\circ` flagged (pre-existing limitation, not in scope for this batch -- these two LaTeX commands aren't in the symbol map yet); `page_number_mismatch` on secondary |
| **148** | 1408 | **`figure_labels_removed: 6`, `figure_values_lost: ১৪৩, 4`** -- see Tasks 3/4 above; also `latex_left: \angle,\circ,\perp` (same pre-existing limitation) |
| 149 | 1314 | 1 typo fix; `page_number_mismatch` flagged (header read as ১৪৮, expected ১৪৪) |
| 150 | 2696 | 1 typo fix; several lines flagged `figure_labels_suspect` (longest page this batch) |

All 10 pages got both the primary (temp 0) and secondary (temp 0.4) bn readings.

## Cost

Batch 15: 20 Gemini calls (10 pages × primary+secondary, no escalation needed).
**Cumulative gemini-3.5-flash-lite spend (Step 4 total so far): $0.5864** (502,881 in / 174,212 out tokens) of the $7.00 stop.

## Task 7 — commit + push

`git status` checked first: no `.env`/API keys/`venv` in the diff (only `full_gemini_ocr.py`, `RUN_LOG.csv`, `digit_disagreements.csv`, and this batch's new `backend/data/ocr_gemini/class_9_General_math_bn/page_141..150.*` files).

**Push result:** _(filled in after the push below)_

---

**Batch ready: class_9_General_math_bn pages 141-150.**
