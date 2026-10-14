# DAY 2 — Page images + Gemini Vision transcription

Read paper/README.md first (folder map, data facts, rules).
Rules: do not modify anything in backend/ or frontend/. New code only in paper/scripts/. Max 5 Gemini API requests in total (plus at most 1 retry per failed page). If the model name fails, STOP and ask Peal — do not silently switch models.

## Task A — Render page images
1. Write paper/scripts/day2_render_pages.py using PyMuPDF (fitz is installed in backend/venv).
2. Render at 300 DPI:
   - backend/data/pdfs/2026/bangla/class_9_General_math_bn.pdf  -> PDF pages 30, 36, 44
   - backend/data/pdfs/2026/english/class_9_General_math_en.pdf -> PDF pages 30, 38
   (1-based page numbers, i.e. fitz index = N-1.)
3. Save as paper/page_images/bn_page_30.png, bn_page_36.png, bn_page_44.png, en_page_30.png, en_page_38.png.
4. Sanity check: for each page, print the first 2 lines of backend/data/ocr_raw/class_9_General_math_{lang}/page_N.txt so Peal can confirm the image matches (Bangla page 30 header should read "অধ্যায় ২. সেট ও ফাংশন ২৫").

## Task B — Gemini Vision transcription
1. Look at backend/test_gemini_vision.py and backend/config.py to reuse the existing Gemini call pattern and API key loading (.env). Use the model in config.gemini_model.
2. Write paper/scripts/day2_gemini_vision.py. For each of the 5 images send exactly this prompt:
   "Transcribe this textbook page exactly as printed. Keep Bangla text in Bangla script and English in English. Write mathematical symbols as Unicode (∈ ∉ ∪ ∩ ∅ ∴ × − ⊂ ⊆, superscripts like ² ⁿ). Keep line breaks. Do not correct, translate, summarise, add or skip anything. Output only the transcription."
3. Save each output to paper/gemini_vision/{lang}_page_{N}.txt (UTF-8).
4. Write paper/gemini_vision/RUN_LOG.md with: date/time, exact model name returned by the API, prompt text, temperature/settings, per-page status and character count, any errors.

## Task C — Find which model did the Chapter 2 OCR correction
1. Search the repo (outside venv) and git history for the code that produced backend/data/comparison/*.json (look for "improvement_score", "changes_count", "ocr_fixed"). Check `git log --all --stat -- backend/data/comparison` too.
2. Write what you find (script path, model name, prompt, date) into paper/results/DAY2_CORRECTION_MODEL.md. If it cannot be found, say so plainly — do not guess.

## Finish
Write paper/results/DAY2_SUMMARY.md: what was done, file list, problems, anything Peal must check by eye. Then tell Peal to open 1-2 images and their Gemini txt files to confirm they match the printed page.
