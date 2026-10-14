# Full OCR — Pilot report (30 pages, paid tier)

**Precondition check: paid tier IS active.** All 30 pilot calls went through with no free-tier quota errors (the free tier's 20/day limit that blocked Day 2/3 work is no longer the constraint here) — so no STOP was needed on that front.

## Two real bugs found and fixed while running this pilot (not pre-existing — found live)

1. **SDK crash masking the real reason for an empty response.** 2 of the first 30 calls raised `AttributeError: Unknown field for Candidate: finish_message` on all 3 attempts identically. Root cause: the installed `google-generativeai==0.8.2` SDK's own `.text` convenience property, when a candidate has zero content parts, tries to build a diagnostic message by reading `candidate.finish_message` — a field the API now returns that this SDK version's compiled proto type doesn't recognize, so even *constructing the error message* crashes, hiding the real finish reason. Fixed by rewriting `call_gemini_once()` in `paper/scripts/full_gemini_ocr.py` to read `candidate.content.parts` directly and never touch `.text`/`.finish_message`. Once fixed, the real reason was visible: both pages had `finish_reason = RECITATION` (Gemini's copyright/recitation filter), not a bug in the request. Retrying a RECITATION block 3x at temperature 0 is pointless (deterministic, identical outcome every time) and was silently burning 3x the tokens for a guaranteed failure — the script now stops after 1 attempt for this specific finish reason and logs it as `BLOCKED (RECITATION)` instead of retrying.
2. **Hidden "thinking" tokens undercounting real cost.** Measured directly: a normal successful page had `prompt_token_count=1176`, `candidates_token_count=518` (the visible transcription), but `total_token_count=3234` — ~1540 tokens unaccounted for by either number. `gemini-3.6-flash` evidently spends a large number of internal/reasoning tokens per call that aren't reflected in `candidates_token_count` at all. The original script only counted `candidates_token_count` as "output tokens," which would have undercounted real output-token cost by roughly 2-3x. Fixed: `output_tokens` is now `total_token_count - prompt_token_count` (captures the full real cost, visible or not). This also fixed bug #1's silent 0-token logging for the blocked pages — they turned out to cost *more* tokens than average successful pages (2807 and 3226 "output" tokens — all spent on internal reasoning before being blocked, producing no usable text).

## Pilot pages (3 per book: near-start, middle, heaviest-math-by-Tesseract-density) — 30 pages across the 10 distinct books, not ~20-25

DAY2.md's own estimate ("about 20-25 pages total") assumed roughly 7-8 distinct books; Step 1 found there are genuinely **10** distinct books after deduping the 4 `class_10_*.pdf` copies (see `FULL_OCR_INVENTORY.md`), so "3 pages × 10 books" is 30, not 20-25. Followed the explicit "3 pages from each distinct book" instruction literally rather than shrinking the per-book sample to hit the rough total — flagging the discrepancy here rather than silently picking one.

| Book | Lang | Page | Role | Status | In tok | Out tok | Chars |
|---|---|---|---|---|---|---|---|
| class_6_math_bn | bn | 13 | start | OK | 1176 | 526 | 1662 |
| class_6_math_bn | bn | 80 | middle | OK | 1176 | 346 | 967 |
| class_6_math_bn | bn | 156 | heavy-math | OK | 1176 | 611 | 1295 |
| class_6_math_en | en | 15 | start | **BLOCKED (RECITATION)** | 1176 | 2807 | 0 |
| class_6_math_en | en | 91 | middle | OK | 1176 | 436 | 1018 |
| class_6_math_en | en | 178 | heavy-math | OK | 1176 | 910 | 1316 |
| class_7_math_bn | bn | 14 | start | OK | 1166 | 614 | 2410 |
| class_7_math_bn | bn | 90 | middle | OK | 1166 | 683 | 1479 |
| class_7_math_bn | bn | 177 | heavy-math | OK | 1166 | 1285 | 2113 |
| class_7_math_en | en | 16 | start | OK | 1176 | 418 | 1506 |
| class_7_math_en | en | 99 | middle | OK | 1176 | 491 | 1494 |
| class_7_math_en | en | 195 | heavy-math | OK | 1176 | 1460 | 1845 |
| class_8_math_bn | bn | 15 | start | OK | 1166 | 435 | 1475 |
| class_8_math_bn | bn | 95 | middle | OK | 1166 | 632 | 1576 |
| class_8_math_bn | bn | 183 | heavy-math | OK | 1166 | 873 | 1571 |
| class_8_math_en | en | 16 | start | OK | 1176 | 637 | 1996 |
| class_8_math_en | en | 101 | middle | OK | 1176 | 680 | 1210 |
| class_8_math_en | en | 196 | heavy-math | OK | 1176 | 824 | 1246 |
| class_9_General_math_bn | bn | 29 | start | OK | 1176 | 642 | 1641 |
| class_9_General_math_bn | bn | 181 | middle | OK | 1176 | 440 | 1932 |
| class_9_General_math_bn | bn | 268 | heavy-math | OK | 1176 | 809 | 1487 |
| class_9_General_math_en | en | 31 | start | OK | 1176 | 723 | 2099 |
| class_9_General_math_en | en | 195 | middle | OK | 1176 | 364 | 1706 |
| class_9_General_math_en | en | 383 | heavy-math | OK | 1176 | 956 | 1958 |
| class_9_Hiher_math_bn | bn | 27 | start | OK | 1176 | 666 | 1908 |
| class_9_Hiher_math_bn | bn | 171 | middle | OK | 1176 | 499 | 1665 |
| class_9_Hiher_math_bn | bn | 233 | heavy-math | OK | 1176 | 799 | 1475 |
| class_9_Higher_math_en | en | 28 | start | **BLOCKED (RECITATION)** | 1176 | 3226 | 0 |
| class_9_Higher_math_en | en | 177 | middle | OK | 1176 | 604 | 2065 |
| class_9_Higher_math_en | en | 246 | heavy-math | OK | 1176 | 778 | 1534 |

Full machine-readable log: `backend/data/ocr_gemini/RUN_LOG.csv`.

## Token usage and cost (ALL numbers below use a placeholder price — see caveat)

- Pilot totals (30 distinct pages, after dedup): **35,220 input tokens / 25,174 output tokens** (output = `total_token_count - prompt_token_count`, i.e. visible text + hidden reasoning tokens — see bug #2 above).
- Pilot cost at the placeholder price ($0.10/1M input, $0.40/1M output): **$0.0136**.
- **Projected cost for all 2,562 pages** (scaling the pilot's actual per-page average: 1174 in / 839 out tokens/page): **≈3.01M input tokens, ≈2.15M output tokens, ≈$1.16 total**.

**⚠️ Price caveat — this is a placeholder, not a confirmed real rate.** `gemini-3.6-flash` is newer than this assistant's training data, so its real per-token price is not something that could be looked up with confidence; `PRICE_PER_1K_INPUT_TOKENS`/`PRICE_PER_1K_OUTPUT_TOKENS` in `full_gemini_ocr.py` are a reasonable-guess placeholder based on older Gemini Flash-tier pricing patterns, clearly marked as such in the code. **Please confirm the actual billing rate from your Google AI Studio / Cloud billing page before Step 4's full run** — the $1.16 projection (and the script's own $4 auto-stop) are only as accurate as that constant. If the real rate turns out to be, say, 3x higher, the full run would still land under $4 (~$3.48); at 4x+ it could exceed the stop threshold before the script catches it, since the stop check itself uses the same placeholder.

## Pages whose output looks wrong

**2 pages genuinely failed** (both English-book pages, both blocked by Gemini's RECITATION/copyright filter, both standard/generic math content — not obviously unique copyrighted phrasing):
- `class_6_math_en` page 15 (divisibility-by-5 and divisibility-by-3 rules — completely standard textbook content, present near-verbatim in many textbooks worldwide).
- `class_9_Higher_math_en` page 28 (generic set-builder-notation practice exercises).

Both are plausibly **over-triggers** of the recitation filter on generic, widely-repeated educational phrasing rather than genuinely unique NCTB copyrighted text — but there's no way to confirm that from the API's response, it just returns the enum. No output was produced for either; no `.txt` file was written (resumability will retry these automatically on a future invocation, though note it will spend the same ~2800-3200 tokens again if it blocks again — see "Open question for Peal" below).

**0 pages had a genuine quality problem** among the 28 that succeeded. One check I ran flagged **3 false positives** worth mentioning so Step 5's real quality-check script doesn't repeat the same mistake: `class_7_math_bn` page 177, `class_8_math_bn` page 95, and `class_8_math_bn` page 183 all have a very LOW fraction of Bangla-script letters (4-24%) among their alphabetic characters — a naive "wrong script" check would flag all three as "English page smuggled into a Bangla book." Reading them directly: all three are **answer-key / worked-algebra pages** (অনুশীলনী ৪.৩ answers, polynomial-division worked examples) where the overwhelming majority of *characters* are legitimately single-letter Latin math variables (`a, b, c, x, y, z`) and digits, with only a handful of actual Bangla words (`নির্ণেয় ভাগফল`, `গণিত`, `অনুশীলনী`). These are correctly in Bangla; the heuristic is just too naive for a math corpus. **Lesson carried into Step 5**: the real `ocr_quality_check.py` needs to distinguish isolated single-letter math variables from genuine multi-letter English *words* when checking for "wrong script," not just raw character-fraction.

No empty/cut-off/commentary/markdown-fence issues found among the 28 successes (spot-checked character-ratio-vs-Tesseract and read several pages directly, including the 3 false-positive-flagged ones above).

## Open question for Peal (not a blocker, just worth a decision before Step 4)

Should a RECITATION-blocked page be retried verbatim on every future resume (same prompt/image, same likely outcome, ~3000 tokens spent for nothing each time), or would you like a different handling for pages that block — e.g. a modified prompt for just that page, or accepting a permanent gap and noting it in the final summary? Not fixed on my own judgment since it changes behavior beyond what FULL_OCR.md specifies; flagging for your call.

---

**Pilot done. Check 2-3 pilot pages against the images and say "run all" to continue.**

Suggested pages to check first: `class_6_math_bn` page 13 (plain Bangla prose, high confidence), `class_8_math_bn` page 95 (the answer-key false-positive case above, worth confirming it's genuinely fine), and `paper/check/_pilot_tmp/class_6_math_en/page_15.png` if you want to see what a RECITATION-blocked page actually looks like (the image renders fine — rendering happens before the Gemini call — it's only the transcription that was refused).

(Note: `paper/check/ERRORS_LOG.csv` and `paper/check/PAGES_CHECKED.csv` already exist in `paper/check/` from outside this task — left untouched, not generated by anything here.)
