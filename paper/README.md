# Paper workspace — "Where OCR Breaks on Bangla Mathematics Textbooks"

Goal: an arXiv preprint (cs.CL) before the KAUST application (early December 2026).
Scope: Class 9-10 General Math, Chapter 2 (Sets and Functions) only.
Do not change anything under backend/ or frontend/. All new code goes in paper/scripts/.

## Folder map
| Folder | What goes here |
|---|---|
| tasks/ | One instruction file per day (DAY2.md, DAY3.md, ...). Claude Code: read the day's file and do exactly that. |
| scripts/ | All code written for the paper |
| results/ | Tables, CSVs and DAYn_SUMMARY.md files |
| page_images/ | 300-DPI PNGs of the selected pages |
| gemini_vision/ | Gemini Vision transcriptions + RUN_LOG.md |
| ground_truth/ | Hand-checked exact text of the selected pages (made by Peal, never by an LLM alone) |
| rag_test/ | 20 questions, reference answers, system answers, Peal's correct/incorrect marks |
| draft/ | main.tex / main.pdf — the paper draft |

## Data facts (verified 2026-10-06)
- Source PDFs: backend/data/pdfs/2026/bangla/class_9_General_math_bn.pdf and backend/data/pdfs/2026/english/class_9_General_math_en.pdf
- Page numbers in backend/data/comparison/ and ocr_raw/ are PDF page numbers (1-based), NOT printed page numbers (PDF page 30 = printed page 25 in the Bangla book).
- Tesseract raw: backend/data/ocr_raw/class_9_General_math_{bn,en}/page_N.txt
- LLM-corrected text + edit log: backend/data/comparison/{bn,en}_page_N.json (keys: raw, fixed, changes, changes_count, improvement_score). Same text also in backend/data/ocr_fixed/.
- Known data bug: `chapter` is None in 22 of the 45 comparison files; page_15.json is a stray test file — ignore it.
- Models in backend/config.py: groq_model = qwen/qwen3.8-27b, gemini_model = gemini-3.6-flash, tiebreak = openai/gpt-oss-120b. Chapter 2 correction code = fix_math_notation() in backend/ingestion/pdf_extractor.py (Groq, settings.groq_model, math-notation prompt). Exact model at run time not recoverable (data files are gitignored); likely llama-3.3-70b-versatile — report as 'a Groq-hosted LLM' unless confirmed. See results/DAY2_CORRECTION_MODEL.md.

## Selected pages for ground truth / comparison
Bangla PDF pages 30, 36, 44 · English PDF pages 30, 38

## Day plan
| Day | Task | Status |
|---|---|---|
| 1 | Count & categorise the 1,024 LLM corrections | DONE (results/DAY1_SUMMARY.md) |
| 2 | Render 5 page images, Gemini Vision transcription, find correction model | DONE except en_page_30/38 (Gemini quota) |
| 3-4 | Ground truth: bn 30, 36, 44 verified by Peal (2026-10-06); en 30, 38 pending Gemini quota | DONE (Bangla) |
| 5 | CER + error classes + Groq edit audit | tasks/DAY5.md |
| 6 | RAG test with 20 questions | — |
| 7 | Collect all results -> paper draft | — |
