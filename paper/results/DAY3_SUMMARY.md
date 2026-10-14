# Day 3 Summary — ground-truth drafts

## Gemini quota status

Still exhausted. Re-ran `paper/scripts/day2_gemini_vision.py en_page_30 en_page_38` (Task A) — both failed again with HTTP 429 (`"limit: 20, model: gemini-3.6-flash... retry in 15h20m"`), same free-tier daily-quota issue as Day 2. This was **not** a model-name failure (no 404/NotFound), so per instructions the script did not stop-and-ask or switch models — it logged the attempt (1 retry each, as DAY3.md specifies) and the result was appended to `paper/gemini_vision/RUN_LOG.md` (now has two run sections: the original Day 2 run + this Day 3 retry).

Per Peal's instruction for this task ("Gemini কোটা শেষ থাকলে ইংরেজি পৃষ্ঠা বাদ দিয়ে বাংলা ৩টা পৃষ্ঠা নিয়ে কাজ শেষ করো"), Tasks B and C below proceeded with **only the 3 Bangla pages** (`bn_page_30`, `bn_page_36`, `bn_page_44`). `en_page_30` / `en_page_38` were skipped entirely — no drafts, no checklists for them yet.

## Files created

```
paper/scripts/day3_diff_hints.py                    (new script, Task B)
paper/ground_truth/bn_page_30_DRAFT.txt              (copy of gemini_vision/bn_page_30.txt, unchanged)
paper/ground_truth/bn_page_36_DRAFT.txt              (copy of gemini_vision/bn_page_36.txt, unchanged)
paper/ground_truth/bn_page_44_DRAFT.txt              (copy of gemini_vision/bn_page_44.txt, unchanged)
paper/ground_truth/bn_page_30_CHECKLIST.md           (32 flagged word-level changes)
paper/ground_truth/bn_page_36_CHECKLIST.md           (23 flagged word-level changes)
paper/ground_truth/bn_page_44_CHECKLIST.md           (21 flagged word-level changes)
paper/ground_truth/HOW_TO_CHECK.md                   (Task C, in Bangla)
```
Also modified: `paper/scripts/day2_gemini_vision.py` — added optional CLI args to restrict which pages to (re-)run (`python day2_gemini_vision.py en_page_30 en_page_38`, defaults to all 5 with no args), and changed `RUN_LOG.md` writing from overwrite to append, so Day 2's run history is preserved rather than erased by Day 3's retry. No other files under `backend/` or `frontend/` were touched.

## Method note on Task B's checklist (differs from a literal reading of DAY2.md's wording)

DAY3.md's Task B step 2 describes comparing "line by line." A literal line-by-line `difflib.SequenceMatcher` was tried first and discarded: Tesseract and Gemini wrap the same paragraph into different line lengths, so almost no line is byte-identical between the two, and a line-level matcher ends up treating nearly the entire page as one giant insert/delete block — every line gets flagged, which defeats the purpose of "look hardest here." Instead, `day3_diff_hints.py` diffs at the **word level** (the same technique already used in `backend/ingestion/pdf_extractor.py`'s `compute_changes()` and `paper/scripts/day1_correction_stats.py`), which tolerates line-wrap differences and finds real matching stretches of text. Each flagged word-level change is still mapped back to a Gemini-draft line number, so the output is still "which lines to look at," just computed more robustly. Flagged only if a change touches ≥3 words or the before/after character similarity is <0.5 (small 1-2 word edits like a digit swap are left unflagged — easy to spot by eye, not worth cluttering the checklist).

## Which pages are ready for Peal

| Page | DRAFT ready | CHECKLIST ready | Status |
|---|---|---|---|
| bn_page_30 | ✅ | ✅ (32 flagged) | Ready for hand-check |
| bn_page_36 | ✅ | ✅ (23 flagged) | Ready for hand-check |
| bn_page_44 | ✅ | ✅ (21 flagged) | Ready for hand-check |
| en_page_30 | ❌ (blocked on Gemini quota) | ❌ | Not started |
| en_page_38 | ❌ (blocked on Gemini quota) | ❌ | Not started |

## What Peal should do next

Follow `paper/ground_truth/HOW_TO_CHECK.md` (written in Bangla) for the 3 Bangla pages: open each `{page}.png` beside its `{page}_DRAFT.txt`, use the matching `{page}_CHECKLIST.md` as a hint for where to look hardest (but check every line, not just flagged ones), fix every character/digit/symbol/bracket/superscript difference against the printed page, then rename `{page}_DRAFT.txt` → `{page}.txt` when done — that rename is what marks a page as hand-verified.

Once Gemini's daily quota resets (RUN_LOG.md's retry-delay said ~15h20m from the Day 3 retry, i.e. sometime on 2026-10-07), re-run `python paper/scripts/day2_gemini_vision.py en_page_30 en_page_38` to get the 2 English drafts, then `python paper/scripts/day3_diff_hints.py` (after adding the two English pages back to its `TARGETS` list) to produce their checklists too.
