# Step 4 — Current batch for review

**Book:** class_9_General_math_bn (book 1/10 in BOOK_ORDER)
**Pages:** 181–190 (of 362) — batch 19. Batch 18's images cleared (text files untouched).
**Settings:** all prior accumulated fixes, plus **FIX_BATCH18**: NFC normalisation (fixes a silent pattern-matching bug on য়/ড়/ঢ়), দুটি/দুইটি now flag-only, page-number auto-fix widened to ৭↔৯ (was ৪↔৮ only), and script_leak widened (Telugu/Kannada/Malayalam + ZWJ-in-Bangla-word flag) plus a new ৰ→র auto-fix. **No RECITATION this batch.**

## Task 1 — জরুরি bugfix: Unicode NFC normalisation
`য়`/`ড়`/`ঢ়` each have two valid codepoint forms (one precomposed single character, or a "base letter + nukta" 2-codepoint sequence) — same glyph, invisible in any diff, but a regex typed in one form silently never matches text in the other. Confirmed live: p174's `_LOKKHONIYO_RE` pattern was typed in the file as the decomposed form, but Gemini's own p174 output used the precomposed form, so FIX_BATCH17's own "fix" never actually fired there.

Fix: `post_process()` now runs `unicodedata.normalize("NFC", text)` as its very first step (these 3 letters are on Unicode's composition-exclusion list, so NFC *decomposes* them rather than composing them — the opposite of its usual behaviour). Every module-load-time pattern/replacement literal containing one of these letters (`_CHAPTER_WORD`, `_NIYAMABOLI_RE` + its replacement, `_LOKKHONIYO_RE` + its replacement) is now run through the same `_nfc()` helper, so both sides always land in the same form. Confirmed the two literals really were in the decomposed form (not the precomposed form `_CHAPTER_WORD` itself uses) by slicing the exact bytes out of the file rather than retyping them.

**Test:** both codepoint forms of "লক্ষনীয়" now correctly normalise and fix to "লক্ষণীয়". Re-ran on p174.raw.txt — fires correctly now.

**Regression, full corpus (page_1..180, primary + alt.raw.txt where present, 334 files, old pipeline vs new):**

| Rule | Before | After | Δ |
|---|---|---|---|
| `লক্ষনীয়→লক্ষণীয়` (`_LOKKHONIYO_RE`) fires | 0 | 7 | +7 |
| `নিয়ামাবলি→নিয়মাবলি` (`_NIYAMABOLI_RE`) fires | 0 | 1 | +1 |
| `typo_fixes` (aggregate of all 25 rules) | 585 | 593 | +8 |
| `exercise_chapter_mismatch` flag count | 21 | 22 | +1 |
| `heading_digit_fixed` | 2 | 2 | 0 |
| `page_number_fixed` (auto-fix count) | 17 | 17 | 0 |
| `page_number_mismatch` flag | 14 | 14 | 0 |
| `script_leak` / `devanagari_leak` / `overline` | 8 / 18 / 2 | unchanged | 0 |

**Notable:** the 7 new লক্ষনীয় fires land on p85 (1, new — not previously flagged by any batch), p142 (×2 readings), p162 (×2), p174 (×2). **p142 and p162 were both reported as "fixed" back in FIX_BATCH17's own review** — this regression shows that fix silently never actually fired on the real corpus text either, for the exact same codepoint-mismatch reason as p174; those two pages only read correctly in the delivered corpus because they were later overwritten by MANUAL_PAGES.txt human review, not because the rule worked. All 3 affected pages (85, 142, 162 — 174 already covered) are already in MANUAL_PAGES.txt territory or will be flagged for Claude (chat) to re-check against the images.

## Task 2 — দুটি→দুইটি auto-fix turned off
The book genuinely prints BOTH spellings (p178 batch 18 had a real, correctly-printed "দুটি" that the old rule was silently turning into the wrong "দুইটি"). `_DUTI_RE` is kept (for visibility) but no longer replaces — `fix_known_bangla_typos()` now returns a separate `duti_seen` count, surfaced as a flag-only `duti_seen: N` line in `build_qc_note`/RUN_LOG, for Claude (chat) to decide per occurrence against the page image.

## Task 3 — page-number auto-fix widened to ৭↔৯
`fix_page_number_swap()`'s single-pair ৪↔৮ check (FIX_BATCH15) is now `_digit_swap_target()`: auto-corrects when the read header number and the expected number differ at **exactly one** digit position, and that position's pair is `{৪,৮}` **or** `{৭,৯}`. Any other kind of mismatch (more than one differing position, or an unlisted pair) stays flag-only, same as before.

**Tests (from the task spec):** ১৯০ (expected ১৭০) → ১৭০ ✓; ১৮০ (expected ১৪০) → ১৪০ ✓; ১৩৫ (expected ১২৮) → flag only, unchanged ✓.

**Fired live in this very batch** (not just the test cases): p182's header read ১৯৭ (expected ১৭৭) → auto-fixed; p183's header read ১৯৮ (expected ১৭৮) → auto-fixed (both readings). These are exactly the p175-177-style ৭/৯ misreads the task was written to catch, now fixed automatically instead of needing a manual flag.

## Task 4 — script leak: Telugu/Kannada/Malayalam + ZWJ, and a real ৰ→র fix
`_SCRIPT_LEAK_RE`'s combined Indic range widened from U+0A00–U+0BFF to U+0A00–U+0D7F (adds Telugu, Kannada, and the task's named Malayalam block — p175's "অন্তর্লিখিত" had picked up a stray Malayalam "র্" cluster). Added `find_zwj_in_bangla_words()` — a ZWJ (U+200D) glued inside an otherwise-Bangla word is flagged separately (`zwj_in_bangla_word`) since the ZWJ character itself isn't in any script's own codepoint block and wouldn't be caught by the range check alone. ৰ (U+09F0, Assamese RA) is now a genuine auto-fix → র (this book never prints ৰ, unlike ৱ which stays flag-only with no safe substitute).

**Tests:** Malayalam+ZWJ synthetic word → `script_leak: 2`, `zwj_in_bangla_word` flagged ✓. "সম্পৰ্কযুক্ত" (real batch-4 example) → auto-fixed to "সম্পর্কযুক্ত" ✓.

**Full-corpus sanity (pages 1-180, 334 raw+alt files, all 4 tasks combined): 0 crashes.**

## Task 5 — batch 19 (pages 181-190)

**No RECITATION, no escalation needed.** Chapter 9 (ত্রিকোণমিতিক অনুপাত — Trigonometric Ratios) continues throughout; this book alternates its running header by page side — even pages print the chapter-title header, odd pages print the plain "<num> গণিত" header.

**Pre-existing stray data found (not part of this task, flagged not silently fixed):** page 181 already had output files, dated 2026-10-06 under the old `gemini-3.6-flash` model — a leftover from Step 3d's model-comparison test (it's listed in `paper/check/STALE_PILOT.txt`). The pipeline's existing `[STALE_PILOT]` auto-force logic handled this correctly and transparently: it re-OCR'd page 181 under the current `gemini-3.5-flash-lite` pipeline as part of this batch, no manual intervention needed.

| Page | Chars | Note |
|---|---|---|
| 181 | 496 | `latex_left: \alpha,\beta,\phi,\theta` — Gemini wrote Greek-letter angle names as LaTeX instead of Unicode; digit_disagreements on the triangle-labels exercise (7/24, 12/9/15, 36/27/45) |
| 182 | 1303 | `page_number_fixed: ১৯৭->১৭৭` (task 3 firing live); `stacked_fraction: L2` |
| 183 | 880 | `page_number_fixed: ১৯৮->১৭৮` (task 3 firing live, both readings) |
| 184 | 1124 | typo_fixes: 2; `latex_left: \boxed,\cos,\cot,\csc,\sec,\sin,\tan,\theta`; `stacked_fraction: L2` |
| 185 | 986 | clean |
| 186 | 904 | `latex_left: \cos,\sec,\sin,\theta`; `stacked_fraction: L2`; digit_disagreement on a trig identity line |
| 187 | 993 | `latex_left: \cos,\sec,\sin,\tan,\theta` |
| 188 | 891 | `stacked_fraction: L2`; `fraction_parens: L15` (primary) / `L9,L10` (secondary); digit_disagreements on 2 trig-simplification lines |
| 189 | 1142 | `latex_left: \cos,\cot,\csc,\sec,\sin,\tan,\theta`; `fraction_coefficient: L10`/`L13` |
| 190 | 1292 | `latex_left: \cos,\cot,\frac,\operatorname,\sec,\sin,\tan,\theta`; `stacked_fraction: L2` |

**Notable new pattern this batch (flagged, not fixed — out of this task's scope):** Chapter 9 is entirely trigonometry, and Gemini is consistently writing trig function names and Greek letters as literal LaTeX (`\sin`, `\cos`, `\tan`, `\sec`, `\csc`, `\cot`, `\theta`, `\alpha`, `\beta`, `\phi`, `\boxed`, even a bare `\frac`/`\operatorname` on p190) despite the prompt's "not LaTeX" instruction — `find_latex_leftover()`'s existing `latex_left` flag is correctly catching every instance (no silent loss), but this will recur heavily for the rest of this trig-heavy chapter. Worth a dedicated FIX_BATCH task to add `\sin`/`\cos`/`\tan`/`\sec`/`\csc`/`\cot` → plain function names and `\theta`/`\alpha`/`\beta`/`\phi` → Greek Unicode (θ/α/β/φ) to `_LATEX_SYMBOL_MAP`, same pattern as the existing `\angle`/`\Delta` handling.

Tasks 1/2/4's rules did not fire live in this batch's own 10 pages (no দুটি, no script-leak/ZWJ content, no য়/ড়/ঢ় typo-pattern words here) — only task 3 did, twice. That's expected for a 10-page sample; the pages 1-180 regression above is where tasks 1/2/4's real impact shows.

## Cost

Batch 19: 20 Gemini calls (10 pages × primary+secondary, no escalation needed).
**Cumulative gemini-3.5-flash-lite spend (Step 4 total so far): $0.7199** (627,441 in / 212,677 out tokens) of the $7.00 stop. Batch 19 itself: +31,140 in / +9,520 out tokens, +$0.0331.

## Task 6 — commit + push

`git status` checked first. Committed and pushed to `origin/main`.

---

**Batch ready: class_9_General_math_bn pages 181-190.**
