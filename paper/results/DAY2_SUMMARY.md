# Day 2 Summary — Page images + Gemini Vision transcription

## What was done

**Task A — rendered 5 page images** (`paper/scripts/day2_render_pages.py`, PyMuPDF, 300 DPI):
- `paper/page_images/bn_page_30.png`, `bn_page_36.png`, `bn_page_44.png` (from `backend/data/pdfs/2026/bangla/class_9_General_math_bn.pdf`)
- `paper/page_images/en_page_30.png`, `en_page_38.png` (from `backend/data/pdfs/2026/english/class_9_General_math_en.pdf`)
- Sanity check passed: Bangla page 30's first OCR line reads exactly `অধ্যায় ২. সেট ও ফাংশন ২৫` as expected.

**Task B — Gemini Vision transcription** (`paper/scripts/day2_gemini_vision.py`, model = `settings.gemini_model` = `gemini-3.6-flash`, temperature 0):
- **3 of 5 succeeded**: `paper/gemini_vision/bn_page_30.txt`, `bn_page_36.txt`, `bn_page_44.txt`.
- **2 of 5 failed**: `en_page_30`, `en_page_38` — see "Problems" below.
- Full run details (model name requested, prompt, settings, per-page status/char-counts/errors) in `paper/gemini_vision/RUN_LOG.md`.

**Task C — identified the Chapter 2 correction model** (`paper/results/DAY2_CORRECTION_MODEL.md`):
- Correction code confirmed: `fix_math_notation()` in `backend/ingestion/pdf_extractor.py` (Groq chat completion, not Gemini).
- Model inferred as **`llama-3.3-70b-versatile`** from the config-default timeline (file mtimes of the comparison JSONs = 2026-08-10, a month before `groq_model` was changed to `qwen/qwen3.8-27b` on 2026-09-08) — not stored in the data itself, so this is a documented inference, not a direct read.
- The actual driver script that ran the 45-file batch could **not** be found anywhere in the repo (git history or working tree) — stated plainly rather than guessed. Full search trail is in that file.

## File list
```
paper/page_images/bn_page_30.png
paper/page_images/bn_page_36.png
paper/page_images/bn_page_44.png
paper/page_images/en_page_30.png
paper/page_images/en_page_38.png
paper/gemini_vision/bn_page_30.txt
paper/gemini_vision/bn_page_36.txt
paper/gemini_vision/bn_page_44.txt
paper/gemini_vision/RUN_LOG.md
paper/results/DAY2_CORRECTION_MODEL.md
paper/results/DAY2_SUMMARY.md   (this file)
paper/scripts/day2_render_pages.py
paper/scripts/day2_gemini_vision.py
```
Not produced (see Problems): `paper/gemini_vision/en_page_30.txt`, `paper/gemini_vision/en_page_38.txt`.

## Problems

1. **Gemini `gemini-3.6-flash` free-tier daily quota (20 requests/day) was already exhausted partway through this run** — the first 3 calls (`bn_page_30`, `bn_page_36`, `bn_page_44`) succeeded, then every call from `en_page_30` onward got HTTP 429 `"Quota exceeded... limit: 20, model: gemini-3.6-flash... Please retry in 15h37m"`. This is the same known limitation already documented in `CLAUDE.md`'s "Known Issues" (20 req/day free tier) — it means **some of today's 20-request daily budget had already been used before this script ran** (by earlier testing today, not by this script, which only ever made 3 successful + 2×2 failed-attempt calls = 7 total, within the DAY2.md budget of "max 5 + 1 retry per failed page" = max 7).
   - This was **not** a model-name failure (no 404/NotFound — the model name `gemini-3.6-flash` is valid, confirmed by the 3 successful calls), so per DAY2.md's instructions the script correctly did NOT stop-and-ask or switch models — it logged the failures, retried once each, and moved on, exactly as the budget rule allows.
   - **`en_page_30.txt` and `en_page_38.txt` still need to be transcribed.** The quota resets in ~15h37m from the run (started 2026-10-06 14:17 local time) — i.e. not until some time on **2026-10-07**. Re-running `paper/scripts/day2_gemini_vision.py` tomorrow will only re-attempt all 5 pages again (it doesn't currently skip already-done pages) — if re-running, either restrict `TARGETS` in that script to the 2 missing pages first, or accept it re-spends 3 requests re-doing the 3 that already succeeded. Flagging this now rather than silently burning more quota today.
2. **Task C's driver script for the real 45-page Chapter 2 correction batch is missing from the repo** (see `DAY2_CORRECTION_MODEL.md` for the full search trail). The *model* is a confident inference (`llama-3.3-70b-versatile`), not a directly-read fact, because it isn't stored anywhere in the comparison JSON files themselves.

## What Peal must check by eye

Please open 1-2 of the rendered page images side-by-side with their matching Gemini transcription and confirm they actually match the printed page (this was not verified beyond the automated header sanity-check in Task A):
- `paper/page_images/bn_page_30.png` vs `paper/gemini_vision/bn_page_30.txt`
- `paper/page_images/bn_page_44.png` vs `paper/gemini_vision/bn_page_44.txt`

Also please confirm/correct the Task C conclusion in `paper/results/DAY2_CORRECTION_MODEL.md` if you happen to remember which script you (or Claude in an earlier, now-lost session) actually ran on 2026-08-10 for the batch correction — that detail could not be recovered from the repo.
