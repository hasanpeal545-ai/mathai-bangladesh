# FULL OCR — re-read every NCTB math book with Gemini Vision (paid tier)

Read paper/README.md first. Precondition: Peal has enabled the Gemini paid tier. If calls still return free-tier quota errors, STOP and tell Peal.

## Rules
- Do NOT modify or delete anything that already exists in backend/ (ocr_raw, ocr_fixed, comparison, approved, Qdrant). The old Tesseract data is needed for the paper.
- New output goes ONLY to backend/data/ocr_gemini/<book_name>/page_N.txt (new folder; creating it is allowed).
- Same model, prompt and settings as Day 2 (see paper/gemini_vision/RUN_LOG.md and paper/scripts/day2_gemini_vision.py): config.gemini_model, temperature 0, the exact "Transcribe this textbook page exactly as printed..." prompt.
- Page images: render each PDF page at 300 DPI in memory (PyMuPDF); do not save PNGs for all pages.

## Step 1 — Inventory
1. List all PDFs in backend/data/pdfs/2026/bangla and backend/data/pdfs/2026/english with page counts.
2. Check for duplicate books (e.g. class_9 vs class_10 files may be the same book): compare page count + SHA-256 of the first few pages' text/images. Skip exact duplicates and say which.
3. Write paper/results/FULL_OCR_INVENTORY.md (book, language, pages, duplicate-of).

## Step 2 — Script (paper/scripts/full_gemini_ocr.py)
- Resumable: skip a page if its output file already exists and is non-empty.
- Log every call to backend/data/ocr_gemini/RUN_LOG.csv: book, page, time, model, input tokens, output tokens, status, error.
- Retry a failed page at most 2 times with backoff; then log and move on.
- Keep a running total of tokens. Stop and report if the estimated cost passes $4 (or if the API reports insufficient balance).
- Command-line options: --books, --max-pages, --sample.

## Step 3 — Pilot (then WAIT for Peal)
Run --sample: 3 pages from each distinct book (one near the start, one middle, one with heavy math), about 20-25 pages total.
Write paper/results/FULL_OCR_PILOT.md: list of pilot pages, token usage, estimated cost for ALL pages, and any page whose output looks wrong (empty, cut off, English page answered in Bangla, etc.).
Then STOP and tell Peal: "Pilot done. Check 2-3 pilot pages against the images and say 'run all' to continue."

## Step 3b — Fixes from the pilot check (do these BEFORE Step 4)
Claude (chat) compared all 28 pilot pages with their images. Results: paper/check/ERRORS_LOG.csv. Findings:
- Content errors on 4 of 28 pages, all on Bangla pages: Bangla digits misread (৭→৯, ৪→৮) in an answer key, a worked example and a question number, plus one word substitution (প্রত্যেকটি→প্রতিটি).
- The vertical margin year (২০২৬) is wrong on every Bangla page (২০২৩/২০২৪/split) and sometimes inserted in the middle of the text; on English pages it is sometimes omitted.
Implement:
1. Prompt addition (append to the existing prompt, keep everything else identical): "Read Bangla digits (০১২৩৪৫৬৭৮৯) very carefully; do not confuse ৭ with ৯, ৪ with ৮, or ৩ with ৬. Ignore any text printed vertically in the page margin. Write fractions as a/b, not LaTeX."
2. Bangla pages only: call Gemini TWICE per page (same prompt, temperature 0 for the first call and 0.4 for the second). Save the first as page_N.txt and the second as page_N.alt.txt. Write paper/check/digit_disagreements.csv listing every line where the two readings differ in any digit (book, page, line, reading1, reading2). Those lines are what Claude (chat) checks first.
3. Post-process every output: remove standalone margin-year tokens (২০২৩ ২০২৪ ২০২৫ ২০২৬ 2023-2026) that appear on their own line or at the end of a line after 10+ spaces. Keep a copy of the raw API text in page_N.raw.txt.
4. RECITATION-blocked pages: do not retry; write the Tesseract text from backend/data/ocr_raw/<book>/page_N.txt into page_N.txt with a first line "[FALLBACK: TESSERACT — Gemini RECITATION block]" and list the page in paper/check/blocked_pages.csv.
5. Re-run the 28 pilot pages with the new prompt (Bangla pages twice) so they match the new pipeline, then re-render their images into paper/check/pilot/ and STOP: tell Peal "Pilot re-run done — ask Claude (chat) to check it."

## Step 3c — Cut the cost (do BEFORE Step 4)
Claude (chat) checked the re-run. Accuracy of the new prompt was NOT clearly better than the old one (156 still wrong in the primary reading; page 14 got a NEW error "৯. ২৫ ৩০ ৩০ ০০" vs book "৯.২৫ ৩০ ০০ ০০"; page 29 still has one "প্রতিটি" for "প্রত্যেকটি"; fixed: 177, LaTeX, margin years). The double reading is what actually catches digit errors (both 156 and 14 were caught by the alt reading). So:
1. Remove ONLY the sentence about reading Bangla digits carefully from the prompt. Keep: "Ignore any text printed vertically in the page margin. Write fractions as a/b, not LaTeX."
2. Keep the Bangla double-call, margin-year stripping and RECITATION fallback exactly as they are.
3. If the SDK/API supports limiting thinking for this model (e.g. a thinking budget / thinking level setting), set it to the lowest allowed value. If not supported, skip this and say so.
4. Test on 4 pages only: class_6_math_bn p156, class_7_math_bn p14, class_8_math_en p196, class_9_General_math_bn p29. Report output tokens per call before vs after, and whether p156/p14 digit disagreements are still flagged.
5. Write paper/results/FULL_OCR_COST_TEST.md and STOP.

## Step 3d — Real prices + a cheaper model test (do BEFORE Step 4)
Real billing (AI Studio Spend page, 2026-10-07): $1.62 so far for ~90k input + ~253k output tokens (billing lags a few hours). Published price for gemini-3.6-flash is $1.50 / 1M input and $7.50 / 1M output, thinking tokens billed as output. The $0.10/$0.40 placeholder in full_gemini_ocr.py is wrong by ~15-19x — replace it with the real prices and recompute both pilot projections in the report. Remaining credit is about $8.40; the $4 auto-stop stays.

Do NOT touch backend/venv. Create a separate venv at paper/.venv (or call the REST API with `requests`) so you can use the current Gemini API features:
1. List the available models for this API key (models.list) and write the list to paper/results/AVAILABLE_MODELS.md. Find the current Flash-Lite model and the thinking control fields (thinkingConfig: thinkingLevel or thinkingBudget) that each model accepts. Do not guess field names — read the API error/response or the official docs.
2. Run these 5 pages with (a) gemini-3.6-flash with the lowest thinking setting it accepts and (b) the Flash-Lite model with the lowest thinking setting:
   bn: class_9_General_math_bn p30, p36, p44 (these have hand-verified ground truth in paper/ground_truth/bn_page_{30,36,44}.txt)
   plus class_6_math_bn p156 and class_7_math_bn p14 (known digit-error pages).
   Same prompt as now (margin-ignore + plain fractions). Temperature 0. One call per page per setting (no double call in this test).
3. For p30/p36/p44 compute CER against ground truth with paper/scripts/day5_cer.py's method (whitespace removed). Report per page and mean, next to the Day 5 Gemini CER (0.24%).
4. For p156 and p14 report whether "(ঘ) ৭০ : ২৩" and "১০৪" / "৯.২৫ ৩০ ০০ ০০" are read correctly.
5. Report input/output tokens and REAL cost per page for each setting, and the projected cost for all 2,562 pages (with and without the Bangla double call), and for Class 9-10 books only (1,448 pages).
6. Write paper/results/FULL_OCR_MODEL_TEST.md and STOP. Total spend for this step must stay under $0.50.

## Step 3e — FINAL settings (decided by Peal + Claude chat, 2026-10-07). No more API tests.
1. Model: gemini-3.5-flash-lite via REST, thinkingLevel "minimal", temperature 0 (primary) / 0.4 (Bangla alt). Same prompt as Step 3d.
2. Keep: Bangla double-call + digit_disagreements.csv, margin-year stripping, RECITATION fallback to Tesseract, page_N.raw.txt copies.
3. NEW, free (no API): LaTeX-to-plain post-processing on every output — strip $...$ delimiters, \begin{array}/\end{array}, and map \cup ∪, \cap ∩, \in ∈, \notin ∉, \subset ⊂, \subseteq ⊆, \emptyset/\varnothing ∅, \therefore ∴, \times ×, \div ÷, \le ≤, \ge ≥, \neq ≠, \pm ±, \{ \} to { }, \frac{a}{b} to a/b, ^{n} / ^2 to superscripts where possible. Keep the raw text in page_N.raw.txt.
4. Re-score Step 3d's saved outputs for p30/p36/p44 AFTER this post-processing (no new API calls) and add the CER to FULL_OCR_MODEL_TEST.md.
5. Book order for Step 4: class_9_General_math_bn, class_9_General_math_en, class_9_Hiher_math_bn, class_9_Higher_math_en, then class_8 (bn, en), class_7, class_6.
6. Cost stop: replace the $4 stop with a stop at $7.00 total spend for Step 4 (real prices: flash-lite $0.30/1M in, $2.50/1M out; verify these on the official pricing page or say they are unverified). Expected: Class 9-10 ≈ $4.8, all books ≈ $8.4, so the run will stop around class 7/6 — that is intended.
Then STOP and say "Final settings ready — ask Claude (chat) to approve run all."

## Step 4 — Full run in BATCHES OF 10 PAGES (only after Peal says "run all")
1. Process the next 10 pages (book by book, in page order). Skip pages already done.
2. For each page of the batch, also save the 300-DPI page image to paper/check/<book>/page_N.png so the images can be compared with the text. (Delete paper/check/<book>/ images only after Peal says the batch is checked — never delete the text files.)
3. Write paper/check/CURRENT_BATCH.md listing the 10 pages: book, page, image path, text path (backend/data/ocr_gemini/<book>/page_N.txt), character count.
4. STOP and tell Peal: "Batch ready: <book> pages X-Y. Ask Claude (chat) to check it."
5. When Peal says "next batch", clear paper/check/<book>/*.png for the checked pages and run the next 10. If Peal says "fix page N", re-run Gemini on that page only.

## Step 5 — Automatic quality check (after each book)
Write paper/scripts/ocr_quality_check.py and run it on the finished book. For every page compare the Gemini text with the old Tesseract text of the same page (backend/data/ocr_raw/...) and flag the page if ANY of these is true:
- empty or very short output (< 30% of Tesseract's character count, or < 50 characters on a page Tesseract found text on)
- much longer than Tesseract (> 2x) — possible hallucination
- the same line or phrase repeated 3+ times in a row (model loop)
- wrong script: a Bangla-book page with < 30% Bangla characters, or an English-book page with > 30% Bangla characters
- output does not end cleanly / API reported truncation (finish reason not STOP)
- page has Tesseract text with math-like garbage but Gemini text has no math symbols, digits or braces at all
- the response contains commentary instead of transcription ("Here is the transcription", "I cannot", markdown fences)
Write paper/results/qc_<book>.csv (page, flags, chars_gemini, chars_tesseract) and paper/results/qc_<book>_FLAGGED.md listing only the flagged pages with the reason. Re-run Gemini once on pages flagged for "empty", "truncated" or "commentary" and re-check them.
Also pick 3 random NON-flagged pages per book and list them in the same report for a visual spot-check.

## Final
At the end write paper/results/FULL_OCR_SUMMARY.md: pages done / failed / flagged per book, total tokens and estimated cost.
Keep all text files — they are small (a few KB per page) and are the new corpus for the tutor. Never delete backend/data/ocr_gemini/.


## v1 STOP RULE (2026-10-08)
arXiv v1 শুধু class 9-10 এর ৪টা বই। BOOK_ORDER এর প্রথম ৪টা বই (class_9_General_math_bn, class_9_General_math_en, class_9_Hiher_math_bn, class_9_Higher_math_en) শেষ হলে OCR থামবে — class_8/7/6 শুরু করবে না যতক্ষণ না Claude (chat) বলে। শেষ বইয়ের শেষ batch এর পরে লেখো: "v1 OCR done. Ask Claude (chat)."
