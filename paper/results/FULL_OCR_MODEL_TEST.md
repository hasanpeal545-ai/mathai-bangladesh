# Full OCR — Step 3d: real prices + cheaper-model/thinking-level test

**Total real spend for this entire step: $0.0464** (the 10-call test below) + the free `models.list` and error-probing calls (zero token cost — confirmed 400 responses before any model call). Well under the task's $0.50 cap.

## Price fix (done first, in `paper/scripts/full_gemini_ocr.py`)

Replaced the placeholder `PRICE_PER_1K_INPUT_TOKENS`/`PRICE_PER_1K_OUTPUT_TOKENS` ($0.10/$0.40 per 1M) with Peal's confirmed real published rate for `gemini-3.6-flash`: **$1.50/1M input, $7.50/1M output** (thinking tokens billed as output).

**Recomputed both earlier pilot projections with the real price** (previously reported at the wrong placeholder rate):

| | Sample measured | Projected for all 2,562 pages |
|---|---|---|
| **Original pilot** (Step 3, old prompt, 1 call/page, 30 pages) | $0.24 | **$20.64** (was reported as $1.16 under the placeholder — **17.8x** too low) |
| **Step 3b re-run** (new prompt + bn double-call, 45 calls/30 pages) | $1.79 | **$151.06** (was reported as $8.15 under the placeholder — **18.5x** too low) |

This confirms the task's own "~15-19x" estimate almost exactly. **$151 for the full corpus under the Step 3b/3c pipeline is not viable** — this is the real reason this step exists.

Current real cumulative spend across every call this project has made so far (per `backend/data/ocr_gemini/RUN_LOG.csv`, now re-priced at the real rate): **$2.31** (98,712 input / 288,700 output tokens). Remaining credit per Peal: ~$8.40.

## Step 3d.1 — Available models (`paper/results/AVAILABLE_MODELS.md`)

Fetched via raw REST `GET /v1beta/models` (free, bypasses the outdated SDK entirely). 62 models total, 26 "flash"-like. Every Gemini-3-generation flash model inspected (`gemini-3.6-flash`, `gemini-3.5-flash-lite`, `gemini-flash-lite-latest`, `gemini-3.8-flash`) reports `"thinking": true` in its metadata, but the model-list response does **not** expose the thinking-control field's name or valid values — that had to be found empirically (next section), exactly as the task anticipated.

**Flash-Lite model chosen for this test: `gemini-3.5-flash-lite`** (the current specific, pinned Flash-Lite release in the same Gemini-3 generation as `gemini-3.6-flash`) — not the `gemini-flash-lite-latest` alias, which could silently point to a different model later and make this test non-reproducible.

### Thinking-control field discovery — found via the API's own error responses, not guessed

Per the task's explicit instruction ("do not guess field names — read the API error/response or the official docs"), found by deliberately sending invalid values in `generationConfig.thinkingConfig` via raw REST and reading the resulting 400 errors (each one free — rejected before reaching the model):
- `{"bogusField": 123}` → `"Unknown name \"bogusField\" at 'generation_config.thinking_config'"` — confirms `thinkingConfig` itself is valid.
- `{"thinkingLevel": "BOGUS_LEVEL"}` → `"Invalid value at '...thinking_config.thinking_level' (...ThinkingConfig.ThinkingLevel)"` — confirms `thinkingLevel` is a real enum field.
- `{"thinkingBudget": "not_a_number"}` → `"Invalid value at '...thinking_config.thinking_budget' (TYPE_INT32)"` — confirms `thinkingBudget` is also real (an int), but per Google's own docs (checked via WebFetch on `ai.google.dev/gemini-api/docs/generate-content/thinking`) **Gemini-3-generation models use `thinkingLevel` exclusively** — `thinkingBudget` is the older Gemini-2.5-era mechanism, kept only for backward compatibility and not meant to be combined with `thinkingLevel`.
- Confirmed valid enum values (from the docs, since the error message didn't enumerate them): **`minimal`, `low`, `medium`, `high`** — `minimal` is the literal lowest. Verified with one real, near-free call (`gemini-3.6-flash`, prompt "Say OK", `thinkingLevel: "minimal"`): **2 input / 1 output / 3 total tokens** — essentially zero hidden-thinking overhead, versus the thousands of hidden tokens measured per call in Steps 3b/3c when `thinkingConfig` wasn't set at all (i.e. the model's own default thinking level, evidently much higher than minimal).

Used **`thinkingLevel: "minimal"`** for both models in the test below, per the task's "set it to the lowest allowed value" instruction.

## Step 3d.2 — The 5-page / 2-setting test

One call per page per setting (no bn double-call), same current prompt (margin-ignore + plain-fraction, imported directly from `full_gemini_ocr.py` so it can't drift), temperature 0, via raw REST (`paper/scripts/model_cost_test.py`).

- **Setting A**: `gemini-3.6-flash`, `thinkingLevel: minimal`
- **Setting B**: `gemini-3.5-flash-lite`, `thinkingLevel: minimal`

| Page | Setting | in tok | out tok | candidates tok | cost |
|---|---|---|---|---|---|
| p30 | A | 1195 | 770 | 770 | $0.00757 |
| p36 | A | 1195 | 796 | 796 | $0.00776 |
| p44 | A | 1195 | 819 | 819 | $0.00793 |
| p156 | A | 1195 | 577 | 577 | $0.00612 |
| p14 | A | 1185 | 557 | 557 | $0.00596 |
| p30 | B | 1195 | 778 | 778 | $0.00230 |
| p36 | B | 1195 | 800 | 800 | $0.00236 |
| p44 | B | 1195 | 700 | 700 | $0.00211 |
| p156 | B | 1195 | 598 | 598 | $0.00185 |
| p14 | B | 1185 | 840 | 840 | $0.00246 |

**Key confirmation: `output_tokens == candidates_tokens` exactly on every single row.** In every prior test (Steps 3b/3c, no explicit `thinkingConfig`), `total_token_count` was always 2,000-12,000+ tokens *larger* than the visible candidate text — that gap is gone entirely at `thinkingLevel: minimal`. This is the real mechanism behind the cost difference, not a fluke of these 10 calls.

## Step 3d.3 — CER against ground truth (p30/p36/p44)

Computed with `paper/scripts/day5_cer.py`'s exact method (Levenshtein, whitespace removed), reused directly (not reimplemented) so the numbers are comparable to Day 5's.

| Page | Setting A (3.6-flash) | Setting B (3.5-flash-lite) |
|---|---|---|
| p30 | 0.22% | 0.51% |
| p36 | **35.59%** | **36.03%** |
| p44 | **38.14%** | 2.45% |
| **MEAN (micro)** | **21.45%** | **11.03%** |

**These numbers look alarming next to Day 5's 0.24% Gemini mean — investigated directly rather than reported at face value, and the cause is NOT digit/content errors:**

Both settings wrapped p36's set-notation-heavy content in **LaTeX** (`$...$` delimiters, `\cup`, `\cap`, `\setminus`, `\pm`, `\le`, `\therefore`, even a stray markdown `##` heading on setting A) — directly violating the prompt's explicit "Write fractions as a/b, not LaTeX" instruction. Setting A did the same thing on p44 (96 `$` + 88 `\` characters); setting B did not (0 of each on p44, hence its much lower 2.45% there). Character-counted directly: p36 has 90 `$` and 74 `\` characters in *both* settings' output — essentially identical LaTeX-wrapping behavior, strongly suggesting this specific page's heavy set-notation content reliably triggers it regardless of model.

**Honest conclusion: Day 5's 0.24% CER was measured under the model's *default* (non-minimal) thinking level. This test's elevated CER on p36 (both settings) and p44 (setting A) is a measured, real side-effect of `thinkingLevel: minimal` specifically — lower deliberation appears to let the model fall back to its natural LaTeX-formatting habit instead of reliably following the custom "no LaTeX" instruction, at least on pages dense with set-notation.** This is a genuine, newly-found accuracy/cost tradeoff, not a transcription-content problem — p30 (plain prose + simple set notation) stayed clean and accurate in both settings.

## Step 3d.4 — p156 / p14 digit checks

| Page | Check | Setting A | Setting B |
|---|---|---|---|
| p156 | `৭০ : ২৩` (correct) present | **Yes** | **Yes** |
| p156 | `৯০ : ২৩` (known-wrong) present | No | No |
| p14 | divisor `১০৪` (correct) present | **Yes** | **No** — reads `১০৮` instead (the exact known ৪→৮ confusion from the original Step 3b pilot, reproduced) |
| p14 | `৯.২৫৩০০০০০`-digit-sequence (example 3) correct | **Yes** (digits match; minor spacing difference only) | **Yes** (wrapped in a LaTeX `\begin{array}` table, but the digit sequence itself is correct) |

Both settings got p156 right this time. For p14, **setting A (full Flash) got the known divisor error right; setting B (Flash-Lite) reproduced it** — plus setting B wrapped p14's long-division layout in LaTeX tables too (visible in its raw output). So the cheaper model is not a clean win on accuracy here, even though it's far cheaper.

## Step 3d.5 — Cost projections (real prices, `thinkingLevel: minimal`)

Using this test's actual measured per-call averages (A: 1193 in / 703.8 out; B: 1193 in / 743.2 out tokens/call):

| Scope | Setting | Single call/page | With Bangla double-call |
|---|---|---|---|
| **Full corpus** (2,562 pages: 1,236 bn + 1,326 en) | A (3.6-flash) | $18.11 | $26.84 |
| | B (3.5-flash-lite) | **$5.68** | **$8.42** |
| **Class 9-10 only** (1,448 pages: 704 bn + 744 en) | A (3.6-flash) | $10.23 | $15.21 |
| | B (3.5-flash-lite) | **$3.21** | **$4.77** |

Compare to the Step 3b/3c pipeline's **$151.06** full-corpus projection (§ price fix above, default thinking, no minimal setting): switching to `thinkingLevel: minimal` cuts the full-corpus cost by roughly **5.6x** (gemini-3.6-flash) to **18x** (gemini-3.5-flash-lite), and dropping the Bangla double-call on top of that saves a further ~30-33%.

Flash-Lite's $0.30/$2.50-per-1M price used above is **third-party-sourced** (aggregator sites, cross-checked across several), **not** read directly off an official Google billing page the way the Flash price was (Peal confirmed that one from the AI Studio Spend page directly) — flagging this the same way the original placeholder price was flagged, so it isn't mistaken for an equally-confirmed number.

## Bottom line for Peal

- `thinkingLevel: minimal` genuinely works and is the real lever Step 3c was looking for (Step 3c's prompt-trim attempt found nothing; this does) — it removes the entire hidden-thinking-token cost (confirmed: `output_tokens == candidates_tokens` on all 10 calls), cutting projected full-corpus cost from $151 down to $5.68-$26.84 depending on model/double-call choice.
- **The tradeoff found**: at `minimal`, the model is less reliable about following the "no LaTeX" instruction on set-notation-dense pages (2 of 3 ground-truth pages affected), and the cheaper Flash-Lite model reproduced one of the two known digit-confusion errors that full Flash avoided this time.
- This step only tested and reported, per FULL_OCR.md's scope — it did not change `full_gemini_ocr.py`'s actual pipeline to use `thinkingLevel` (the installed SDK can't express it at all; that would require either switching the whole pipeline to raw REST calls, or a different mechanism) or decide which model/setting to adopt for Step 4. That decision, and whether the LaTeX-formatting issue needs its own fix first, is Peal's call.

## Files produced
```
paper/scripts/list_models.py
paper/scripts/model_cost_test.py
paper/results/AVAILABLE_MODELS.md
paper/results/model_test_log.csv
paper/results/model_test_outputs/A_gemini-3.6-flash_minimal/*.txt  (5 pages)
paper/results/model_test_outputs/B_gemini-3.5-flash-lite_minimal/*.txt  (5 pages)
paper/results/FULL_OCR_MODEL_TEST.md   (this file)
```
Also modified: `paper/scripts/full_gemini_ocr.py` — real price constants only (no pipeline logic changed).

---

## Step 3e.4 addendum (2026-10-07) — re-scored CER after the new LaTeX-to-plain post-processing

**No new API calls** — this re-scores the exact outputs already saved above (§3d.2) by running them through `latex_to_plain()` (new in Step 3e.3, see `paper/results/FULL_OCR_FINAL_SETTINGS.md` for the full spec) and recomputing CER against ground truth with the unchanged `day5_cer.py` method.

| Page | Setting A (3.6-flash) before → after | Setting B (3.5-flash-lite, **the chosen final model**) before → after |
|---|---|---|
| p30 | 0.22% → 0.22% (no change — no LaTeX on this page) | 0.51% → 0.51% (no change) |
| p36 | 35.59% → **6.77%** | 36.03% → **7.21%** |
| p44 | 38.14% → **8.38%** | 2.45% → 2.45% (no change — setting B never used LaTeX on this page) |
| **MEAN (micro)** | **21.45% → 4.49%** | **11.03% → 2.96%** |

**The post-processing step works as intended**: mean CER for the chosen model (setting B) drops from 11.03% to **2.96%** — a 73% relative reduction — and setting A drops 79% (21.45% → 4.49%). Both are now much closer to Day 5's 0.24% default-thinking baseline, though not equal to it.

**What's left in the residual gap (checked directly on setting B's p36, the worst remaining page):** a character-level diff against ground truth after post-processing shows only a handful of distinct causes, all explainable:
- `\text{...}` and `\setminus` — LaTeX commands Step 3e's list does **not** cover (only the symbols explicitly named were mapped; `\text{}` wrapping and `\setminus` were deliberately left as a known gap rather than silently expanding scope beyond what was specified).
- `−` (Unicode minus, U+2212) transcribed as plain `-` (ASCII hyphen), and `′` (Unicode prime, U+2032, used for set-complement notation like A′) transcribed as `'` (ASCII apostrophe) — not LaTeX, a separate minor Unicode-fidelity issue untouched by this post-processing pass.
- **One genuinely interesting non-error**: ground truth contains `২০২৬` (the page's own printed margin year) where the processed output has nothing — because `post_process()` runs Step 3b.3's margin-year stripping *before* `latex_to_plain()`, and that stripping is deliberately designed to remove margin-year tokens from the pipeline's output (they were an OCR-reliability problem in Tesseract/earlier Gemini passes). Peal's hand-made ground truth faithfully transcribes the physical page, margin year included — so this specific diff is an inherent, known side effect of a Step-3b design decision intersecting with a Step-5-style CER check, not a new bug. Worth knowing if ground-truth-based CER is used again on margin-year-bearing pages.

This addendum does not change any of the cost projections in §3d.5 above (post-processing is free, local, and doesn't touch token usage).
