# Day 5 Summary — CER, error-class breakdown, Groq edit audit

Scope: the 3 **verified** Bangla pages only (`bn_page_30`, `bn_page_36`, `bn_page_44`) — English pages (`en_page_30`, `en_page_38`) still have no ground truth (Gemini quota not yet reset as of Day 3/4), so they are excluded from every table below, per DAY5.md's own scope note.

Nothing under `backend/`, `frontend/`, or `paper/ground_truth/*.txt` was modified — all three are read-only inputs here.

## Task A — CER table (methods × pages + mean)

Methods: **M1** = Tesseract raw (`comparison/bn_page_N.json["raw"]`), **M1b** = Tesseract raw from the separate `ocr_raw/class_9_General_math_bn/` run (cross-check only, not averaged with M1), **M2** = Tesseract + Groq fix (`comparison/bn_page_N.json["fixed"]`), **M3** = Gemini Vision (`gemini_vision/bn_page_N.txt`, the raw Gemini output — not the ground truth, which Peal hand-edited from a copy of it).

CER = Levenshtein edit distance / len(ref), on NFC-normalised text with **all whitespace removed** (primary). `CER_with_spaces` collapses whitespace to single spaces instead, as a sensitivity check. Full per-page S/I/D counts are in `paper/results/day5_cer.csv`.

| Page | Method | ref chars | CER | CER (with spaces) |
|---|---|---|---|---|
| 30 | M1 Tesseract raw | 1379 | 7.98% | 10.32% |
| 30 | M1b Tesseract raw (alt run) | 1379 | 9.43% | 11.54% |
| 30 | M2 Tesseract+Groq fixed | 1379 | 6.53% | 9.43% |
| 30 | M3 Gemini Vision | 1379 | 0.07% | 0.06% |
| 36 | M1 Tesseract raw | 916 | 13.43% | 19.00% |
| 36 | M1b Tesseract raw (alt run) | 916 | 12.34% | 18.45% |
| 36 | M2 Tesseract+Groq fixed | 916 | 10.48% | 12.17% |
| 36 | M3 Gemini Vision | 916 | 0.11% | 0.08% |
| 44 | M1 Tesseract raw | 978 | 13.09% | 16.79% |
| 44 | M1b Tesseract raw (alt run) | 978 | 11.66% | 15.74% |
| 44 | M2 Tesseract+Groq fixed | 978 | 9.10% | 8.85% |
| 44 | M3 Gemini Vision | 978 | 0.61% | 0.52% |
| **MEAN (micro)** | **M1 Tesseract raw** | 3273 | **11.03%** | **14.79%** |
| **MEAN (micro)** | **M1b Tesseract raw (alt run)** | 3273 | **10.91%** | **14.81%** |
| **MEAN (micro)** | **M2 Tesseract+Groq fixed** | 3273 | **8.40%** | **10.04%** |
| **MEAN (micro)** | **M3 Gemini Vision** | 3273 | **0.24%** | **0.20%** |

Mean = micro-average (total edits ÷ total ref chars across all 3 pages, not an average of the 3 per-page percentages).

**Headline**: Gemini Vision's raw output is already ~46x closer to the hand-verified ground truth than raw Tesseract (0.24% vs 11.03% CER), and the Groq LLM correction step measurably helps Tesseract (11.03% → 8.40%, a relative ~24% reduction) without fully closing the gap. M1 and M1b (two independent Tesseract runs on the same pages) land within ~0.1pp of each other — a useful cross-check that the ~11% raw-Tesseract CER isn't a one-run fluke.

## Task B — error breakdown by character class (all 3 pages combined)

Alignment: `difflib.SequenceMatcher` on characters (ref vs hyp), no-whitespace normalisation (same primary variant as Task A). `error_rate` = errors ÷ how many reference characters fall in that class. Insertions (extra hyp characters with no ref counterpart) are tallied separately per method, not attributed to any class — see `paper/results/day5_error_by_class.csv` for the full method×page breakdown.

| Class | ref count | M1 raw | M1b raw (alt) | M2 fixed | M3 Gemini |
|---|---|---|---|---|---|
| Bangla letter/vowel sign | 1836 | 0.98% | 1.58% | 1.47% | 0.11% |
| Bangla digit (০-৯) | 34 | 32.35% | 41.18% | 32.35% | 14.71% |
| Latin letter | 296 | 32.77% | 27.03% | 18.92% | 0.00% |
| ASCII digit | 291 | 0.69% | 0.69% | 2.41% | 0.00% |
| Math symbol (∈∉∪∩∅∴⊂⊆×−≤≥±′\ + superscripts) | 99 | 98.99% | 98.99% | 66.67% | 0.00% |
| Bracket/other punctuation | 717 | 14.92% | 12.55% | 7.53% | 0.00% |
| *(insertions, no ref class)* | — | 17 | 18 | 25 | 1 |

**Headline**: this is the sharpest, most paper-worthy finding of the day — **math symbols are where Tesseract fails almost completely** (98.99% error rate: it gets a math symbol right only ~1 time in 100), consistent with CLAUDE.md's previously-documented qualitative observation (`∩`→`N`, `∪`→`U`, fractions garbled). The Groq LLM-fix step cuts that from 98.99% to 66.67% — a real improvement, but still wrong 2 times in 3. Bangla digits are the second-worst class for Tesseract (32-41%), and the Groq fix does *not* improve them at all here (32.35% both before and after — the fix's own prompt example list includes digit-adjacent rules but apparently didn't fire for these specific pages' digit errors). Gemini is near-perfect on every class except Bangla digits (14.71% — its one remaining weak spot on these 3 pages, worth a sentence in the paper).

## Task C — Groq edit audit (89 edits across the 3 pages)

| Label | Count |
|---|---|
| fixed | 2 |
| harmful | 0 |
| neutral/unclear | 87 |

Full per-edit detail (before, after, label, note) in `paper/results/day5_edit_audit.csv`.

**Method, and a real bug found and fixed while building it:** each edit's position was recovered by re-running the exact `difflib.SequenceMatcher(None, raw_words, fixed_words)` call that originally produced the stored `"changes"` list (verified byte-for-byte reproducible for all 3 pages before trusting it), then separately aligning `raw_words→gt_words` and `fixed_words→gt_words` to find "what the ground truth says at that place" for `before` and `after` independently. The first version of this did **not** bound how large that aligned "place" could be, and it produced 8 "harmful" labels that turned out to be alignment artifacts, not real regressions: a tiny 1-2 word edit sitting near other, unrelated OCR noise would get folded into one huge difflib opcode, and the unioned ground-truth snippet handed back could be 5-10 words long — comparing a 1-word `after` against an unrelated 5-word snippet always "fails," which the original logic mistakenly treated as evidence of a regression. Manually inspecting those 8 rows confirmed every one was this artifact (e.g. `before='গুণিতক }'→ after='গুণিতক}'`, correct, but compared against an unrelated 5-word snippet). Fixed in two steps: (1) reject any aligned snippet longer than `max(edit_word_count + 2, 4)` words as unreliable, and (2) require **both** the before-side and after-side snippets to be reliable before attempting a `fixed`/`harmful` verdict at all — otherwise label `neutral/unclear`. This is the literal implementation of DAY5.md's "when uncertain choose unclear, never guess fixed" rule, extended to `harmful` for the same reason (a false "harmful" would be just as misleading in the paper as a false "fixed").

**Honest reading of the result:** with that conservative confidence gate, only 4 of 89 edits (4.5%) could be confidently localised in the ground truth at all — 2 fixed, 0 harmful, 2 that resolved to "neither side matches" (counted under unclear). The other 85 are small 1-3 word fragments (digits, brackets, single Bangla words) that recur often enough on a dense math page that word-level alignment to an independently-hand-typed ground truth can't localise them with confidence. This is a real limitation of the method, not evidence that the other 85 edits were neutral in effect — **Peal's requested 10-row spot-check by eye is the right next step** to judge whether the "unclear" bucket is hiding more true fixes/harms than this conservative method can see, or whether 4.5% confidently-resolvable really is the ceiling for this alignment approach at this edit granularity.

## 5 concrete example errors per method (ref vs hyp)

### M1 — Tesseract raw
- GT `B` → got `7` (page 30 — single Bangla capital-letter-context OCR'd as a digit)
- GT `∴ B,` → got `... 3,` (page 30 — `∴` symbol lost entirely, read as three dots)
- GT `B ⊂` → got `BC` (page 30 — subset symbol `⊂` merged into the preceding letter)
- GT `−` → got `—` (page 36 — minus sign read as a long dash)
- GT `(2, 4), (2,` → got `(2,4), (2,6), (3, 2), (3, 4), (3,6), (5, 2), (5, 4), (5, 6)) 7 {(3, 2), (3, 4), (3,` (page 44 — a long ordered-pair set badly over- and under-segmented)

### M1b — Tesseract raw (alternate run)
- GT `সেট।` → got `সেট ।` (page 30 — spurious space before the sentence-ending দাঁড়ি)
- GT `B` → got `` (page 30 — letter dropped entirely)
- GT `F = উভয় বিষয়ে` → got `17 = উভয় বিষয়ে` (page 36 — `F` misread as `17`)
- GT `{(2, 2), (2,` → got `{(2,2), (2,4), (2,6), (3, 2), (3,4), (3, 6), (5, 2), (5,4), (5,6)) 1 {(3, 2), (3,` (page 44 — same kind of set-notation run-on as M1)
- GT `(2,` → got `(3,` (page 44 — a single digit substitution inside a coordinate pair)

### M2 — Tesseract + Groq fix
- GT `B` → got `৭` (page 30 — still wrong, but now a *Bangla* digit instead of an Arabic one — the fix "corrected the script" without correcting the content)
- GT `B,` → got `3,` (page 30 — same underlying error surviving the fix)
- GT `∩` → got `7` (page 44 — intersection symbol still unrecovered)
- GT `……` → got `-` (page 44 — a dotted-line/ellipsis notation collapsed to a hyphen)
- GT `অধ্যায় ২.` → got `২০২৬ অধ্যায় ২,` (page 44 — a stray `২০২৬` (year) token from the page footer leaking into the chapter heading, carried over unfixed from raw)

### M3 — Gemini Vision
- GT `৯ম-১০ম` → got `৯মে-১০ম` (page 30 — one stray extra syllable `মে` inserted into "9th-10th")
- GT `২০২৬` → got `২০২৩` (page 36 — single Bangla-digit substitution, `৬`→`৩`, in the footer year)
- GT `নিশ্ছেদ` → got `নিচ্ছেদ` (page 44 — one conjunct consonant misread, `শ্ছ`→`চ্ছ`; happens twice on this page)
- GT `২০২৬` → got `` (page 44 — the same footer year token dropped entirely on this page, inconsistent with page 36's behaviour)
- (Gemini had only 3 total character-level S/I/D errors across all of page 30, 1 on page 36, and 6 on page 44 — these 4 are close to the *complete* list of its mistakes on these 3 pages, not a cherry-picked sample.)

## Files produced
```
paper/scripts/day5_cer.py
paper/scripts/day5_error_by_class.py
paper/scripts/day5_edit_audit.py
paper/results/day5_cer.csv
paper/results/day5_error_by_class.csv
paper/results/day5_edit_audit.csv
paper/results/DAY5_SUMMARY.md   (this file)
```

## Housekeeping done this session (not part of DAY5.md, done on Peal's direct request)
`paper/ground_truth/bn_page_44_DRAFT.txt` was confirmed byte-identical to the verified `bn_page_44.txt` (via `diff`, exit code 0 / no output) and deleted as a stray leftover file.
