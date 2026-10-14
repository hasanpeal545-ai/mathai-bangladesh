# OCR findings for the paper (running list — Claude chat updates after every batch)

Source data: check/ERRORS_LOG.csv (every error, with batch/page/line), check/PAGES_CHECKED.csv (every checked page), check/MANUAL_PAGES.txt (hand-corrected pages). Model: gemini-3.5-flash-lite, thinkingLevel minimal, double reading (temp 0 + 0.4) for bn.

## Headline numbers so far (class_9_General_math_bn, p1-130)
- Ground-truth CER (Peal-verified pages): p30 primary 5.15% / alt 0.36%; p36 1.86% / 1.86%. (Day 5: Tesseract 11.03%, +Groq 8.40%, gemini-3.6-flash 0.24% on 3 pages.)
- RECITATION blocks: p9, p17, p23 (all 5 attempts) -> manual transcription; p19 recovered by gemini-3.6-flash escalation; p33 recovered by temp-0.4 retry.
- Total spend at p80: ~$0.35. Batches 6-8: 3-4 of 10 pages error-free each (pipeline improving).
- p72 RECITATION recovered by escalation ladder.

## Error categories (each = a paper finding)
1. Recurring-decimal overdots (ch.1): dropped entirely without explicit prompt; with prompt, frequently placed on wrong digits (also gemini-3.6-flash). p11-25. Meaning-changing; CER barely registers it.
2. Bangla digit confusion: ৪↔৮ (Venn birth year p29, page no. p45, question no. p47), ৬↔৫ (p69), ৩৩৫ vs ৩৪৫ (TOC p5, caught by double reading). Latin digits for Bangla (p49 "88") and the reverse: Latin 36/72 rendered as Bangla ৩৬/৭২ (p78). Latin 8→4 inside a কাজ question (p73).
3. Fraction structure: stacked fractions (p10, p12, p75 even after prompt fix), mixed numbers flattened (2 4/5→24/5 p8; 3 2/9→32/9 exercise p24), lost parentheses ((28−2)/90→28−2/90 p20; (a+b)²+(a−b)²/2 p49; 3bc denominators p59), fraction coefficients ambiguous (1/2x², 1/27(3a+1), f(−1/2 a) p63, p67).
4. Symbol meaning: negation slash dropped x R̸ y → xRy (p38, meaning inverted); ⊆ vs ⊂ (p38).
5. Script leaks inside Bangla words: Devanagari (p26), Assamese ৰ (p39), Cyrillic "ке" (p60), Odia ଷ (p76) — visually identical, breaks search/retrieval.
6. Model token leak: "<bos>" in footer (p22, p30).
7. LaTeX leftovers despite "no LaTeX" prompt: \dots \sqrt \dot \frac \setminus \text \tabular \underline \because Q_0 \% etc.
8. Bangla spelling/orthography: বীজগণিতিক vs বীজগাণিতিক (systematic, ch.3), দুটি vs দুইটি, doubled letters (উউদাহরণ, মমন্তব্য, উদাাহরণ).
9. Margin artefacts: rotated year digits leaking into text (p41).
10. Figures/diagrams not transcribed (Venn diagrams, flowchart p8, graphs).

## Method findings
- Double reading (temp 0 + 0.4) catches digit errors AND lets us pick the better reading (p30: 5.15% vs 0.36%).
- Cheap escalation ladder recovers some RECITATION pages; ~3/70 pages still need manual transcription.
- Character-level CER underestimates harm: structural/meaning errors (dots, parentheses, negation) are invisible to CER — argue for a "math-semantic error" metric.
- Exercise pages are highest-stakes (tutor answers them) — errors there found on p24, p47, p59.

11. Exponent/superscript structure (ch.4, p81-90): Flash-Lite falls back to LaTeX ^{...}, detaches exponents from bases ((aᵖ)^(q−r) -> "(aᵖ) q⁻r"), splits stacked exponents into separate lines (p85 unusable), and outputs whole exercise pages as \dfrac LaTeX (p86). Every page in batch 9 needed fixing — notation density predicts error rate.
12. Subscript letters read as Greek: log_b -> logᵪ (chi) / logᵦ (beta) (p88, p89) — changes the log base. Also math-italic 𝑞 (U+1D45E) instead of q.
13. ৪->৮ confusion now hits structural numbers too: উদাহরণ ৪ -> ৮ (p84), অধ্যায় ৪ -> ৮ (p90).
14. Exercise-header digit errors break the tutor's navigation: "অনুশীলনী ৪.২/৪.৩" read as "৮.২/৮.৩" (p91, p96) — the dropdown keys on these.
15. Overbar lost on negative characteristic: 2̅ -> 2 in an MCQ option (p97), making two options identical.
16. RECITATION rate rising: p92, p98 (book's chapter openings / prose-heavy pages) blocked on all 5 attempts. Running total manual transcriptions: p9, 17, 23, 92, 98.
17. RECITATION blocking concentrates on prose-heavy pages (chapter openings, geometry axioms): p117, 119, 120 (3 of 10 in batch 12). Total fully-blocked pages so far: 10 of 120 (p9, 17, 23, 92, 98, 102, 117, 119, 120 + earlier). These were hand-transcribed.
18. Gemini "normalises" the book's own wording (বহুদ্বয়ের -> বাহুদ্বয়ের p114; দ্বিবিভক্ত -> দ্বিখণ্ডিত p116) — a faithfulness error, not a recognition error.
19. Our own post-processing can corrupt correct text: the "দুটি -> দুইটি" regex (FIX_BATCH5) has no word boundary, so the correct word বিন্দুটি became বিন্দুইটি (p123, p124 — raw Gemini output was right). Rule-based cleanup needs its own audit; every auto-fix rule is a potential error source.
20. Prompt examples leak into output: the prompt says "keep negation slashes (e.g. x R̸ y, ∉, ≠)"; on p129 the book's ≠ (AB = AC ≠ BC) came out as R̸ — the model copied the example symbol. Few-shot hints in an OCR prompt can introduce the very errors they try to prevent.
21. The anti-synonym prompt line (FIX_BATCH12) did not stop substitution: নির্দিষ্ট করে -> নির্দেশ করে (p121, batch 13, first batch with the new line). Faithfulness errors persist even under an explicit instruction.
22. Geometry chapters (ch.6, p121-130): the angle sign is dropped (∠POQ -> POQ, 3x on p123, which turns an angle into a bare list of points), and figure labels (A, B, C, 1, 2, x, 40⁰ …) leak as one-letter text lines (p123, p128, p130: ~30 lines on p130). No RECITATION in batch 13 (0/10 pages), versus 3/10 in batch 12.
- Split-page escalation (FIX_BATCH12): reading the page as top/bottom halves recovered all 3 pages (p117, 119, 120) that had been blocked on all 5 full-page attempts. Method finding: RECITATION blocking is length/page-level; halving the input avoids it.
23. Rare-term normalisation (faithfulness): the geometry term বিশেষ নির্বচন ("particular enunciation") was output as বিশেষ নির্বাচন ("election") on all 3 occurrences in batch 14 (p131, 133, 134) — the model swaps a rare word for a frequent look-alike, changing the meaning. Same family as 18/21; explicit anti-synonym prompt does not prevent it.
24. Figure-dependent exercises lose their data: MCQ answers depend on numbers printed only inside the figure (p137 Q2: 30°, 40°; p139 Q3-4: 120°, 150°). Text-only OCR makes these questions unanswerable for the tutor; we add a bracketed, clearly-labelled figure note ("[চিত্র (Claude দ্বারা বর্ণিত): …]"). A text-only RAG tutor needs a figure-description step for geometry.
25. Angle-sign loss persists after adding ∠ to the prompt (p136 ∠ADC = ACD), but at a lower rate (1 occurrence in batch 14 vs 3 on one page in batch 13).
26. Construction-geometry pages (ch.7, p141-150) bring new layout failures: the model DRAWS figures as ASCII art (lines of `_ - | / *`) mixed into the text (p147, p150), and interleaves a text column with figure labels (p148). Both p148 and p150 had to be hand-rewritten. Figure-heavy layout, not language, now drives the error rate.
27. Page-number ৪->৮ confusion is now the most frequent single digit error: 4 of 10 headers in batch 15 (p145 ১৪০->১৮০, p147, p149, p150); one more header lost its page number entirely (p144). The QC flag caught 2 of the 4.
28. New leak types: Latin letters inside a Bangla word (নিম্নে -> "নিমne", p149) and Markdown bold (`**সম্পাদ্য ৪.**`, p150). Meaning-changing word errors continue: সন্নিহিত -> সংহিত, কোণটি ("the angle") -> কোনটি ("which one") (p150), উদ্দিষ্ট -> নির্দিষ্ট (p146).
29. Spelling-variant normalisation: the book itself mixes variant spellings (উপর/ওপর, দেয়া/দেওয়া, নিম্নের/নিচের), and the model silently rewrites them toward one form (p154, 155, 158, 159; 8 instances in batch 16). These can't be fixed by rule because the book is inconsistent — a faithfulness error that only page-image comparison catches.
30. New symbol/digit failures: the angle sign rendered as a slash (`/ABC` for ∠ABC, 3x on p154); Bangla ৪ read as Latin 8 in a structural number (উদাহরণ 8. for উদাহরণ ৪., p153); 2-column MCQ options read column-wise (ক, গ, খ, ঘ, p154).
31. Pipeline maturity: batch 16 needed no hand-rewrite (0/10) and no RECITATION, and the ৪↔৮ page-number auto-fix fired correctly on p154; remaining errors are mostly word-level faithfulness errors.
32. Rule interference: a post-processing rule added for one failure (ASCII-art figures, FIX_BATCH15) silently deleted correct content of another kind — the rows of a Markdown table (`| ১ | | | |`) on p166. Second instance (after finding 19) of our own cleanup rules corrupting correct OCR; each new rule needs a regression check against all earlier page types, not just the pages it was written for.
33. Figure labels placed to the RIGHT of text on the same line (p168: "… AB = 3        D") are not caught by line-based label stripping; the ASCII-art circle figure on the same page also survived because its lines were mostly letters and spaces.
34. Punctuation look-alikes: Bangla visarga ঃ used for colon (মন্তব্যঃ, রয়েছেঃ — p168) and দাঁড়ি for period in exercise numbers (p167) — visually near-identical, but break heading detection.
35. Unicode normalisation silently disables cleanup rules: Bangla য় can be one code point (U+09DF) or two (U+09AF+U+09BC). Our rule for লক্ষনীয় was written in the 2-code-point form, the model output the 1-code-point form, so the rule never fired (p174). Text and rules must be normalised to one form (NFC) before matching — otherwise rule coverage is lower than tests suggest.
36. Rule over-generalisation vs. book inconsistency: the book usually prints দুইটি but sometimes দুটি (p178). Our global দুটি→দুইটি rule made a faithful reading unfaithful. Rules derived from "the book always writes X" need per-instance verification.
37. New script leak: Malayalam ര് + ZWJ inside a Bangla word (অন্তര്‍লিখিত, p175), plus Assamese ৰ again (p176). Page-number digit confusion ৭→৯ on 3 consecutive headers (p175-177: ১৭০→১৯০ …), a different pair from the ৪↔৮ case the auto-fix handles. The model also "corrected" a genuine typo in the book (স্পর্শ → স্পর্শক, p177) — faithfulness cuts both ways.
