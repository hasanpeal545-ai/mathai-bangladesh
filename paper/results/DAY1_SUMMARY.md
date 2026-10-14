# Day 1 — Chapter 2 LLM OCR-correction statistics

Source: backend/data/comparison/{bn,en}_page_*.json (Class 9-10 General Math, Ch. 2 "Set and Function")
Script: paper/scripts/day1_correction_stats.py

| | Bangla | English | Total |
|---|---|---|---|
| Pages | 22 (p26-47) | 23 (p27-49) | 45 |
| Raw OCR characters | 29,615 | 30,906 | 60,521 |
| LLM corrections | 557 | 467 | 1,024 |
| Corrections / page | 25.3 | 20.3 | 22.8 |
| Mean improvement_score | 0.099 | 0.078 | — |

## Corrections by category (heuristic, auto-classified)
| Category | bn | en | total | % |
|---|---|---|---|---|
| Math symbol (∈ ∉ ∪ ∩ ∴ × −) | 172 | 182 | 354 | 34.6 |
| Other (word / mixed) | 194 | 94 | 288 | 28.1 |
| Punctuation / spacing | 47 | 80 | 127 | 12.4 |
| Superscript / exponent | 46 | 79 | 125 | 12.2 |
| Bracket / set notation | 43 | 16 | 59 | 5.8 |
| Bangla↔Latin digit swap | 43 | 0 | 43 | 4.2 |
| Deletion (noise removed) | 12 | 16 | 28 | 2.7 |

## Observations for the paper (need verification against ground truth, Day 3-5)
- Math notation (symbols + superscripts + set brackets) = 52.6% of all corrections -> Tesseract's main failure is math, not Bangla words.
- Bangla↔Latin digit confusion appears only in Bangla pages (৫ vs x, ৮ vs 8) -> mixed-script problem specific to Bangla math books.
- Some LLM "corrections" look WRONG: deleting real text ("সেটের উপাদান সংখ্যা" -> ""), "দুই" -> "2টি", "7" -> "৭" where the book shows a set name, "1" -> "¹". So corrections are candidates, not ground truth; the paper should report how many corrections were correct vs harmful.
- Even after correction many errors remain (e.g. "(2,%,2]" stays) -> correction is partial.
- Data bugs: `chapter` field is None in 22 of 45 files; page_15.json is a stray test file.
