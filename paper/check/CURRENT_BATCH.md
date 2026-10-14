# Step 4 — Current batch for review

**Book:** class_9_General_math_bn (book 1/10 in BOOK_ORDER)
**Pages:** 171–180 (of 362) — batch 18. Batch 17's images cleared (text files untouched).
**Settings:** all prior accumulated fixes, plus **FIX_BATCH17**: a real bug fix (ASCII-art rule was deleting Markdown tables), trailing same-line figure labels, visarga→colon, and 2 spelling fixes. **No RECITATION this batch.**

## Task 1 — real bug fix: the ASCII-art rule was deleting a real Markdown table
`_is_ascii_art_line()` now excludes any line that both starts AND ends with `|` (a Markdown table row — header, separator, or data) before it even checks the `|`-density heuristic that was wrongly firing on them. Also excludes a bare `---|---|---`-style separator row without enclosing pipes, per the task's own second bullet, though every separator actually observed in this corpus already has them.

**Regression, full corpus (page_1..170, both readings where present):** 27 Markdown table-row lines exist across the whole corpus (all on page 166 — the only page with a real table so far); under the OLD rule, **14 of those 27 would have been wrongly deleted** as ASCII art. Under the new rule: **0**. Re-verified p147/p150's real hand-drawn ASCII art (the original target of this rule) is still fully caught — neither page has any line that both starts and ends with `|`, so the exclusion can't suppress real art there.

## Task 2 — same-line (trailing) figure labels
Two additions, both verified against the real page-168 content and the task's own test cases:
- **`strip_trailing_figure_labels()`**: a line ending in ≥8 spaces then only 1-3 short tokens (a single uppercase Latin letter, or a parenthesized single Bangla character like `(ক)`) gets that tail cut — `trailing_labels_removed: N`. Test passes: `"AB = 3          D"` → `"AB = 3"`; the tab-separated MCQ test case is correctly left unchanged (the rule requires literal spaces, not tabs).
- **Whitespace-majority label lines** (no Bangla, ≥70% whitespace, remaining tokens all short Latin, e.g. page 168's `"P   AP   P"`) now also count as label lines inside the *existing* run-based `find_figure_label_runs()` machinery, via `_is_figure_label_line()`.

**2 real bugs found and fixed while testing against page 168 itself, not assumed up front:** (1) the trailing-run regex, applied to a line that is *entirely* label tokens, would partially match from its last internal gap and chop off just the final token instead of leaving the whole line for the run-based remover — fixed by skipping any line `_is_figure_label_line()` already recognizes as a whole-line label, checked regardless of which function runs first. (2) separately, a line with *nothing but* parenthesized-Bangla tokens (page 168's own `"(খ)                     (গ)"`, two sub-item markers positioned over two sub-figures) could still be matched end-to-end by the trailing-run regex itself, silently doing the whole-line job *without* that job's explicit Bangla exclusion — fixed by also requiring real, non-empty content before the matched gap. Both fixes verified live: page 168's actual figure-label cluster (P/AP/A/Q/Q, 3 removed) now collapses cleanly, its 4 genuine trailing labels (D, C, O, "A B") are removed, and the Bangla sub-marker line is correctly left untouched (out of this task's stated scope).

## Task 3 — ঃ/। punctuation
- **Visarga→colon**: `মন্তব্যঃ`/`অঙ্কনঃ`/`প্রমাণঃ`/`সমাধানঃ`/`কাজঃ` at the start of a line → `:` (word kept, just the glyph swapped). Verified these 5 fire correctly and that genuine mid-word visarga (`দুঃখ`, `অন্তঃস্থ`, `বহিঃস্থ`) is never touched.
- **Tab after question-number dari**: `_QUESTION_NUMBER_PERIOD_RE` only matched a literal space after `।` — confirmed broken exactly as the task suspected (page 167's `"১।\tΔABC..."` uses a tab). Fixed by capturing and reusing whichever of space/tab was actually there, rather than normalizing it away (so a tab used for MCQ column alignment elsewhere on a page is never disturbed).

## Task 4 — spelling
`অন্তলিখিত`→`অন্তর্লিখিত` (র-ফলা restored; page 167 ×3) and `লক্ষনীয়`→`লক্ষণীয়` (page 142/162). Both scoped and tested per the task's own guidance (word-start lookbehind for the first; a plain literal for the second, consistent with this file's other single-word fixes).

**Full-corpus regression (473 raw+alt files, all 4 tasks combined): 0 crashes.** The 3 non-manually-fixed batch-17 pages (163, 165, 170) were also re-checked against the new rules — none would change.

## Task 5 — batch 18 (pages 171-180)

**No RECITATION, no escalation needed.** Chapter 8 (বৃত্ত, Circle) ends around page 178; **Chapter 9 (ত্রিকোণমিতিক অনুপাত — Trigonometric Ratios) begins at page 179.**

| Page | Chars | Note |
|---|---|---|
| 171 | 1519 | 8 typo fixes |
| 172 | 1569 | 3 typo fixes; `stacked_fraction: L2` |
| 173 | 1585 | clean |
| 174 | 1651 | 2 typo fixes |
| 175 | 1267 | 2 typo fixes; `page_number_mismatch`: header `১৯০` vs expected `১৭০` |
| 176 | 1336 | `script_leak: 1`; `page_number_mismatch`: header `১৯১` vs expected `১৭১`; `script_digit_mismatch` |
| 177 | 797 | 2 typo fixes; `page_number_mismatch`: header `১৯২` vs expected `১৭২` |
| 178 | 859 | 2 typo fixes; `ascii_figure_suspect: L5` |
| 179 | 1779 | clean — Chapter 9's opening page (no running header, as usual for a chapter-opener) |
| **180** | 1272 | **`figure_labels_removed: 12`, `figure_values_lost: 17, 15, 8`** — see note below |

**On p175-177's `page_number_mismatch`**: checked the raw headers directly before writing this up — it's **not** a systematic offset shift (the 190/191/192-vs-170/171/172 gap looked like one at first glance) but 3 consecutive instances of this corpus's already-documented ৭/৯ digit confusion: `১৯০`/`১৯১`/`১৯২` vs the correct `১৭০`/`১৭১`/`১৭২` (single middle-digit misread each time, same pattern as earlier batches' ৭↔৯ findings). p178's own header (`১৭৩`) reads correctly, confirming the underlying page-number sequence itself never actually jumped.

**On p180's figure-label loss**: this page (উদাহরণ ১, Chapter 9's first worked example) has THREE small right-triangle sub-figures labelled (ক)/(খ)/(গ), each with its own set of axis/side labels — (ক)'s are the numeric side lengths **17, 15, 8** (needed to answer "চিহ্নিত করো" for that sub-figure), (খ)'s are variables p/q/r, (গ)'s are point labels E/F/G. The run-based remover correctly caught all of these as label clusters (plus an earlier P/N/O ×2 cluster higher up the page) and flagged the lost numeric values by name, exactly as designed — this is a real content loss on a question-critical sub-figure, not a formatting nit, flagged here for Claude (chat) to add back from the image.

## Cost

Batch 18: 20 Gemini calls (10 pages × primary+secondary, no escalation needed).
**Cumulative gemini-3.5-flash-lite spend (Step 4 total so far): $0.6868** (596,301 in / 203,157 out tokens) of the $7.00 stop.

## Task 6 — commit + push
