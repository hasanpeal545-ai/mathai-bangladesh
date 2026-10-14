# Paper progress (single source of truth — Claude chat updates this after every check)

## Ground truth (hand-verified by Peal, used for CER)
| page file | book | printed page | type | draft started from | verified |
|---|---|---|---|---|---|
| bn_page_30.txt | class_9_General_math_bn | 25 | definitions + examples | Gemini | yes (2026-10-06) |
| bn_page_36.txt | class_9_General_math_bn | 31 | exercise 2.1 | Gemini | yes (2026-10-06) |
| bn_page_44.txt | class_9_General_math_bn | 39 | worked example | Gemini | yes (2026-10-06) |

## Results so far
- Day 1: 1,024 Groq edits on Ch.2 (results/DAY1_SUMMARY.md)
- Day 5: CER on 3 bn pages — Tesseract 11.03%, Tesseract+Groq 8.40%, Gemini 0.24% (results/DAY5_SUMMARY.md)

## Full Gemini OCR — page-by-page check (Claude compares image vs text)
- Log of every checked page: check/PAGES_CHECKED.csv
- Log of every error found: check/ERRORS_LOG.csv
- Running totals (2026-10-08): class_9_General_math_bn p1-20 checked & fixed. Finding: recurring-decimal overdots — Flash-Lite drops them without explicit prompt; with prompt it misplaces many (also gemini-3.6-flash). Claude fixed p11,14-20 by hand (list: check/MANUAL_PAGES.txt). Manual full transcriptions: p9, p17 (RECITATION), p18, p20 (dots). Spend $0.092 of $7.

## Paper draft
- draft/main.tex — v0.2 (Day 1 + Day 5 results). Updated after each finished book and after each new ground-truth page.

## Decision 2026-10-08 — arXiv v1 = class 9-10 only
- v1 covers the 4 class-9/10 books only: class_9_General_math_bn, class_9_General_math_en, class_9_Hiher_math_bn, class_9_Higher_math_en (every page checked by Claude).
- After those 4: stop OCR -> exercise/example split -> tutor -> tutor test -> paper -> arXiv v1.
- Class 6-8 books come after v1 is submitted -> arXiv v2 (same link).
- Find an arXiv cs.CL endorser early.

## Workflow phases
ক OCR measurement ✅ · খ Full Gemini OCR (batches of 10, every page checked) ⬅ · গ more ground-truth pages · ঘ split exercises/examples · ঙ rebuild Qdrant + dropdown + explanations · চ tutor test (old vs new) · ছ deploy · জ paper + arXiv + GitHub · ঝ KAUST

## Running totals (2026-10-14)
- class_9_General_math_bn p1-150 checked & fixed (batch 1-15). Spend $0.5864 / $7. Next: batch 16 (p151-160) via tasks/FIX_BATCH15.md.
- Batch 13 (2026-10-14): 8 of 10 pages needed fixes, 2 clean (p122, p126); no RECITATION. New findings 19-22 (post-process bug বিন্দুইটি, prompt example R̸ leak, synonym despite prompt, angle sign + figure labels). Split-page escalation recovered p117/119/120 in a standalone test.
- Handoff for a new Claude chat: check/HANDOFF_FOR_NEW_CHAT.md
- Batch 14 (2026-10-14): 8 of 10 pages fixed, 2 clean (p132, p140); no RECITATION. Findings 23-25 (নির্বচন->নির্বাচন, figure-only MCQ data, ∠ loss lower). Claude Code also found+fixed 2 more prefix-regex bugs (_DBIMATO_RE, _SONKHYAK_RE).
- Batch 15 (2026-10-14): chapter 7 (construction geometry). 9 of 10 pages fixed, p141 clean; p148, p150 hand-rewritten (ASCII-art figures, column interleave). Findings 26-28.
