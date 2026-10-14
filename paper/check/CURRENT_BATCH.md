# Step 4 — Current batch for review

**Book:** class_9_General_math_bn (book 1/10 in BOOK_ORDER)
**Pages:** 131–140 (of 362) — batch 14. Batch 13's images cleared (text files untouched).
**Settings:** all prior accumulated fixes, plus **FIX_BATCH13**: `_DUTI_RE`/`_DBIMATO_RE`/`_SONKHYAK_RE` word-boundary bugs fixed, prompt symbol-leak fix + 5 new Unicode symbols, margin-year 2021/2022, `∥` parallel-symbol fix, and a new `figure_labels_removed`/`figure_labels_suspect` QC step. **No RECITATION this batch — `escalate_split` was not exercised live** (see Task 1 note below on the earlier two batches' own standalone test).

## Task 1 — `_DUTI_RE` word-boundary bug + review of the rest

Fixed `_DUTI_RE` exactly as specified: `re.compile(r"(?<![ঀ-৿])দুটি")` (negative lookbehind for any Bangla character, since Python's `\b` doesn't treat Bangla conjuncts/matras reliably). Test: `"বিন্দুটি"` unchanged; `"দুটি"`, `"দুটিকে"`, `"(দুটি"` → `"দুইটি"`/`"দুইটিকে"`/`"(দুইটি"`. All pass.

**Reviewed every other regex in `fix_known_bangla_typos()` by actually running each one against the real corpus (pages 1-130's `.raw.txt`/`.alt.raw.txt`, both directions: Bangla char immediately before the match, and immediately after) instead of reasoning in the abstract. Found two more REAL, confirmed instances of the same bug class — both fixed:**

- **`_DBIMATO_RE`** (`"দ্বিমাত"` → `"দ্বিঘাত"`, meant to fix a "quadratic" typo) was a literal PREFIX of `"দ্বিমাত্রিক"` ("two-dimensional") and `"দ্বিমাত্রা"` ("two dimensions") -- real geometry vocabulary, confirmed by running the function directly on page 106's own raw.txt (the exact page this rule was written for): it silently turned `"দ্বিমাত্রিক"` into `"দ্বিঘাত্রিক"` (nonsense). This never showed up in the delivered `page_106.txt` only because that page was later hand-rewritten by a human (MANUAL_PAGES.txt) -- the bug was live and armed, not merely theoretical, and Chapter 6 (solid geometry: points/lines/**planes**) is exactly where it would keep biting. Fixed: `re.compile(r"দ্বিমাত(?!্র)")` -- blocks both bad continuations (both start with "্র") while the real typo (always followed by a space before "সমীকরণ") still matches.
- **`_SONKHYAK_RE`** (`"সংখ্যাক"` → `"সংখ্যক"`) was a literal PREFIX of the extremely common `"সংখ্যাকে"` ("the number", object case -- "সংখ্যা" + the everyday "-কে" suffix). 57 real occurrences found across pages 1-130's raw text that would hit this collision; none have corrupted the delivered corpus yet only because this rule (FIX_BATCH10) postdates those pages' processing. Fixed: `re.compile(r"সংখ্যাক(?!ে)")`.

All three fixes unit-tested (unchanged on the real word, still fires on the real typo) -- see the commit for the test transcript.

**Read-only scan requested by the task** (`class_9_General_math_bn` pages 1-130, "[Bangla char]দুইটি"-style broken words): **0 found in the delivered `page_N.txt` files.** Also checked `page_N.alt.txt` (not asked, but free to check): 2 found -- pages 123 and 124, the exact two ERRORS_LOG already flagged (their main `.txt` output is already hand-fixed per MANUAL_PAGES.txt; the `.alt.txt` copies were left as-is, untouched, per the "don't touch anything" rule).

## Task 2 — prompt: symbol leak + new symbols

Replaced the negation-slash sentence (its own `R̸` example was being copied verbatim into real answers -- p129's `AB = AC ≠ BC` came back as `AB = AC R̸ BC`): now "Keep negation slashes on symbols exactly as printed (∉, ≠, ⊄) -- never drop them, and never replace one symbol with another." Added `∠ ∥ Δ ° ≠` to the Unicode symbol list (Chapter 6 geometry needs them -- p123's `∠POQ` had lost its `∠` three times).

## Task 3 — three small post-process additions

(a) `MARGIN_YEAR_TOKENS` += `"২০২১"`, `"২০২২"`, `"2021"`, `"2022"`.
(b) New `fix_parallel_symbol()`: `"AB || CD"` → `"AB ∥ CD"`. **Real bug caught running batch 14 itself** (not a synthetic test): the task's own literal regex (`([A-Z]{2})\s*\|\|\s*([A-Z]{2})` → `\1 ∥ \2`) consumes both flanking tokens, so a 3-way chain -- page 139's real `"AB || EF || CD"` -- only converted the first `||` (`"AB ∥ EF || CD"`), since `"EF"` was already spent as the first match's own capture group and had nothing left on its right to anchor a second match. Fixed with fixed-width lookaround instead of capturing letters (`(?<=[A-Z]{2})\s*\|\|\s*(?=[A-Z]{2})` → `" ∥ "`), so neither token is consumed and every `||` in a chain converts independently. Re-verified: `"AB || EF || CD"` → `"AB ∥ EF ∥ CD"`. Page 139 was reprocessed with `--reprocess-only` (no new API calls) after the fix, confirmed now reads `"AB ∥ EF ∥ CD"` correctly.
(c) New `strip_figure_labels()` / `find_figure_label_runs()`: a run of **3+ consecutive** short (≤4 char), non-Bangla, letter/digit/x/y/°⁰/(i)(ii)-style lines is removed outright (`figure_labels_removed: N` in the QC note); a run of 1-2 is left alone and only flagged (`figure_labels_suspect`). Test: a p130-style sample with a 10-line label run gets the whole run removed, while `"∴ x = 5"` and a lone `"(i)"` survive untouched (confirmed: `"(i)"` alone → 0 removed, flagged as `figure_labels_suspect: L2`).

**Both new fixes fired for real in this very batch, not just in synthetic tests:**
- Page 136: `figure_labels_removed: 6` -- a run of `C`/`B`/`O` and a separate run of `Q`/`A`/`R` (triangle-vertex labels) removed; a lone `P` right before them survived (it was isolated by a blank line from the next run, so "3+ *consecutive*" correctly didn't reach across the blank line -- a known, intentional limitation of "consecutive" as specified, not a bug: flagged here for visibility rather than silently left unmentioned).
- Page 137: the *secondary* (temp 0.4) reading had a cleaner 13-line label run removed; the *primary* (chosen as the page's main output, since it had fewer OTHER quality issues) has the same labels scattered as non-consecutive 1-2-line runs, so they're only flagged (`figure_labels_suspect`, many lines) not removed -- worth a human glance at page 137's image.
- Page 139: `parallel_fixes: 2` -- see the chain-bug fix above.

## Task 4 — batch 14 (pages 131-140)

**No RECITATION at all this batch** -- all 20 calls (10 pages × primary+secondary) returned `OK ... finish_reason=STOP` on the first attempt. The new `escalate_split` ladder step (FIX_BATCH12) was therefore **not exercised live** in batch 13 or 14 -- its only real-page confirmation remains the standalone test against batch 12's pages 117/119/120 (see batch 13's report / RUN_LOG). Will report again the moment a page actually blocks.

| Page | Chars | Note |
|---|---|---|
| 131 | 1137 | 2 typo fixes; 1 line flagged `figure_labels_suspect`/`stacked_fraction` |
| 132 | 1201 | 1 line flagged `figure_labels_suspect`/`stacked_fraction` |
| 133 | 1288 | `script_digit_mismatch` flagged (1 Bangla digit on a math-like line) -- flag only |
| 134 | 1120 | 1 line flagged `figure_labels_suspect`/`stacked_fraction` |
| 135 | 711 | clean on both readings |
| 136 | 785 | **`figure_labels_removed: 6`** (see Task 3c) |
| 137 | 733 | heavy `figure_labels_suspect`/`stacked_fraction` flagging (13 lines) on the chosen primary reading -- worth a visual check against the image |
| 138 | 1395 | 13 typo fixes; 1 line flagged |
| 139 | 940 | **`parallel_fixes: 2`** (chain bug caught+fixed, see Task 3b) |
| 140 | 1021 | 1 line flagged `figure_labels_suspect`/`stacked_fraction` |

All 10 pages got both the primary (temp 0) and secondary (temp 0.4) bn readings, per policy.

## Cost

Batch 14: 20 Gemini calls (10 pages × primary+secondary, no escalation needed), plus one `--reprocess-only` pass after the Task 3b fix (0 new API calls, $0 cost).
**Cumulative gemini-3.5-flash-lite spend (Step 4 total so far): $0.5565** (471,941 in / 165,963 out tokens) of the $7.00 stop.

## Task 5 — commit + push

`git status` checked first: no `.env`/API keys/`venv` in the diff (only `full_gemini_ocr.py`, `RUN_LOG.csv`, `digit_disagreements.csv`, and this batch's new `backend/data/ocr_gemini/class_9_General_math_bn/page_131..140.*` files). Committed and pushed -- see the one-line result appended below after the push.

---

**Batch ready: class_9_General_math_bn pages 131-140.**
