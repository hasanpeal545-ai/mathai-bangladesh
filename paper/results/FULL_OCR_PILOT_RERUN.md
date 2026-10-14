# Full OCR — Step 3b pilot re-run report

All 5 of Step 3b's fixes are implemented in `paper/scripts/full_gemini_ocr.py` and have been run for real on the full 30-page pilot set (the same pages as the original pilot). Nothing under `backend/data/ocr_raw`, `ocr_fixed`, `comparison`, `approved`, or Qdrant was touched — only `backend/data/ocr_gemini/` (new output) and `paper/check/` (digit_disagreements.csv, blocked_pages.csv, pilot/ images).

## 1. Prompt addition — implemented, mixed real-world effect (reported honestly)

Appended verbatim to the existing prompt, nothing else changed: *"Read Bangla digits (০১২৩৪৫৬৭৮৯) very carefully; do not confuse ৭ with ৯, ৪ with ৮, or ৩ with ৬. Ignore any text printed vertically in the page margin. Write fractions as a/b, not LaTeX."*

Checked directly against the 4 specific content errors `paper/check/ERRORS_LOG.csv` recorded from the original pilot:

| Page | Known error | Fixed by the new prompt? |
|---|---|---|
| `class_7_math_bn` p177 | question number ২৯→should be ২৭ | **Yes** — now reads `২৭।` correctly. |
| `class_9_General_math_bn` p29 | `\frac{p}{q}` LaTeX → should be `p/q` | **Yes** — now reads `{p/q : ...}` plain-text. |
| `class_6_math_bn` p156 | answer `৯০ : ২৩` → should be `৭০ : ২৩` | **No** — primary (temp 0) reading still says `৯০`, the exact ৭/৯ confusion the prompt explicitly warns against. See §2 — caught a different way. |
| `class_9_General_math_bn` p29 | `প্রতিটি` → should be `প্রত্যেকটি` | **No** — not expected to be fixed by this prompt addition; that's a word-choice/synonym substitution, a different error class than the digit/margin/fraction issues this prompt addition targets. |

**Headline: the prompt fix is real but not 100% reliable** — it fixed 2/2 of the issues it specifically targets that could be checked this way, but missed the clearest textbook case of the exact digit pair it names. This is why §2's independent double-reading check matters, not just the prompt.

The margin-text instruction ("ignore any text printed vertically in the page margin") appears to have worked very well on its own: **zero** margin-year tokens (২০২৩/২০২৪/২০২৫/২০২৬/2023-2026) were found in any of the 30 new raw outputs — the post-processing regex (§3) currently has nothing to clean up in this sample, though it stays in place as a safety net for the full corpus.

## 2. Bangla double-call + digit disagreement check — implemented, verified working, caught a real error

Every bn page now gets 2 independent Gemini calls (temp 0 → `page_N.txt`/`page_N.raw.txt`, temp 0.4 → `page_N.alt.txt`/`page_N.alt.raw.txt`), diffed for digit disagreements into `paper/check/digit_disagreements.csv`.

**A real bug was found and fixed first**: a naive line-by-line positional comparison (line *i* vs line *i*) was tried, and produced a cascade of false "disagreements" the moment the two readings wrapped text into even slightly different line counts anywhere on the page (the exact same failure mode already found and fixed in Day 3's `day3_diff_hints.py`). Fixed by aligning the two line lists with `difflib.SequenceMatcher` first and only comparing digit sequences within genuinely non-matching aligned blocks.

**Validated against the known `৯০`/`৭০` error from §1**: the secondary (temp 0.4) reading of `class_6_math_bn` page 156 independently got it right (`৭০ : ২৩`), while the primary (temp 0) reading kept the error (`৯০ : ২৩`) — and `digit_disagreements.csv` line 24 correctly flags exactly this line, showing both readings side by side. **The two-reading system catches the error the prompt fix alone missed** — this is the intended layered defense working as designed, not a coincidence.

Across all 30 pages: 95 flagged lines, concentrated in 10 of the 15 bn pages (5 bn pages had zero digit disagreements between their two readings). One real limitation found: pages with heavily tabular/visual layouts (long division, square-root algorithms — e.g. `class_7_math_bn` page 14, 26 flagged lines) produce noisy line-level detail, because the two temperature samples sometimes format the same 2-D calculation layout into different text-line structures that don't align cleanly even after the difflib fix. The check still correctly flags that *page* as needing careful attention; the per-line detail on such pages is just less precise. Worth knowing before Claude (chat) reviews that file.

## 3. Margin-year post-processing — implemented, verified correct, currently a dormant safety net

`strip_margin_year()` removes a standalone year-only line, or a trailing "10+ spaces + year" fragment at end of line, for ২০২৩/২০২৪/২০২৫/২০২৬ and 2023-2026. Unit-verified the regex logic directly; as noted in §1, none of the 30 pages' raw outputs actually contained this artifact under the new prompt, so the function currently has nothing to remove in this sample — kept in the pipeline for the full corpus since not every page is guaranteed to behave the same way.

## 4. RECITATION fallback to Tesseract — implemented, verified working for real

`class_9_Higher_math_en` page 28 (the generic set-builder-notation exercise page) **still blocks under the new prompt too** — confirming this is a genuine, prompt-independent recitation-filter behavior, not an artifact of the old prompt. The fallback triggered correctly: `page_28.txt` now starts with `[FALLBACK: TESSERACT — Gemini RECITATION block]` followed by the existing Tesseract text, and `paper/check/blocked_pages.csv` has the corresponding row. `class_6_math_en` page 15 (the other original-pilot block) did **not** block this time — RECITATION triggering is evidently sensitive to small prompt differences, not perfectly deterministic across prompt variants (it stayed deterministic *within* one fixed prompt, which is what mattered for the original pilot's retry-avoidance logic).

## 5. Full 30-page re-run + re-rendered images — done

All 30 original pilot pages reprocessed with `--force` under the new pipeline. Images re-rendered into `paper/check/pilot/<book>/page_N.png` (nested, 300 DPI). Note: `paper/check/pilot/` already contained a separate, flatter set of images (`<book>_page_N.png`, smaller files, timestamped 20:31 — before this re-run started) that appear to belong to the other Claude (chat) review session's own setup; left untouched, no naming collision with this run's nested `<book>/page_N.png` layout.

## ⚠️ Cost impact — the most important finding of this re-run, flagged prominently

**Output-token usage per call increased roughly 6-9x under the new prompt — on EVERY page type, not just Bangla ones.** Measured directly across all 45 real API calls in this re-run (median 4,758 output tokens/call, range 2,412-12,563) versus the original pilot's calls (roughly 300-1,000 visible/800-900 "real" output tokens per call). This happens on single-call English pages too (e.g. `class_8_math_en` page 196: 8,660 output tokens for one call) — so it is the **prompt addition itself** driving far more internal/"thinking" token usage, not merely the Bangla double-call policy. The double-call policy is a *second*, independent cost multiplier on top of that, affecting only the ~48% of pages that are Bangla (1,236 of 2,562 pages).

**Revised full-corpus (2,562-page) projection, using these real per-call averages:**
- Expected total calls: 1,236 bn pages × 2 + 1,326 en pages × 1 = **3,798 calls**
- Projected tokens: **≈4.65M input / ≈19.2M output**
- Projected cost at the same placeholder price as the original pilot report ($0.10/1M in, $0.40/1M out): **≈$8.15** — more than **7x** the original pilot's $1.16 estimate, and **over 2x the script's own $4 auto-stop threshold.**

This means: if Step 4 is approved as currently configured, the `full_gemini_ocr.py` script will almost certainly **hit its own $4 safety stop partway through the full run** and halt automatically (the safety mechanism doing exactly what it's supposed to) — it will need to be explicitly resumed (or the threshold raised) to continue past that point. Flagging this now, before "run all," rather than letting it be a surprise mid-run. The $4 threshold itself is unchanged in the script; this is reporting what will happen under it, not proposing to change it unilaterally.

As before, both the $1.16 and $8.15 numbers rest on a **placeholder price** (`gemini-3.6-flash` is newer than this assistant's training data) — please confirm the real billing rate from your Google AI Studio / Cloud billing page. If real output-token price is anything above the placeholder, the real cost is correspondingly higher than $8.15.

---

**Pilot re-run done — ask Claude (chat) to check it.**

Files for review: `paper/check/digit_disagreements.csv` (95 flagged lines across 10 bn pages), `paper/check/blocked_pages.csv` (1 page), `paper/check/pilot/<book>/page_N.png` (all 30 pages' fresh images), and the primary/alt/raw text files under `backend/data/ocr_gemini/<book>/`.
