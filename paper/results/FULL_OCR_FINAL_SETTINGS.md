# Full OCR — Step 3e: FINAL settings (decided 2026-10-07, Peal + Claude chat)

No new API calls were made for this step (per FULL_OCR.md Step 3e's own heading: "No more API tests") — everything here is either a code/config change or a free re-score of data already saved in Step 3d.

## 1. Model and call mechanism — FINAL

- **Model**: `gemini-3.5-flash-lite`
- **Call mechanism**: raw REST (`requests`, directly against `generativelanguage.googleapis.com/v1beta`), not the `google-generativeai` SDK. The SDK (0.8.2, in `backend/venv`, left untouched) cannot express `thinkingConfig` at all — confirmed in Step 3d by inspecting its compiled proto types directly, not just failing to find a kwarg — and separately has a real bug (found in Step 3b) where its own `.text` convenience property crashes on an empty candidate. REST sidesteps both.
- **thinkingConfig.thinkingLevel**: `"minimal"` — the literal lowest of `minimal/low/medium/high` (confirmed via the API's own error messages in Step 3d, cross-checked against `ai.google.dev/gemini-api/docs/generate-content/thinking`). This is what actually removes the multi-thousand-hidden-token overhead every call had before Step 3d (confirmed: `output_tokens == candidates_tokens` on 10/10 Step 3d test calls).
- **Temperature**: 0 (primary), 0.4 (Bangla secondary/alt reading) — unchanged from Step 3b.
- **Prompt**: unchanged since Step 3c — base Day 2 prompt + "ignore vertical margin text" + "fractions as a/b, not LaTeX". The Step 3b digit-care sentence stays removed (Step 3c found it unreliable and likely a cost driver; the double-reading mechanism is what actually catches digit errors).

All implemented in `paper/scripts/full_gemini_ocr.py` — `GEMINI_MODEL`, `THINKING_LEVEL` constants; `call_gemini_once()` rewritten for REST.

## 2. Kept unchanged from Step 3b

- Bangla double-call (temp 0 + temp 0.4) with `paper/check/digit_disagreements.csv` (now difflib-aligned, not positional — see `FULL_OCR_PILOT_RERUN.md` for why positional comparison was discarded).
- Margin-year stripping (`strip_margin_year()`).
- RECITATION fallback to Tesseract text with the `[FALLBACK: TESSERACT — Gemini RECITATION block]` marker line + `paper/check/blocked_pages.csv`.
- `page_N.raw.txt` / `page_N.alt.raw.txt` copies of the unprocessed API text.

## 3. NEW — LaTeX-to-plain post-processing (free, local, no API cost)

`latex_to_plain()`, applied after margin-year stripping (combined as `post_process()`), handles exactly what Step 3e specified — no more, no less:

| Pattern | Handling |
|---|---|
| `$...$`, `$$...$$` | Delimiters stripped, content kept |
| `\begin{array}{...}` / `\end{array}`, `\cline{...}` | Stripped (pure tabular scaffolding, treated as part of "strip the array environment") |
| `\cup \cap \in \notin \subset \subseteq \emptyset \varnothing \therefore \times \div \le \ge \neq \pm` | Mapped to `∪ ∩ ∈ ∉ ⊂ ⊆ ∅ ∅ ∴ × ÷ ≤ ≥ ≠ ±` |
| `\{` / `\}` | Unescaped to `{` / `}` |
| `\frac{a}{b}` | → `a/b` (non-nested case; a `\frac` nested inside another `\frac`'s argument only has its outer layer converted) |
| `^{n}` / `^2` (digits 0-9 and `n` only) | → superscript Unicode (`⁰¹²³⁴⁵⁶⁷⁸⁹ⁿ`) — "where possible" per the task's own wording; any other character after `^` is left alone rather than guessed at |

**Deliberately NOT handled** (not in Step 3e's list — flagged rather than silently added or silently left as an unexplained gap): `\text{...}` wrapping, `\overline{...}`, bare array-internal `&`/`\\` separators. These do still appear in some post-processed output (confirmed on the re-scored p36, see `FULL_OCR_MODEL_TEST.md`'s addendum).

**Measured effect** (re-scoring Step 3d's already-saved outputs, no new API calls): mean CER for the chosen model (`gemini-3.5-flash-lite`) on the 3 ground-truth pages drops from **11.03% → 2.96%** (73% relative reduction). Full before/after table and residual-error analysis in `paper/results/FULL_OCR_MODEL_TEST.md`'s Step 3e.4 addendum.

## 4. CER re-score

See `paper/results/FULL_OCR_MODEL_TEST.md` (Step 3e.4 addendum, appended, not a separate file — per the task's explicit instruction to add this to that existing file).

## 5. Book order for Step 4 — FINAL

```
1. class_9_General_math_bn
2. class_9_General_math_en
3. class_9_Hiher_math_bn     (sic -- matches the existing filename/folder typo)
4. class_9_Higher_math_en
5. class_8_math_bn
6. class_8_math_en
7. class_7_math_bn
8. class_7_math_en
9. class_6_math_bn
10. class_6_math_en
```
Implemented as `BOOK_ORDER` in `full_gemini_ocr.py`; `load_books()` now returns books in this order (default sequential/`--sample` iteration follows it — no longer `curriculum.json`'s own 6/7/8/9General/9Higher order).

## 6. Cost stop — FINAL

- **Stop threshold: $7.00** (was $4.00), tracked via `read_prior_cost_usd()` — **now filtered to only `RUN_LOG.csv` rows where `model == gemini-3.5-flash-lite`**, deliberately excluding the Steps 2-3d rows made under `gemini-3.6-flash` at its own, different, higher real price. Mixing the two would misrepresent what "$7.00 total spend for Step 4" means once Step 4 only ever calls the new model — this was a real correctness fix made while implementing the stop, not just a literal placeholder swap.
- **Price, verified OFFICIAL** (not third-party, unlike the same number used provisionally in Step 3d): checked directly on `ai.google.dev/gemini-api/docs/pricing` — **$0.30/1M input tokens, $2.50/1M output tokens (thinking tokens included in the output price)** for `gemini-3.5-flash-lite`. Matches the task's stated numbers exactly.
- **Expected outcome, per the task's own framing**: Class 9-10 books (1,448 pages) ≈ $4.8 (Step 3d's test measured $3.21-$4.77 depending on single-vs-double-call mix for this exact model), all 2,562 pages ≈ $8.4, both using the model's own measured per-call averages — so the $7.00 stop is expected to land **around the class 7/6 boundary**, which the task says is intentional, not a bug to "fix" by raising the threshold further.

## Current real cumulative spend (all models, for context)

Per `backend/data/ocr_gemini/RUN_LOG.csv`: **$2.31** so far under `gemini-3.6-flash` (Steps 2-3d) + **$0.0464** under the model-comparison test (also priced at its own real rate in Step 3d's report) = **~$2.36** total real spend to date. None of this counts against the new $7.00 Step-4 stop (§6 above) since that's filtered to `gemini-3.5-flash-lite` rows only, and Step 4 hasn't started yet (0 real `gemini-3.5-flash-lite` production rows exist in RUN_LOG.csv — the Step 3d/this-step test calls were logged separately, to `paper/results/model_test_log.csv`, not `RUN_LOG.csv`, since they were a one-off comparison test, not the main pipeline).

## Files produced / modified
```
paper/results/FULL_OCR_FINAL_SETTINGS.md   (this file)
paper/results/FULL_OCR_MODEL_TEST.md       (appended: Step 3e.4 CER re-score addendum)
```
Modified: `paper/scripts/full_gemini_ocr.py` — model/REST migration, thinkingLevel, LaTeX post-processing, BOOK_ORDER, real flash-lite price, $7 stop filtered by model. No change to `backend/venv` or anything under `backend/data/{ocr_raw,ocr_fixed,comparison,approved}`.

---

**Final settings ready — ask Claude (chat) to approve run all.**
