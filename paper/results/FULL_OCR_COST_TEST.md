# Full OCR — Step 3c cost-cutting test

Goal per `paper/tasks/FULL_OCR.md`: try to reduce the per-call token cost found in `FULL_OCR_PILOT_RERUN.md` (~6-9x higher output tokens under the Step 3b prompt, pushing the full-corpus projection to ~$8.15, over 2x the script's own $4 stop) before approving Step 4.

## 1. Prompt trim — done

Removed only this sentence from `PROMPT` in `paper/scripts/full_gemini_ocr.py`: *"Read Bangla digits (০১২৩৪৫৬৭৮৯) very carefully; do not confuse ৭ with ৯, ৪ with ৮, or ৩ with ৬."*

Kept, unchanged: *"Ignore any text printed vertically in the page margin. Write fractions as a/b, not LaTeX."* — plus the entire original Day 2 base prompt.

## 2. Bangla double-call, margin-year stripping, RECITATION fallback — unchanged

All three mechanisms from Step 3b are untouched in the code, per the instruction to keep them exactly as they are.

## 3. Thinking-budget / thinking-level setting — not supported by this SDK, confirmed by direct inspection

Checked whether the installed client library exposes any way to cap `gemini-3.6-flash`'s internal reasoning:
- `google.generativeai.types.generation_types.GenerationConfig.__init__`'s full parameter list: `candidate_count, stop_sequences, max_output_tokens, temperature, top_p, top_k, seed, response_mime_type, response_schema, presence_penalty, frequency_penalty, response_logprobs, logprobs`. No thinking-related parameter.
- Checked the underlying compiled protobuf type directly (`google.ai.generativelanguage_v1beta.types.generative_service.GenerationConfig.meta.fields.keys()`), in case the Python wrapper just doesn't expose a field the raw proto has: same list, no `thinking_config`/`thinking_budget`/anything similar.
- Confirmed by trying it directly: `GenerationConfig(temperature=0, thinking_budget=0)` → `TypeError: unexpected keyword argument 'thinking_budget'`; same for `thinking_config={...}`.

**Conclusion: not supported by the installed `google-generativeai==0.8.2` SDK for this API version at all** — the field doesn't exist anywhere in this client's compiled types, not just unavailable via a documented kwarg. Per the task's own instruction, this step is skipped. (A newer SDK release or a raw-REST call against a newer API version might expose this — not attempted, since upgrading a dependency is outside what this task asked for and the project's own convention is not to add/upgrade dependencies without asking Peal first.)

## 4. Test on the 4 named pages — done, result: no clear cost reduction

Re-ran exactly `class_6_math_bn:156`, `class_7_math_bn:14`, `class_8_math_en:196`, `class_9_General_math_bn:29` (via a new `--pages book:page,...` option added to the script for this precise targeting — `--sample` would have pulled 3 pages/book, 12 total, more than the "4 pages only" the task asked for) with `--force` under the trimmed prompt, and compared against each page's Step 3b (pre-trim) RUN_LOG numbers.

| Page | Call | Before (out tok) | After (out tok) | Change |
|---|---|---|---|---|
| class_6_math_bn p156 | primary | 4,741 | 3,564 | −24.8% |
| class_6_math_bn p156 | secondary | 5,557 | 5,111 | −8.0% |
| class_7_math_bn p14 | primary | 2,714 | 4,602 | **+69.6%** |
| class_7_math_bn p14 | secondary | 2,770 | 7,613 | **+174.8%** |
| class_8_math_en p196 | primary (only call) | 8,660 | 6,405 | −26.0% |
| class_9_General_math_bn p29 | primary | 5,258 | 4,384 | −16.6% |
| class_9_General_math_bn p29 | secondary | 4,707 | 4,241 | −9.9% |
| **TOTAL (7 calls)** | | **34,407** | **35,920** | **+4.4%** |

**Honest result: removing the digit-care sentence did NOT reduce cost.** 5 of 7 calls got cheaper (−8% to −26%), but `class_7_math_bn` page 14 — the page with the dense long-division/square-root tabular layout already flagged in `FULL_OCR_PILOT_RERUN.md` as hard to align — got dramatically *more* expensive (+70% to +175%), swamping the other pages' savings and landing the 7-call total essentially flat (+4.4%, well within normal call-to-call variance for this model). **This strongly suggests the heavy hidden-"thinking"-token usage is not primarily driven by that one sentence** — it looks structural to this model/task combination (dense, exact-transcription work on math-heavy pages), not something a small prompt edit fixes. Combined with §3's finding that there's no SDK-level lever to cap it either, **neither of Step 3c's two proposed cost-cutting mechanisms produced a measurable reduction in this test.**

**p156 / p14 digit disagreements: still flagged, confirmed.** Recomputed directly from the current (post-trim) `page_N.txt`/`page_N.alt.txt` files: `class_6_math_bn` page 156 → **11** digit-disagreement lines; `class_7_math_bn` page 14 → **23** digit-disagreement lines. Both non-zero, confirming — as the task's own framing predicted ("the double reading is what actually catches digit errors") — that the double-call-and-diff mechanism keeps working regardless of this specific prompt wording change, since it doesn't depend on the removed sentence at all.

## Bottom line for Peal

The ~$8.15 full-corpus cost projection from `FULL_OCR_PILOT_RERUN.md` **does not change** based on this test — the one lever tried (prompt trim) was cost-neutral on this 4-page/7-call sample, and the other lever (thinking budget) isn't available in this SDK. The $4 auto-stop will still very likely trigger partway through Step 4 if run as currently configured. This is reported plainly rather than silently declared "fixed" — no cost-reduction mechanism from Step 3c actually worked, measured honestly rather than assumed.
