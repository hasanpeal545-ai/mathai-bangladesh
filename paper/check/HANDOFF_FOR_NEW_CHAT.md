# HANDOFF — নতুন Claude chat এর জন্য (লেখা: 2026-10-14)

নতুন chat: এই ফাইলটা পুরো পড়ো, তারপর PROGRESS.md, results/OCR_FINDINGS_FOR_PAPER.md, check/CURRENT_BATCH.md, সর্বশেষ tasks/FIX_BATCH*.md।

## অবস্থা
- arXiv v1 = শুধু class 9-10 এর ৪টা বই (General bn/en, Higher bn/en)। class 6-8 → v2।
- class_9_General_math_bn: পৃষ্ঠা 1-130 OCR + Claude (chat) দ্বারা প্রতি পৃষ্ঠা ছবির সাথে মিলিয়ে চেক ও ঠিক করা শেষ (batch 1-13)। বইয়ে মোট ৩৬২ পৃষ্ঠা।
- পরের ধাপ: Peal Claude Code (VS Code) এ tasks/FIX_BATCH13.md চালাবে → batch 14 = পৃষ্ঠা 131-140 → "Batch ready" → Claude (chat) চেক করবে।
- খরচ: ~$0.5271 / $7.00 (budget stop $7)।
- FIX_BATCH12 এর ফল: split page escalation p117/119/120 তিনটাই উদ্ধার করেছে (standalone test)। batch 13 এ কোনো RECITATION হয়নি।
- FIX_BATCH13 এ নতুন: _DUTI_RE word-boundary bug (বিন্দুটি→বিন্দুইটি) ঠিক, prompt থেকে "x R̸ y" উদাহরণ সরানো (≠ কে R̸ বানাচ্ছিল), prompt এ ∠ ∥ যোগ, margin year ২০২১/২০২২, figure label লাইন সরানো, || → ∥। batch 14 এ দেখতে হবে এগুলো কাজ করল কিনা।

## প্রতি batch এর workflow (Claude chat এর কাজ)
1. device bash: $HOME/mnt/banglamathai। ছবি: check/class_9_General_math_bn/ (CURRENT_BATCH.md দেখো) বা PDF থেকে pymupdf 150dpi। টেক্সট: backend/data/ocr_gemini/class_9_General_math_bn/page_N.txt
2. প্রতিটা পৃষ্ঠা (সবগুলো, বাদ নেই) ছবি vs টেক্সট মেলাও। ভুল ঠিক করো (Python re দিয়ে; sed এ বাংলা range কাজ করে না)।
3. পুরো খারাপ/RECITATION/Tesseract পৃষ্ঠা → হাতে পুরো লেখো, প্রথম লাইন: `[MANUAL: transcribed by Claude (chat) from page image — ...]`; আসলটা .tesseract.txt/.flashlite.txt হিসেবে রাখো। কোনো OCR ফাইল কখনো delete না।
4. ঠিক করা পৃষ্ঠা check/MANUAL_PAGES.txt এ যোগ (format: class_9_General_math_bn/page_N.txt)।
5. লগ: check/ERRORS_LOG.csv (batch,date,book,language,page,status,error_type,gemini_text,correct_text,line,note), check/PAGES_CHECKED.csv।
6. Human audit: random.seed(20261008+batch) দিয়ে ২টা পৃষ্ঠা + হাতে rewrite করা exercise পৃষ্ঠা → check/HUMAN_AUDIT.csv (utf-8-sig), ছবি check/audit_images/ এ। এখন পর্যন্ত ২৮টা পৃষ্ঠা (batch 13: p127, p129)। Peal "audit done" বললে HUMAN_AUDIT.csv পড়ে ভুল ঠিক করো ও residual error rate হিসাব করো।
7. নতুন ধরনের ভুল → results/OCR_FINDINGS_FOR_PAPER.md (এখন item 1-22)।
8. পরের batch এর জন্য tasks/FIX_BATCH<N>.md লেখো (বাংলায়; কাজ ১..n; শেষ কাজ = পরের ১০ পৃষ্ঠা OCR; শেষে "Batch ready" লিখে থামো)।
9. Peal কে বাংলায় রিপোর্ট (পৃষ্ঠাভিত্তিক টেবিল) + এক লাইনের prompt দাও।

## Notation convention
সমান্তরাল = ∥ (U+2225, || না); ত্রিভুজ = Δ; কোণ = ∠ (বাদ পড়লে যোগ করো); চিত্রের লেবেল (A, B, 1, x, 40⁰ …) টেক্সটে রাখা হয় না; recurring dot = U+0307 combining dot (scripts/manual_dotfix.py: digit এর পরে ' = U+0307); superscript Unicode (scripts/sup.py), না হলে ^(…); ভগ্নাংশ a/b, বন্ধনী সহ; মিশ্র "2 4/5"; log₁₀, logₐ; ∛, ⁿ√; বইয়ের শব্দ হুবহু (synonym বসানো যাবে না)।

## Hand-written (full) পৃষ্ঠা এখন পর্যন্ত
p9,17,18,20,23,24,75,85,86,91,92,98,101,102,117,119,120; p30 = Peal এর ground truth। (batch 13 এ পুরো হাতে লেখা পৃষ্ঠা নেই)

## নিয়ম (Peal)
বাংলায় উত্তর; বিস্তারিত ধাপ; কোনো timeline/সময় হিসাব না; backend/ frontend/ কোড বদলানো না (data ফাইল ঠিক করা চলবে); API key কখনো দেখানো না; প্রতিটা পৃষ্ঠা চেক।

## ৪ বইয়ের পরে
ground-truth আরও পৃষ্ঠা → exercise/example split → নতুন Qdrant collection + dropdown tutor → tutor test → deploy → paper (draft/main.tex) → arXiv v1 (cs.CL endorser লাগবে) → MUN supervisor outreach।
