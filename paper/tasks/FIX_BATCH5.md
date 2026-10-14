# FIX_BATCH5 — post-processing + batch 6

Claude (chat) batch 5 (p41-50) মিলিয়েছে (ERRORS_LOG batch=5)। p41-43, 45, 47-50 এখন MANUAL_PAGES.txt এ।

নিয়ম আগের মতো (backend/frontend নয়, delete নয়, MANUAL_PAGES ছোঁবে না, key নয়)।

## কাজ ১ — fix_known_bangla_typos() এ যোগ
- `বীজগণিতিক` → `বীজগাণিতিক` (এই বইয়ের নিয়মিত বানান; ৩য় অধ্যায় জুড়ে আসবে)
- `দুটি` → `দুইটি`, `দুটিকে` → `দুইটিকে` (বই সবসময় দুইটি লেখে)
- `উদাাহরণ` → `উদাহরণ` (দ্বিগুণ আ-কার)
- `সূত্র ১।` / `অনুসিদ্ধান্ত ১।` → `সূত্র ১.` (উদাহরণ এর মতো)
## কাজ ২ — QC flag
- পৃষ্ঠার প্রথম ২ লাইনে পৃষ্ঠা নম্বর যদি Latin অঙ্কে (যেমন `88`) বা আগের পৃষ্ঠার নম্বর+১ এর সাথে না মেলে → flag `page_number_mismatch` (PDF পৃষ্ঠা − ৫ = ছাপা নম্বর এই বইয়ে)
- লাইনের শেষে tab + একটা বাংলা অঙ্ক (margin থেকে আসা) → মুছে দাও, flag `margin_digit`
- `X / Y` প্যাটার্ন যেখানে X এ `+`/`−` আছে আর বন্ধনী নেই (যেমন `(a+b)² + (a−b)² / 2`) → flag `fraction_parens` (বদলাবে না, Claude দেখবে)
## কাজ ৩ — batch 6
FULL_OCR.md Step 4: class_9_General_math_bn পৃষ্ঠা 51-60। শেষে "Batch ready" লিখে থামো।
