# BanglaMathai — Project Memory

## Project Overview
RAG-based Adaptive Bangla Math Tutoring System for NCTB Class 6-10 students in Bangladesh.
Backend: Python/FastAPI/LangChain/LangGraph/Qdrant Cloud/Groq/Gemini.
Frontend: React + TypeScript + TailwindCSS + PWA.
Deploy: Hostinger VPS, Docker Compose, Nginx, SSL.

## Problem Statement
লক্ষ লক্ষ গরিব শিশু বাংলাদেশে math teacher বা guide book রাখতে পারে না। BanglaMathai তাদের জন্য বিনামূল্যে, NCTB curriculum অনুসরণকারী, SSC board format এ answer দেওয়া AI math tutor।

Target users: Class 6-10 শিক্ষার্থী, গ্রামের গরিব শিশু, যারা teacher/guide book এর টাকা দিতে পারে না।

## Features Status

### Phase 1 — Core (Paper এর জন্য)
- ✅ Feature 1 — Dual Query Mode (reference-based + direct question) — backend FastAPI skeleton + `/api/health` done; `/api/chat` now RAG-wired for both modes (see below); `chapter`/`exercise` both optional in reference mode
- ✅ Feature 2 — Class-wise Board Standard (6-7 / 8 / 9-10 SSC exact format) — `class_standards.py` built, unit-tested, and wired into `solver.py`/`/api/chat` (confirmed working via Feature 3's end-to-end test)
- ✅ Feature 3 — Multi-LLM Cross-check (Groq + Gemini + tiebreak + rate-limit fallback), wired into `/api/chat`, verified with a real SSC-style math question end-to-end
- ✅ Feature 4 — Smart Glossary System — all 3 tiers built, tested, and wired into `/api/chat` (query terms detected + fed to the LLM as hints, solution-side English leakage detected, both surfaced via a new `glossary_terms` response field). Admin approve/reject UI (Phase 3, Feature 20) still pending — separate, later feature.
- ⏳ Feature 5 — Interactive Figure (Plotly, real-time geometry) — not started (see note below: user is currently working on the PDF ingestion pipeline instead, ahead of this)
- ✅ **PDF Ingestion Pipeline** (`ingestion/pdf_extractor.py`, not a numbered spec feature) — OCR extraction ✅ (full 362-page book tested: 17 chapters, 38 exercises, 888 chunks). OCR+LLM dual-output/comparison system ✅ (tested on page 15). Admin preprocess/approve/reject/summary API endpoints ✅ built. All 3907 approved chunks pushed into Qdrant's `nctb_math_content` collection ✅ (2026-09-08, `run_qdrant_push.py`). Reference-mode retrieval in `/api/chat` ✅ wired (2026-09-08, see below).
- ⏳ Feature 6 — Step-by-step Mode
- ⏳ Feature 7 — Difficulty Detection
- ⏳ Feature 8 — Practice Mode
- ⏳ Feature 9 — Voice Input (বাংলা, Web Speech API)
- ⏳ Feature 10 — Confusion Detection
- ⏳ Feature 11 — Smart Error Analysis
- ⏳ Feature 12 — Bilingual Support (bn/en)

### Phase 2 — Advanced
- ⏳ Feature 13 — Multi-modal Input (photo/handwriting recognition)
- ⏳ Feature 14 — Personalized Learning
- ⏳ Feature 15 — Exam Preparation Mode
- ⏳ Feature 16 — Offline PWA Mode
- ⏳ Feature 17 — Gamification

### Phase 3 — Platform
- ⏳ Feature 18 — Teacher Dashboard
- ⏳ Feature 19 — Parent Dashboard
- ⏳ Feature 20 — Admin Panel
- ⏳ Feature 21 — API as a Service
- ⏳ Feature 22 — Content Moderation

Legend: ✅ Done | 🔄 In progress | ⏳ Not started

## Current File Structure
```
/banglamathai
  /backend
    main.py, auth.py, prompts.py, config.py, .env, requirements.txt
    /ingestion       → pdf_extractor.py, solution_learner.py, chunker.py, pdf_manager.py, version_controller.py
    /retrieval       → vector_store.py, retriever.py, glossary_engine.py, term_learner.py
    /solving         → solver.py, cross_checker.py, class_standards.py, error_analyzer.py
    /features        → figure_generator.py, step_mode.py, difficulty_tracker.py, practice_mode.py,
                        confusion_handler.py, voice_handler.py, exam_prep.py, learning_path.py
    /admin           → admin.py, analytics.py, moderation.py, glossary_admin.py
    /models          → user.py, session.py, progress.py, glossary.py
    /data/pdfs/{2025,2026}, /data/solution_style/versions, /data/archive
  /frontend
    /src
      /components/{chat,figure,modes,dashboard,gamification,auth}  (all .tsx stubs created)
      App.tsx, index.tsx, service-worker.ts
    tsconfig.json, package.json
  CLAUDE.md, README.md, docker-compose.yml, nginx.conf
```
Most files above still exist as empty stub files (one-line purpose comment only) — no logic implemented yet. Exceptions with real code so far: `backend/main.py` (FastAPI app, `/api/health`, `/api/chat` fully wired to the solver incl. `glossary_terms` in the response), `backend/config.py` (pydantic-settings, API keys + model names incl. tiebreak + Qdrant), `backend/solving/class_standards.py` (per-class style rules), `backend/solving/cross_checker.py` (Groq+Gemini+tiebreak cross-check with rate-limit fallback), `backend/solving/solver.py` (prompt building incl. SSC few-shot example + glossary-hint injection, returns `SolveResult`), `backend/retrieval/vector_store.py` (Qdrant Cloud REST wrapper), `backend/retrieval/glossary_engine.py` (3-tier glossary + query/solution text scanning), `backend/retrieval/term_learner.py` (Tier 3 self-learning: LLM translation + Qdrant auto-store + file log), `backend/ingestion/pdf_extractor.py` (OCR-based text extraction + chapter/exercise/problem chunking). `backend/data/glossary_learning_log.txt` is a new runtime-generated log file (not hand-authored). `backend/data/pdfs/2026/{bangla,english}/` now contains 14 real NCTB textbook PDFs (7 per language). `backend/data/tessdata/` holds Tesseract's `eng`/`ben` language files (project-local, not the system install). `__init__.py` added to every backend subpackage (`ingestion`, `retrieval`, `solving`, `features`, `admin`, `models`) for proper Python packaging.

## Task History (compact)
1. **Scaffolding** — full folder structure, `requirements.txt`, `package.json`, `tsconfig.json`, `.env` template, `docker-compose.yml`, `nginx.conf`.
2. **Feature 1 (structure) + fix** — `/api/chat` request/response schema built with validation; later fixed so `reference` mode doesn't require `chapter`/`exercise` (both optional — user clarified students may query with just class+chapter, no exercise number).
3. **Feature 2** — `class_standards.py`: `get_class_standard(class_number)` returns style rules for 6-7 / 8 / 9-10 (SSC exact format incl. required markers). Unit-tested standalone.
4. **Feature 3** — Groq ping ✅, Gemini ping ✅ (both required swapping spec's named models for current equivalents — see Important Decisions), `cross_checker.py` (Groq+Gemini+3rd-LLM-tiebreak+rate-limit-fallback, 5-level confidence), `solver.py` (SSC few-shot prompt), wired into `/api/chat`. Verified end-to-end with the triangle-area question — output matches spec's own Example 2. Found & fixed 2 real bugs along the way (degenerate SSC answers from prose-only prompting; Windows `curl.exe` corrupting inline Bangla text in tests).
5. **Feature 4, all 3 tiers + wiring** — `glossary_engine.py` (51 seed terms, exact+semantic+LLM-learn), `vector_store.py` (Qdrant REST wrapper — see Important Decisions), `term_learner.py` (Tier 3: Groq translation + Qdrant auto-store + file log). Embedding model swapped mid-stream from MiniLM (miscalibrated for short Bangla terms) to `intfloat/multilingual-e5-large` (user-approved). Tested with `"সমদ্বিবাহু"` (not in seed) → correctly fell through to Tier 3 → Groq said `"Isosceles"` → auto-stored → logged. Then wired into `/api/chat`: `find_terms_in_text()`/`find_english_terms_in_text()` added, `solver.build_prompt()` injects a glossary hint into the LLM prompt, `ChatResponse` gained a `glossary_terms` field. Verified end-to-end with `"অতিভুজ এর দৈর্ঘ্য কত"` → correctly detected + translated + used by the LLM. Compacted 2026-08-10 to keep this file manageable; see conversation history for full narrative if needed again.

## Last Task Completed
**2026-08-10 — PDF ingestion pipeline (`ingestion/pdf_extractor.py`), in progress:**

User asked to build a PDF extractor per the original spec pattern (PyMuPDF text extraction → detect language from folder → detect chapter/exercise → chunk each math problem). Real NCTB PDFs turned out to already be placed at `backend/data/pdfs/2026/{bangla,english}/` (7 books each, e.g. `class_9_General_math_bn.pdf`, `class_9_Hiher_math_bn.pdf` — note: General Math is the mandatory book for all students, Higher Math is a science-group elective; used **General** for testing, flagged this assumption to the user, no objection raised).

**Major finding — PyMuPDF text extraction doesn't work at all on these files:** checked `page.get_text()` across every page of 3 different PDFs (Bangla class 9, Bangla class 6, English class 9) — **0 extractable characters on every single page**. These are 100%-scanned page-image PDFs (hence the huge file sizes, 23-106MB each), not digitally-typeset text. Confirmed this before writing any detection code, rather than guessing. This meant the literal spec instruction ("PyMuPDF দিয়ে text extract") could not work as stated — flagged to the user rather than silently pivoting.

**User chose OCR (Tesseract) as the path forward.** Installed via `winget install UB-Mannheim.TesseractOCR` (only `eng` language data ships by default). Downloaded `ben.traineddata` (best-accuracy model, from `tesseract-ocr/tessdata_best` on GitHub) and placed it in a **project-local** `backend/data/tessdata/` folder (not the default `Program Files\Tesseract-OCR\tessdata\`, which needs admin rights to write to) — `pytesseract` is pointed at this folder via `--tessdata-dir` on every call.

**OCR quality measured honestly across 3 page types before writing any parsing logic** (see "Known Issues" for the full before/after text comparisons):
- Cover/graphic page: poor — large stylized titles missed entirely.
- Plain paragraph text (chapter intro): ~95%+ accurate, very usable.
- Math-notation-heavy page (equations, set theory `∈∩∪×`, fractions): **meaningfully degraded** — fractions like `x/2 + y/3` become nonsense, `∩`→`N`, `∪`→`U`, `×`→`x`, some Bangla numerals misread (`১২`→`92`), `।` sometimes becomes `1`.

**Presented this mixed picture to the user; user chose to proceed anyway** ("এগিয়ে যাও... pdf_extractor.py বানাও... সীমাবদ্ধতা CLAUDE.md তে note করো") rather than trying alternate OCR configs first — accepting the known math-notation limitation for now.

**Built `backend/ingestion/pdf_extractor.py`:**
- `detect_language(path)` — `bangla`/`english` folder name → `bn`/`en`.
- `detect_class_number(path)` — regex on filename (`class_(\d+)`).
- `ocr_page(page, language, dpi)` — renders a PyMuPDF page to an image (default 300 DPI — tested, 200 DPI gave no meaningful speed benefit) and runs Tesseract with the right language.
- `extract_all_text(...)` — OCRs every page and concatenates into **one continuous string** (deliberately not per-page-independent — a problem/solution that spans a page break needs to stay one chunk; per-page chunking would have silently truncated those).
- Chapter regex (`অধ্যায়\s*...`), exercise regex (`অনুশীলনী\s*X\s*[.।]\s*Y`), and problem regex (`^\s*(?:উদাহরণ\s*)?<number>[.।:]\s+`, multiline) — **all three patterns were derived by actually reading real OCR'd pages first** (found live examples of `অধ্যায় ২`, `অনুশীলনী ২.২`, `উদাহরণ ১২`/`১৩`/`২৪`, and numbered practice items like `১২.`), not guessed.
- `chunk_text(...)` — merges all three marker types into one position-sorted stream, walks through it as a small state machine (current chapter/exercise context; flush the pending problem's text whenever a new problem/chapter/exercise marker appears), producing `MathChunk(class_number, chapter, exercise, language, content)` — matches the spec's exact requested shape.

**Timing discovery:** ~10 seconds/page regardless of 200 vs 300 DPI (Tesseract's own processing dominates, not image size) → a 362-page book takes ~60 minutes (actual: 48 min / 2886s).

**FULL-BOOK RESULT (`class_9_General_math_bn.pdf`, all 362 pages): 17 chapters found (1-17), 38 exercises found, 888 chunks total.** Chapters 1, 10, 15, 17 had no exercise matches — either those chapters genuinely lack an `অনুশীলনী`-labeled section or the regex missed a formatting variant there; not yet investigated further. 17 chapters is plausible for an SSC General Math book (algebra/geometry/trig/statistics coverage) — a reasonable structural result at first glance, though the *content* of chunks inherits all of Tesseract's math-notation noise (see below).

## Last Task Completed
**2026-08-10 — Feature 1 (OCR+LLM dual-output) and Feature 2 (preprocessing mode) added to the PDF pipeline:**

**`pdf_extractor.py` additions:**
- `fix_math_notation(raw_text)` — sends raw OCR text to Groq with the user's exact correction prompt, returns the "fixed" version.
- `compute_changes(raw, fixed)` — **word-level** diff (via `difflib.SequenceMatcher` on `.split()` tokens, not character-level) — produces clean `{"before": ..., "after": ...}` pairs matching the spec's example format, rather than noisy single-character fragments a raw character diff would produce.
- `save_page_outputs(...)` — writes `data/ocr_raw/page_N.txt`, `data/ocr_fixed/page_N.txt`, `data/comparison/page_N.json` (includes `changes_count`, `changes`, and `improvement_score` — defined as `changes_count / word_count`, our own formula since the spec's example number wasn't accompanied by an exact definition).
- `process_page_with_llm_fix(pdf_path, page_number)` — the one-call convenience function tying OCR → LLM-fix → save together for a single page.
- `build_summary()` — aggregates every saved `comparison/page_N.json` into `comparison/summary.json` (total pages, avg changes/page, most common corrections).

**`config.py`** — added `PREPROCESSING_MODE = True` (plain module constant, not env-driven, per the spec).

**`main.py`** — 5 new admin endpoints: `POST /api/admin/preprocess` (runs the pipeline for one page, blocked if `PREPROCESSING_MODE` is off), `GET /api/admin/comparison/{page}`, `POST /api/admin/approve/{page}` (marks approved, appends `{page, chapter, content}` to `data/approved/chunks.json` — **staging only, does not yet push to Qdrant**, see Important Decisions), `POST /api/admin/reject/{page}` (marks `manual_review_needed`), `GET /api/admin/summary`.

**Test: page 15 of `class_9_General_math_bn.pdf`** (chosen area — recurring-decimal-to-fraction conversion, math-notation-dense):
- 33 changes detected, `improvement_score = 0.1119`, `chapter: None` (page 15 in isolation has no `অধ্যায়` mention on that specific page — a single-page test can't know book-wide chapter context the way the full-book run does; expected, not a bug).
- **What the LLM actually did, honestly assessed:** it mostly (a) converted Arabic digits to Bangla digits throughout (`452346`→`৪৫২৩৪৬`) — plausible and verified digit-for-digit correct, likely fixing a real OCR confusion (the printed book almost certainly uses Bangla numerals) even though this wasn't literally one of the prompt's example fixes; and (b) cleaned up some garbled English-looking OCR noise back into real Bangla words (`WALT`→`ভগ্নাংশ`, `ATS দশমিক Wallet AAT`→`আবৃত্ত দশমিক ভগ্নাংশ বলে`). **It did NOT reconstruct the underlying broken equations into valid math** — dense calculation lines like `452346- 452 451894 22594 1172` came out as `৪৫২৩৪৬- ৪৫২ ৪৫১৮৯৪ ২২৫৯৪ ১১৭২`, same nonsensical structure, just cleaner digits. **Conclusion: the LLM-fix step is a real, measurable improvement (digit consistency + word-level cleanup) but does not make dense equation lines trustworthy — content still needs human review before being treated as ground truth**, consistent with the Mode 1 "admin manual review" step already planned in Feature 2's design.

## Last Task Completed
**2026-09-08 — RAG wired into `/api/chat` (both modes):**

`retrieval/retriever.py` built (was an empty stub): `retrieve(query, class_number, book_type, chapter, exercise, problem_number, language, top_k=3)` embeds the query (`"query: "` prefix, same `intfloat/multilingual-e5-large` model as ingestion) and searches Qdrant's `nctb_math_content` collection, filtering on `class`/`book_type`/`chapter`/`exercise`/`language` when given (only non-`None` values become filter conditions). `problem_number` is accepted in the signature per the user's exact spec but is **not** added to the filter — the spec's own filter-building step listed only the other 5 fields, so this was followed literally rather than assumed; flagged here in case that was an oversight.

`solving/solver.py`'s `solve()` gained a `mode` param plus the same retrieval fields. Reference mode retrieves with all filters; direct mode calls `retrieve(query, language=language)` only — no structural filters (true semantic search) but still scoped to the query's own language, a deliberate judgment call (the user's literal wording was "pass only query," but `retrieve()`'s own spec'd default is `language="bn"`, and skipping this would silently mis-scope English direct-mode queries). If chunks come back, their text is joined and prepended as `"নিচের NCTB পাঠ্যবই থেকে প্রাসঙ্গিক অংশ:\n{context}"` ahead of the existing SSC-format prompt; if none come back, `rag_note = "RAG context পাওয়া যায়নি"` is set instead (surfaced via a new `ChatResponse.rag_note` field) and the LLM solves from its own knowledge as before. `SolveResult` gained `retrieved_chunks` and `rag_note`; `ChatResponse` gained matching fields so retrieval is visible in the API response, not just internal.

`main.py`'s `ChatRequest` gained `book_type` (`"general"`/`"higher"`) and `problem_number`, and `exercise` was changed from `Optional[int]` to `Optional[str]` — the real chunk payloads use string exercise numbers like `"2.1"`, not ints, so the old typing would have rejected every real reference-mode request.

**Bugs found and fixed while wiring this, not part of the original ask:**
- `vector_store.search()` had no filter support at all — added a `query_filter` param that gets sent as Qdrant's `"filter"` body key.
- **Qdrant Cloud rejects filtering on any payload field without an index** (400 Bad Request: "Index required but not found"). Added `vector_store.create_payload_index()` and ran it once for `class` (integer), `book_type`/`exercise`/`language` (keyword), and `chapter` (integer) directly against the `nctb_math_content` collection — a one-time setup step, not part of the request path. Without this, every filtered search would 500.
- `retriever.py` was about to load its own second copy of the `intfloat/multilingual-e5-large` model (~2.24GB) via `fastembed.TextEmbedding`, on top of the one `glossary_engine.py` already loads eagerly at import time — on a machine already documented as RAM-constrained for this exact model. Added `glossary_engine.get_embedder()` and had `retriever.py` reuse that single instance instead of instantiating its own.

**Tested end-to-end via a live `/api/chat` call (not just unit-level):** direct-mode query `"সেট কাকে বলে"` correctly retrieved 3 relevant "সেট" (Set) chunks (top score 0.827) and the LLM's answer visibly used them ("প্রদত্ত পাঠ্যবইের অংশ থেকে..."). Reference-mode query (`class=9, book_type=general, chapter=2, exercise="2.1"`) correctly retrieved only chunks matching all four filters (verified: all 3 results had exactly `chapter=2, exercise="2.1"`).

**Blocker found, unrelated to this task — flagged, not silently fixed:** `config.py`'s production models are both dead. Groq's `llama-3.3-70b-versatile` now 404s ("does not exist or you do not have access to it") and Gemini's `gemini-2.5-flash` 404s with "no longer available to new users... use models/gemini-3.6-flash". Confirmed via each provider's live model-list: Groq currently offers `openai/gpt-oss-120b` (already the tiebreak model), `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`, `qwen/qwen3.6-27b`, `groq/compound(-mini)`, `allam-2-7b`; Gemini offers `gemini-3.6-flash`/`gemini-3.5-flash`/etc. Testing above used a **temporary, not-persisted** env-var override (`qwen/qwen3.8-27b` + `gemini-3.6-flash`) just to exercise the full pipeline — `config.py` itself was left untouched since swapping the production model is the kind of decision this project has always run past the user first (see Important Decisions). Needs a user decision before `config.py` is updated for real.

## Next Task
Awaiting user's decision on replacement Groq/Gemini model names (see blocker above) before making it permanent in `config.py`. After that: consider parallelizing the sequential Groq→Gemini→tiebreak calls (already a known perf issue, now more visible — a tiebreak-triggered reference-mode call took ~59s in testing), or move to a different feature (e.g. Feature 5). Per project rule: build one piece at a time, test it, then move on — no auto-advancing.

## Important Decisions Made
- Project root confirmed by user as `d:\Paper_project\banglamathai` (not `d:\Paper_project` directly), matching the `/banglamathai` root shown in the spec's file structure.
- Scaffolding-only on day 1: all `.py`/`.tsx` files created as empty stubs with a one-line purpose comment — no business logic, per "build one feature at a time" rule.
- `.env` created with all keys blank; real credentials will be requested only when the specific feature that needs them is being built.
- Qdrant Cloud (managed, free tier) chosen over self-hosted Qdrant — not included in `docker-compose.yml`.
- Backend dependencies are installed into a local venv (`backend/venv/`, gitignored-worthy — not yet a git repo) pinned exactly to `requirements.txt` versions, so local testing always matches the declared spec.
- ~~`reference` mode requires `chapter` + `exercise`~~ — **overturned by user**: both are optional in reference mode; class alone, class+chapter, or class+chapter+exercise must all work.
- Request/response Pydantic schemas for `/api/chat` live directly in `backend/main.py` for now rather than a separate schemas file — kept simple since it's still just structure; may extract into its own module once real solving logic is wired in.
- `class_standards.py` returns a small typed dataclass (not raw dict) with a `required_markers` list — chosen so Feature 3's solver can later validate an SSC-format LLM response by checking each marker is present in the output text.
- Added `__init__.py` to every backend subpackage (standard Python packaging practice, was missing from the original scaffold) — made as a small unasked structural fix, flagged here per rule 3.
- **Groq production model confirmed by user: `llama-3.3-70b-versatile`** (replaces the spec's `llama3-70b-8192`, which Groq has decommissioned). Chosen over `llama-3.1-8b-instant` for better math accuracy despite higher cost/latency. This name needs to land in `config.py` once that file is built out.
- Pinned `httpx==0.27.2` in `requirements.txt` — required for `groq==0.11.0` to work (newer httpx removed the `proxies` kwarg groq's SDK still uses internally).
- **Gemini production model confirmed by user: `gemini-2.5-flash`** (stable-named, not a preview build). Also needs to land in `config.py` alongside the Groq model name.
- **Tiebreak model confirmed by user: `openai/gpt-oss-120b`** (Groq-hosted, replaces spec's now-removed "Mixtral"). Chosen for architectural diversity from the Llama-family primary model.
- SSC-format prompting uses a **few-shot worked example** (copied from this spec's own Example 2) instead of a prose description of the format rules — prose alone produced inconsistent/degenerate answers in testing; the concrete example fixed it. Applies only to class 9-10; classes 6-8 still use the prose `style_description`.
- `class_standards.py`'s `required_markers` for class 9-10 includes `∴`, but the spec's own two worked examples disagree on whether `∴` is used (present in the algebra example, absent in the geometry one) — treating it as contextual per problem type, not a hard requirement, since nothing currently enforces it at runtime anyway.
- `requirements.txt`'s `pydantic` pin updated from `2.9.2` to `2.13.4` (what actually got installed and is tested-working) rather than downgrading to match the original stale pin.
- **`qdrant-client` package dropped in favor of raw REST calls via `httpx`** (user-confirmed choice) — the official SDK's hard `grpcio-tools>=7.35.1` dependency conflicts with `google-generativeai`'s `protobuf<6.0.0`; the alternative (migrating off deprecated `google-generativeai` to `google-genai`) was rejected to avoid touching already-working Feature 3 code.
- ~~Embedding model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`~~ — **superseded**: tested empirically and found badly miscalibrated for short Bangla terms (unrelated words scored higher than true synonyms). **Switched to `intfloat/multilingual-e5-large` via `fastembed`** (1024-dim, ~2.24GB, uses `"query: "`/`"passage: "` prefix convention) — user-approved after seeing the comparison data. Bigger download/RAM cost, but the smaller model was simply not usable for this domain — this wasn't a preference call, the small model's rankings were empirically wrong.
- Tier-3-learned glossary terms get UUID string point IDs in Qdrant (not integers) — the seed data uses integer IDs 0-50, so UUIDs guarantee no collision without needing to track/query a running counter.
- Tier-3-learned terms are stored with `payload.approved = False` but nothing currently filters on it — Tier 2 search will happily return an unapproved term. This is fine for now (no code path enforces approval yet) but will need addressing once Feature 20 (Admin Panel) exists.
- Used the **General Math** book (not Higher Math) for `class_9`/`class_10` PDF testing, since General Math is mandatory for all students and this project targets all Class 6-10 students, not just the science-group elective track. Flagged to user, no objection.
- **OCR (Tesseract) chosen over cloud vision APIs for PDF text extraction** — free, local, no per-page quota (unlike Gemini, which is already quota-constrained at 20/day). Accepted the measured math-notation accuracy tradeoff (see Known Issues) rather than pursuing a cloud-vision alternative — user's explicit choice after seeing the comparison data.
- `pdf_extractor.py` concatenates a whole book's OCR'd pages into one continuous string before chunking, rather than chunking per-page — deliberate, so a problem/solution that spans a page break isn't silently cut off.
- **`compute_changes()` diffs raw vs. LLM-fixed text word-by-word, not character-by-character** — a char-level diff would fragment every change into tiny unreadable pieces; word-level matches the spec's example `{"before": "x2", "after": "x²"}` format.
- **`/api/admin/approve/{page}` only stages into `data/approved/chunks.json`** — it does not push to Qdrant yet. The spec's file-structure comment (`chunks.json ← Qdrant এ যাবে`) reads as "will go to Qdrant" (future), so this was treated as a two-step process rather than one endpoint doing both; actually wiring `chunks.json` → Qdrant's `nctb_content` collection is left as a follow-up, not done in this turn.

## Known Issues & Bugs
- On this Windows/Git-Bash setup, the PID uvicorn logs ("Started server process [PID]") does not match the actual OS-level owning PID for the port — `bash kill <pid>` fails silently claiming "No such process" even though the server is still up. Workaround: use PowerShell `Get-NetTCPConnection -LocalPort <port> | Stop-Process`. Noting this so future test-server cleanups don't get skipped by mistake.
- **Testing gotcha (not an app bug): Windows `curl.exe` mangles inline Bangla text.** `curl -d '{"query": "বাংলা টেক্সট..."}'` on this machine (Git Bash + Windows curl) silently corrupts UTF-8 multi-byte characters into `?` before the request is even sent — confirmed by echoing the received query back from the server. Any future manual API testing with Bangla content MUST write the JSON body to a file first and send it with `curl --data-binary @file.json`, never inline `-d '...'` with non-ASCII text.
- Gemini free tier is quite limited: `gemini-2.5-flash` free tier = **20 requests/day** (not per-minute — per DAY). Heavy manual testing can exhaust it fast, after which `/api/chat` will correctly fall back to Groq-only (`confidence=SINGLE_SOURCE`) rather than fail, but cross-verification stops happening until the quota resets. Worth keeping in mind when demoing or testing multiple times in one day.
- `cross_check()` calls Groq then Gemini sequentially (not concurrently), and calls the tiebreak model sequentially after that on mismatch — so a full cross-checked answer can take several seconds (worse on tiebreak). Not addressed yet; could parallelize with `asyncio`/threads later if latency becomes a problem.
- `fastembed` downloads its embedding model (~220MB) from Hugging Face on first use and caches it in `%TEMP%\fastembed_cache`; on this Windows dev machine it printed harmless warnings (no symlink support without Developer Mode/admin, mean-pooling vs CLS embedding note). Neither affects correctness — just noise on first run. First embedding call takes longer (~20s download); subsequent calls are fast (cached).
- **All NCTB PDFs in `backend/data/pdfs/` are scanned page images with zero embedded text** (verified across 3 different books, every page, `page.get_text()` always returned an empty string). File sizes (23-106MB per book) are consistent with this — they're image scans, not typeset documents. `PyMuPDF` alone cannot extract anything from them; OCR is mandatory.
- **OCR (Tesseract, `ben` best-accuracy model) quality is good on plain paragraph text but meaningfully degrades on math notation.** Measured examples from a real exercise page (class 9 General Math, Chapter 2):
  | Actual | OCR got |
  |---|---|
  | `3x = 9 বা x = 3` | `32 ₹- 9 Wax =3` |
  | `A = {সাদা, নীল}` | `A= (সাদা, নীল]` |
  | `x/2 + y/3, 1) = (1, x/3 + y/4)` | `(5 +2, 1) = (1 +4 4)` |
  | `R = P∩Q` | `R= PNQ` |
  | `উদাহরণ ১২` | `উদাহরণ 92` |

  Plain prose (chapter intros, objective lists) came through at ~95%+ accuracy. **Any downstream feature that consumes `pdf_extractor.py`'s chunks (e.g. RAG retrieval for "reference mode") should not treat the extracted math notation as ground truth without a human review step** — the text content is a reasonable starting point/context, not a reliable source of exact equations yet.
- Tesseract's Bengali language file (`ben.traineddata`) lives in a **project-local** `backend/data/tessdata/` folder, not the default `C:\Program Files\Tesseract-OCR\tessdata\` (which needs admin rights to write to). Every `pytesseract` call must pass `--tessdata-dir` pointing at the local folder — `ingestion/pdf_extractor.py` does this via its `TESSDATA_DIR` constant. If Tesseract or this OCR pipeline is ever run from a different machine, this data folder needs to travel with the repo (or be re-downloaded) and Tesseract itself needs a fresh `winget install UB-Mannheim.TesseractOCR`.
- OCR is slow: ~10 seconds/page regardless of 200 vs 300 DPI (bottleneck is Tesseract's own processing, not image resolution) — a 362-page book takes about an hour. This will matter a lot once all 14 PDFs (7 subjects × 2 languages) need processing; worth considering parallelization (multiple pages at once) before doing a full production ingestion run.

## API Keys Status
- GROQ_API_KEY — ✅ provided by user in `backend/.env` (2026-08-09), connection tested and working
- GEMINI_API_KEY — ✅ provided by user in `backend/.env` (2026-08-09), connection tested and working
- QDRANT_URL / QDRANT_API_KEY — ✅ provided by user in `backend/.env` (2026-08-10), connection tested and working (raw REST, not the qdrant-client SDK)
- POSTGRES_URL — not provided
- REDIS_URL — not provided
- JWT_SECRET — not provided
- ADMIN_PASSWORD — not provided
- SMTP_EMAIL / SMTP_PASSWORD — not provided

## Database Schema (current)
Not yet implemented. Planned (from spec, to be created via Alembic migrations when backend work starts):

**PostgreSQL:** users, sessions, queries, progress, glossary_terms, achievements
**Qdrant collections:** nctb_content, math_glossary, solution_styles
**Redis:** session cache, rate limiting, LLM response cache

## Deployment Notes
- `docker-compose.yml` created (backend, frontend, postgres, redis, celery_worker, nginx) — template only, not built or tested yet.
- `nginx.conf` created as reverse proxy template (HTTP now, HTTPS block commented out pending SSL setup) — not tested yet.
- **New system-level dependency: Tesseract OCR engine** (not installable via pip) — the production Docker image / VPS will need `tesseract-ocr` + Bengali language data installed at the OS level (e.g. `apt-get install tesseract-ocr tesseract-ocr-ben` on Debian/Ubuntu, which is simpler than this Windows dev setup's manual `winget` + `tessdata_best` download dance). Not yet added to `backend/Dockerfile` (doesn't exist yet) or `docker-compose.yml`.
- Target deployment: Hostinger VPS.

## Performance Notes
- `/api/chat` latency is currently dominated by sequential LLM calls: Groq + Gemini always, plus a third Groq call (tiebreak model) whenever the first two disagree. No caching, no concurrency yet. Fine for manual testing; will need attention (parallel calls, Redis response caching per the original architecture) before real user load.
