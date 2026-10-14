# DAY 3 — Prepare ground-truth drafts (Peal checks them by eye on Day 3-4)

Read paper/README.md first. Do not modify backend/ or frontend/.

## Task A — Finish the 2 missing Gemini pages (only if quota has reset)
1. Re-run paper/scripts/day2_gemini_vision.py for en_page_30 and en_page_38 ONLY (same model, same prompt, temperature 0). Max 1 retry each.
2. Append the result to paper/gemini_vision/RUN_LOG.md. If quota still fails, write that in the log and continue with Task B for the Bangla pages.

## Task B — Make draft ground-truth files
For every page that has a Gemini transcription (bn_page_30, bn_page_36, bn_page_44, and en_page_30 / en_page_38 if Task A worked):
1. Copy paper/gemini_vision/{page}.txt to paper/ground_truth/{page}_DRAFT.txt (UTF-8, unchanged).
2. Write paper/scripts/day3_diff_hints.py that, for each page, compares the Gemini text with the Tesseract raw text (backend/data/ocr_raw/class_9_General_math_{lang}/page_N.txt) line by line and writes paper/ground_truth/{page}_CHECKLIST.md listing every line where the two differ a lot (so Peal knows where to look hardest). Keep it simple (difflib).
3. Do NOT "fix" anything in the drafts yourself. The ground truth must come from Peal reading the printed page.

## Task C — Instructions for Peal (write to paper/ground_truth/HOW_TO_CHECK.md, in Bangla)
Explain simply:
- Open {page}.png (in paper/page_images/) and {page}_DRAFT.txt side by side (VS Code: right-click the png -> "Open to the Side").
- Read line by line. Fix every difference so the txt matches the printed page exactly: every symbol, digit (Bangla vs English digit exactly as printed), brace, superscript.
- Use the CHECKLIST to look hardest at flagged lines, but check ALL lines.
- Do not fix spacing/alignment; only characters. One line in the book = one line in the file. Skip page header/footer? -> KEEP them (they are part of the page).
- When a page is done, rename it from {page}_DRAFT.txt to {page}.txt. That rename means "Peal verified".

## Finish
Write paper/results/DAY3_SUMMARY.md (files created, which pages are ready for Peal, Gemini quota status).
