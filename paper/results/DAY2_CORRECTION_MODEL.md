# Day 2 / Task C — which model did the Chapter 2 OCR correction?

## What was searched
- `grep -ri "improvement_score|changes_count|ocr_fixed"` over the whole repo (working tree, not just git-tracked files).
- `git log --all --stat -- backend/data/comparison` and `git log --all -- backend/data/ocr_fixed` (and the same for `page_15.json`'s pattern).
- `backend/.gitignore` — confirms `**/data/ocr_raw/`, `**/data/ocr_fixed/`, `**/data/comparison/`, `**/data/approved/`, `**/data/pdfs/` are all gitignored, i.e. these data files were **never committed to git**.
- `git log --all --oneline --format="%h %ad %s" --date=iso` — full commit list with dates.
- File mtimes of every file in `backend/data/comparison/` and `backend/data/ocr_fixed/`.
- Every top-level backend script (`run_full_ocr.py`, `run_chunking.py`, `run_verification.py`, `extract_toc.py`) and `backend/ingestion/pdf_extractor.py`, `backend/main.py`.
- `backend/__pycache__/` and `backend/ingestion/__pycache__/` (stale compiled bytecode can sometimes outlive a deleted source file).
- `backend/*.log` for any mention of the correction step.
- The contents of `backend/data/comparison/bn_page_30.json` itself, for a model-name field.

## What was found — confirmed

**The correction code** is `fix_math_notation()` in [backend/ingestion/pdf_extractor.py:168-174](../../backend/ingestion/pdf_extractor.py#L168-L174). It calls the **Groq** API (not Gemini):

```python
def fix_math_notation(raw_text: str) -> str:
    completion = _groq_client.chat.completions.create(
        model=settings.groq_model,
        messages=[{"role": "user", "content": _MATH_FIX_PROMPT + raw_text}],
        max_tokens=3000,
    )
    return completion.choices[0].message.content.strip()
```

**The exact prompt** (`_MATH_FIX_PROMPT`, same file, lines 34-42):

```
তুমি Bangladesh SSC Math expert। এই OCR text এ শুধু math notation ঠিক করো। যেমন:
x2 → x²
l → 1 (যদি সংখ্যা হয়)
1/2 → ½
sqrt → √
... → ∴
শুধু corrected text দাও। অন্য কিছু লিখবে না।

<raw OCR text appended here>
```

**The model name** is not hardcoded — it's read from `settings.groq_model` (`backend/config.py`) at call time. That setting's value has changed over the project's life:

| Commit | Date | `groq_model` value |
|---|---|---|
| `d6a7981` "Initial commit" | 2026-09-07 | `llama-3.3-70b-versatile` |
| `746e220` "RAG wired... Model configs updated" | 2026-09-08 | `qwen/qwen3.8-27b` |
| current (`HEAD`) | — | `qwen/qwen3.8-27b` |

`backend/.env` has no `GROQ_MODEL` override (checked: the `.env` file contains no model-name keys at all), so the pydantic-settings default in `config.py` was always the effective value.

**Date of the actual Chapter 2 batch run**: the 45 real `bn_page_*.json` / `en_page_*.json` files in `backend/data/comparison/` all have filesystem mtimes of **2026-08-10, between 17:16:24 and ~17:21:18** (e.g. `bn_page_26.json` → 17:16:24, `en_page_49.json` → 17:21:18). `page_15.json` (the stray test file CLAUDE.md and the README both call out separately) has an earlier mtime, **13:24:11 the same day** — consistent with it being the isolated single-page admin test described in CLAUDE.md ("Test: page 15 of `class_9_General_math_bn.pdf`"), run before the full Chapter 2 batch.

Since **2026-08-10 is a full month before the repo's first git commit (2026-09-07)**, and `config.py`'s `groq_model` default at that first commit was still `llama-3.3-70b-versatile` (only changed on 2026-09-08 per the commit above), and CLAUDE.md's own "Important Decisions" log records `llama-3.3-70b-versatile` as the confirmed production Groq model from early in the project (well before 2026-08-10) through to the 2026-09-08 blocker that forced the swap — **the model used for the Chapter 2 OCR correction run was almost certainly `llama-3.3-70b-versatile`.**

This is an inference from timeline + config defaults, not a value read directly out of the data — see the caveat below.

## What could NOT be found — stated plainly, not guessed

1. **No field in the comparison JSON files records which model produced them.** `bn_page_30.json`'s keys are exactly `page, language, chapter, raw, fixed, changes_count, changes, improvement_score` — no model name, no timestamp, no prompt text stored.
2. **The actual script that ran the 45-file Chapter 2 batch no longer exists anywhere in this repo** (git history or working tree):
   - It is not `backend/ingestion/pdf_extractor.py`'s own `process_page_with_llm_fix()` → `save_page_outputs()` path — that function writes output as `page_{page_number}.json` (no `bn_`/`en_` prefix, see line 218) and its output dict has **no `"language"` key** — it only matches the one stray `page_15.json` test file, not the 45 real files (which do have a `"language"` key and `bn_`/`en_`-prefixed names).
   - `grep` across every `.py` file in the repo for an f-string pattern like `{lang}_page_` or `f"bn_`/`f"en_` found nothing except the two Day 2 scripts written today.
   - None of the other batch scripts (`run_full_ocr.py` = Tesseract-only STEP 3, `run_chunking.py` = STEP 4 chunking, `run_verification.py` = Gemini double-verification, `extract_toc.py` = STEP 2 TOC parsing) touch Groq, `fix_math_notation`, or `comparison/`.
   - The stale `.pyc` in `backend/ingestion/__pycache__/pdf_extractor.cpython-313.pyc` is timestamped 2026-08-10 13:23:42 — just after the 13:24 `page_15.json` test and well *before* the 17:16+ batch run — so it reflects the same `page_N.json`-producing code already in the repo today, not a different `bn_`/`en_`-prefixed variant.
   - No `.log` file in `backend/` mentions `fix_math_notation`, `comparison`, or `improvement_score`.
3. **Conclusion: the driver script for the 45-file batch was an ad-hoc/one-off script** (very likely reusing `fix_math_notation()` + `compute_changes()` from `pdf_extractor.py` directly, plus its own `bn_`/`en_`-prefixed save logic and an added `"language"` key) **that was run once on 2026-08-10 and never committed to git** — the repo's git history starts a month later (2026-09-07), and nothing in the current working tree reproduces its exact output format. It cannot be recovered from this repo.

## Bottom line
- **Correction mechanism**: Groq chat completion, prompt = `_MATH_FIX_PROMPT` in `backend/ingestion/pdf_extractor.py` — confirmed directly from code.
- **Model** (inferred from config-default timeline, not stored in the data itself): **`llama-3.3-70b-versatile`**.
- **Driver script for the actual 45-page batch**: not found in the repo; presumed ad-hoc and lost. Stated here rather than guessed at.
