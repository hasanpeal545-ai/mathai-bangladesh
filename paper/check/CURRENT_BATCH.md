# Step 4 — Current batch for review

**Book:** class_9_General_math_bn (book 1/10 in BOOK_ORDER)
**Pages:** 151–160 (of 362) — batch 16. Batch 15's images cleared (text files untouched).
**Settings:** all prior accumulated fixes, plus **FIX_BATCH15**: ৪↔৮ page-number self-fix, ASCII-art figure stripping, Markdown/Latin-leak handling, 5 new LaTeX symbols. **No RECITATION this batch.**

## Task 1 — page number ৪↔৮ self-fix

`detect_page_number_mismatch()` is now backed by a shared `_header_number_candidates()` scan and a new `fix_page_number_swap()`: when the header's read number and the expected number are the **same length and differ only at ৪↔৮ digit positions**, the header is corrected in place (qc note `page_number_fixed: <read>-><expected>`); any other kind of mismatch (extra/missing digit, non-4/8 digit error, Latin-script misread) is still flag-only, unchanged. Also added a new `page_number_missing` flag for a chapter-opening title line (`অধ্যায় N. <title>`) with no page number anywhere on it (p144) — distinct from a bare `অধ্যায় N` title-divider page (p141), which never prints a number by design and stays silently unflagged.

**Why p147/p150 "didn't fire" last batch, investigated as asked:**
- **p147 actually DID fire** — on the secondary (temp 0.4) reading, which was the one quality-promoted into the final output (RUN_LOG confirms `page_number_mismatch: header number(s) ['১৮২']...` attached to that row). The *primary* reading had read the number correctly (`১৪২`) and so had nothing to flag — not a bug, just a case where the cleaner-looking reading happened to have the wrong digit.
- **p150 genuinely never fired** — real bug, now fixed. Its header is a different layout this book also uses: the full `অধ্যায় ৭. ব্যবহারিক জ্যামিতি` chapter-title line with the page number appended far to the right (`...জ্যামিতি` + a wide space gap + `১৮৫`), not the usual short `<num> গণিত` header. The old `_HEADER_LIKE_LINE_RE`-only check required the *whole* line to be just digits/"গণিত", so a real title line never matched and its number was never looked at. New `_CHAPTER_TITLE_TRAILING_NUM_RE` recognizes this layout specifically.
- **A second, more basic bug found underneath both of these**: `_CHAPTER_WORD` (used by `_CHAPTER_NUMBER_RE` and now by the two new chapter-title regexes) was a plain typed string literal that had silently NFD-normalized to the *decomposed* "য়" (U+09AF + nukta) instead of the *precomposed* form (U+09DF) the OCR output actually uses — despite the code's own existing comment warning this exact thing could happen. This made every "অধ্যায়"-matching regex a silent no-op; it was never visibly wrong before because the one place it used to matter (p141's bare `অধ্যায় N` divider page) produces the same "skip, no number" result wheither way. Rebuilt `_CHAPTER_WORD` from `chr()`-joined plain decimal code points, which can't be silently renormalized by any future save/editor round-trip.
- Found and fixed two more real-page separator variants while testing against the whole book, not just this batch: a **tab** separator (p130: `...ত্রিভুজ<TAB>১২৫`) and **no separator at all**, the number glued straight onto the title word (p268: `...ধারা২৬৩`) — both initially produced a false `page_number_missing` before the trailing-number regex was loosened to accept any gap width.

**Tests (from the task spec) pass**: `"১৮০\nগণিত"` (expected ১৪০) → `"১৪০\nগণিত"`; `"১২৮"` (expected ১২৮) unchanged; `"১৩৫"` (expected ১২৮) → unchanged text, flag only.

**Swept the whole already-OCR'd book (152 pages) as a regression check**: 7 pages auto-fixed (p45, p109, p129 — pre-existing known mismatches, now corrected retroactively too — plus the 4 from this batch's own review: p145/147/149/150), 2 genuine `page_number_missing` (p104, p144), 2 correctly left flag-only (p49's Latin-digit misread, p69's ৫↔৬ misread — not a 4/8 swap). Zero crashes, zero new false positives.

## Task 2 — ASCII-art figures

Prompt gained `"Do not draw figures or diagrams; skip them."` (appended, English, no example). New `strip_ascii_figures()`: a line with a run of ≥4 consecutive `_`/`-`, or where ≥50% of non-space characters are drawing glyphs (`_ - | / \ * . ' +`, ASCII-only — never the proper Unicode minus `−` this book uses for real subtraction), is "ASCII-art"; a run of ≥2 such lines (blank or figure-label lines in between stay transparent, same tolerance as the existing figure-label-run logic) is removed, noted `ascii_figure_removed: N`; a lone instance is left untouched, only flagged (`ascii_figure_suspect`). Test confirms `"AB − AC = d"` and `"x = 1/2"` are untouched (the proper minus sign and a plain fraction never match the ASCII-only character set); a lone `"-----"` line is flagged, not removed. **Retroactive test against p147's real raw text**: now correctly strips 21 ASCII-art lines instead of leaving them in the output.

## Task 3 — Markdown and Latin leak

(a) New `strip_markdown_bold()`: `**text**` / `__text__` → `text`, note `markdown_stripped: N`. Retroactive test against p150's real raw text strips 46 instances.
(b) New `find_latin_in_bangla_words()`: a whitespace-delimited token mixing Bangla script with a **lowercase** Latin letter (no space between) is flagged `latin_in_bangla_word: <word>`, never corrected — uppercase A-Z excluded entirely (this book legitimately writes geometry names like "ABC" next to Bangla text). Retroactive test against p149's real raw text correctly flags `নিমne` and nothing else.

## Task 4 — LaTeX map additions

Added to the symbol map: `\perp`→⊥, `\parallel`→∥, `\triangle`→Δ, `\cong`→≅, `\circ`→°. `\angle`→∠ got its own regex instead of a plain dict entry so the trailing space after the command is consumed too (this book always writes `∠ABC`, never `∠ ABC` — confirmed by grepping the whole corpus). `^\circ` / `^{\circ}` resolve to a plain `°` via a dedicated regex that runs first, before anything else (including the generic superscript handler) can see the `^`. Tests pass: `"60^\circ"` → `"60°"`, `"\angle BAD"` → `"∠BAD"`.

## Task 5 — figure_values_lost header exclusion

`find_figure_label_runs()` now skips the first 2 lines (this book's own header zone) entirely when scanning for label-line runs — a header page number can no longer be swept into a removed figure-label cluster or reported as a "lost value". **Retroactive test against p148's real raw text**: `figure_values_lost` now correctly reports just `4` instead of `১৪৩, 4` (১৪৩ was always just that page's own header number, confirmed via `detect_page_number_mismatch`'s offset table).

## Task 6 — batch 16 (pages 151-160)

**No RECITATION, no escalation needed.** Still in Chapter 7 (ব্যবহারিক জ্যামিতি, practical geometry).

| Page | Chars | Note |
|---|---|---|
| 151 | 2905 | clean; secondary (discarded alt) had `page_number_fixed: ১৮৬->১৪৬` |
| 152 | 2603 | clean both readings |
| 153 | 1605 | clean; secondary (discarded alt) had `page_number_fixed: ১৮৮->১৪৮` |
| **154** | 2047 | **`page_number_fixed: ১৮৯->১৪৯`** — fired on BOTH readings this time, so it's in the final delivered text (verified: `page_154.txt`'s header now reads `১৪৯`, the correct number) |
| 155 | 4296 | clean both readings |
| 156 | 3107 | 1 typo fix; `sqrt_parens: 5` |
| 157 | 4021 | clean |
| 158 | 3996 | clean |
| 159 | 2851 | secondary promoted (1 < 3 issues); 4 typo fixes; `latex_left: \Delta` flagged — **new leftover, not one of Task 4's named symbols** (capital `\Delta` means something different in context from `\triangle`, e.g. "change in x" — left for a future task to decide the right mapping rather than guessed at here) |
| 160 | 2469 | clean |

Tasks 2/3/5 did not fire live in this specific batch (no ASCII art, Markdown, or Latin-leak content, and no figure-label runs, on these 10 pages) — all three are verified against real prior-batch data instead (see their sections above). Task 1 fired 3 times (p151/153 alt only, p154 on the final output).

## Cost

Batch 16: 20 Gemini calls (10 pages × primary+secondary, no escalation needed).
**Cumulative gemini-3.5-flash-lite spend (Step 4 total so far): $0.6203** (534,021 in / 184,038 out tokens) of the $7.00 stop.

## Task 7 — commit + push

`git status` checked first: no `.env`/API keys/`venv` in the diff (only `full_gemini_ocr.py`, `RUN_LOG.csv`, `digit_disagreements.csv`, this file, and this batch's new `backend/data/ocr_gemini/class_9_General_math_bn/page_151..160.*` + `paper/check/class_9_General_math_bn/page_151..160.png` files).

**Push result:** committed as `3ede07e` ("Batch 16: OCR p151-160 + FIX_BATCH15 (page no 4/8 fix, ASCII figures, markdown/latin leak, LaTeX symbols)") and pushed to `origin/main` successfully (`3b66915..3ede07e`) -- this push also carried up an earlier unpushed commit (`c5abd98`, the Batch 15 human-review commit that produced FIX_BATCH15.md itself, made by a separate session, not this one).

---

**Batch ready: class_9_General_math_bn pages 151-160.**
