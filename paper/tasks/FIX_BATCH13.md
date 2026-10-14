# FIX_BATCH13 — post-process bug, prompt উদাহরণ leak, geometry চিহ্ন + batch 14

Claude (chat) batch 13 (p121-130) মিলিয়েছে (ERRORS_LOG batch=13)। p121, 123, 124, 125, 127, 128, 129, 130 MANUAL_PAGES.txt এ। p122, p126 পরিষ্কার। RECITATION হয়নি।
নিয়ম আগের মতো: backend/ frontend/ কোড বদলাবে না (শুধু paper/scripts/full_gemini_ocr.py), কোনো ফাইল delete করবে না, MANUAL_PAGES এর পৃষ্ঠা ছোঁবে না, API key দেখাবে না।

## কাজ ১ — আমাদের নিজের post-process bug: `_DUTI_RE`
`_DUTI_RE = re.compile(r"দুটি")` এ word boundary নেই। তাই সঠিক শব্দ "বিন্দুটি" (বি-ন্-দু-টি) এর ভেতরের "দুটি" ধরে "বিন্দুইটি" বানিয়ে দিয়েছে (p123, p124 — Gemini এর raw লেখা ঠিক ছিল)।
- ঠিক করো: সামনে কোনো বাংলা অক্ষর থাকলে মিলবে না — `re.compile(r"(?<![ঀ-৿])দুটি")`। (Python এর `\b` বাংলা কার/হসন্তের সাথে ঠিকমতো কাজ করে না, তাই lookbehind।)
- ছোট test লেখো: "বিন্দুটি" অপরিবর্তিত থাকবে; "দুটি", "দুটিকে", "(দুটি" → "দুইটি…" হবে।
- `fix_known_bangla_typos()` এর বাকি regex গুলোও একবার দেখো — অন্য কোনোটা কি শব্দের মাঝখানে মিলতে পারে? পেলে একই ভাবে ঠিক করো এবং CURRENT_BATCH.md এ লেখো।
- শুধু পড়ে দেখো (কিছু বদলাবে না): class_9_General_math_bn এর page_1..130.txt এ "[বাংলা অক্ষর]দুইটি" ধরনের আর কোনো ভাঙা শব্দ আছে কিনা — থাকলে তালিকা CURRENT_BATCH.md এ দাও।

## কাজ ২ — prompt এর উদাহরণ নিজেই ভুল বানাচ্ছে
PROMPT এ আছে: "Keep negation slashes on relation symbols (e.g. x R̸ y, ∉, ≠)"। p129 এ বইয়ের `AB = AC ≠ BC` এসেছে `AB = AC R̸ BC` — model উদাহরণের R̸ কপি করেছে।
- বাক্যটা বদলাও: "Keep negation slashes on symbols exactly as printed (∉, ≠, ⊄) -- never drop them, and never replace one symbol with another." (R̸ উদাহরণ বাদ।)
- PROMPT এর Unicode চিহ্নের তালিকায় (∈ ∉ ∪ … ⊆) যোগ করো: `∠ ∥ Δ ° ≠`। কারণ: p123 এ ∠POQ এর ∠ তিনবার বাদ পড়েছে (অধ্যায় ৬ থেকে জ্যামিতি, সামনে প্রচুর ∠ আসবে)।

## কাজ ৩ — post-process এ ছোট তিনটা যোগ
(ক) `MARGIN_YEAR_TOKENS` এ যোগ করো: "২০২১", "২০২২", "2021", "2022" (p130 এর শেষে "২০২১" ঢুকেছিল)।
(খ) সমান্তরাল চিহ্ন: দুই বড় হাতের অক্ষরের জোড়ার মাঝে `||` থাকলে `∥` (U+2225) বানাও — যেমন "AB || CD" → "AB ∥ CD", "BA || CE" → "BA ∥ CE"। regex: `([A-Z]{2})\s*\|\|\s*([A-Z]{2})` → `\1 ∥ \2`। (|| থাকলে tutor এটাকে absolute value ভাবতে পারে।)
(গ) চিত্রের লেবেল: জ্যামিতির পৃষ্ঠায় চিত্রের লেবেল আলাদা আলাদা লাইনে টেক্সটে ঢুকছে (p130 এ ~৩০ লাইন: A, B, C, 2, 1, x, y, 40⁰, (i), (ii))। নতুন function: পরপর **৩ বা বেশি** লাইন যেগুলোর প্রতিটা ≤ ৪ অক্ষর, কোনো বাংলা অক্ষর নেই, আর শুধু বড় হাতের অক্ষর/অঙ্ক/x y/°⁰/(i)(ii) জাতীয় — সেই পুরো run বাদ দাও এবং qc note এ `figure_labels_removed: N` লেখো। ২টা বা কম লাইনের run বাদ দেবে না, শুধু flag করবে (`figure_labels_suspect`)। ছোট test: p130 এর মতো একটা নমুনায় run বাদ যায়, কিন্তু "∴ x = 5" বা "(i)" একা থাকলে থাকে।

## কাজ ৪ — batch 14
FULL_OCR.md Step 4: class_9_General_math_bn পৃষ্ঠা 131-140। CURRENT_BATCH.md আগের মতো লেখো (কাজ ১-৩ এর ফল + পৃষ্ঠার টেবিল + খরচ)। RECITATION হলে split ধাপ live কাজ করল কিনা আলাদা করে লেখো। শেষে "Batch ready" লিখে থামো।
