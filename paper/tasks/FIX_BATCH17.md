# FIX_BATCH17 — ASCII-art নিয়ম table মুছে দিচ্ছে, একই লাইনের figure label, ঃ/। চিহ্ন + batch 18

Claude (chat) batch 17 (p161-170) মিলিয়েছে (ERRORS_LOG batch=17)। p161, 162, 164, 166-169 MANUAL_PAGES.txt এ। p163, 165, 170 পরিষ্কার। হাতে পুরো লেখা লাগেনি। RECITATION হয়নি।
নিয়ম আগের মতো: শুধু paper/scripts/full_gemini_ocr.py বদলাবে, কিছু delete না, MANUAL_PAGES এর পৃষ্ঠা ছোঁবে না, API key দেখাবে না, prompt এ বাংলা উদাহরণ যোগ করবে না।

## কাজ ১ — জরুরি: ASCII-art নিয়ম আসল table মুছে দিয়েছে
p166 এর raw লেখায় সঠিক Markdown table ছিল (header + `| :---: |` + ৫টা সারি `| ১ | | | | | | |`)। FIX_BATCH15 এর ASCII-art নিয়ম `|` চিহ্নের আধিক্য দেখে সারি আর separator লাইন মুছে দিয়েছে (`ascii_figure_removed: 6` — এটা ভুল fire ছিল)। Claude (chat) সারিগুলো ফিরিয়ে দিয়েছে।
- ASCII-art detector থেকে বাদ দাও: যে লাইন `|` দিয়ে শুরু **এবং** `|` দিয়ে শেষ হয় (Markdown table সারি), আর `| :---: |` / `|---|` ধরনের separator লাইন।
- Regression test: p166.raw.txt এ এখন ASCII নিয়ম ০টা লাইন মুছবে; p147/p150 এর flashlite (ASCII art) এখনো ধরা পড়বে। পুরো corpus (page_1..170 এর .raw.txt) এ table-row লাইন কতগুলো ছিল আর আগের নিয়মে কতগুলো মুছত — সংখ্যা CURRENT_BATCH.md এ লেখো।

## কাজ ২ — একই লাইনে লেখার ডানে figure label
p168 এ চিত্রের লেবেল টেক্সট লাইনের **শেষে** অনেক space এর পরে বসেছে: "৫. O কেন্দ্রবিশিষ্ট … AB = 3        D", "… সমদ্বিখণ্ডক।        C"।
- নিয়ম: লাইনের শেষে ≥ 8টা পরপর space, তারপর শুধু ১-৩টা ছোট token (প্রতিটা ১টা বড় হাতের অক্ষর বা (ক)/(খ)…) — সেই tail কেটে দাও, qc note `trailing_labels_removed: N`।
- একই সাথে: যে লাইনে বাংলা অক্ষর নেই এবং লাইনের ≥ 70% space, আর বাকি সব ১-অক্ষরের token — সেই লাইন label লাইন হিসেবে figure-label run এ গোনো (p168 এর "P   AP   P" ধরনের লাইন)।
- Test: "AB = 3          D" → "AB = 3"; "ক) 5, 6, 7	খ) 5, 7, 14" (tab-separated MCQ) অপরিবর্তিত।

## কাজ ৩ — ঃ আর । বিরাম চিহ্ন
- "মন্তব্যঃ", "অঙ্কনঃ", "প্রমাণঃ", "সমাধানঃ", "কাজঃ" (লাইনের শুরুতে এই শব্দ + ঃ) → ":" (বই এখানে colon দেয়; visarga ঃ দেখতে একই)। শুধু এই তালিকার শব্দের ঠিক পরে — "দুঃখ", "অন্তঃস্থ", "বহিঃস্থ" ইত্যাদি শব্দের ভেতরের ঃ যেন না বদলায় (test করো)।
- অনুশীলনীর প্রশ্ন নম্বর: লাইনের শুরুতে বাংলা অঙ্ক + "।" + tab/space → "." (p167 "১।\t")। আগের `_QUESTION_NUMBER_PERIOD_RE` এ tab ধরা পড়ছে কিনা দেখো — না পড়লে ঠিক করো।

## কাজ ৪ — বানান নিয়ম (শব্দের পুরো রূপ মিললে তবেই)
- "অন্তলিখিত" → "অন্তর্লিখিত" (p167 এ ৩ বার, র-ফলা বাদ)। শুধু পুরো শব্দ (আগে-পরে বাংলা অক্ষর নেই, অথবা পরে "ত"/"তের" জাতীয় বিভক্তি) — lookbehind দাও।
- "লক্ষনীয়" → "লক্ষণীয়" (p142, p162 — দুইবার)।

## কাজ ৫ — batch 18
FULL_OCR.md Step 4: class_9_General_math_bn পৃষ্ঠা 171-180। CURRENT_BATCH.md আগের মতো (কাজ ১-৪ live কোথায় fire করল + টেবিল + খরচ)।

## কাজ ৬ — commit + push
"Batch ready" এর আগে: `git status` দেখো, সব পরিবর্তন commit — "Batch 18: OCR p171-180 + FIX_BATCH17 (table-safe ASCII rule, trailing labels, visarga colon, spelling)" — তারপর `git push origin main`। ফল CURRENT_BATCH.md এ এক লাইনে। শেষে "Batch ready" লিখে থামো।
