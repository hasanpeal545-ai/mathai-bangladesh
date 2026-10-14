# FIX_BATCH2b — হাতে ঠিক করা পেজ রক্ষা + আবৃত্ত দশমিক পেজে বিশেষ flag

Claude (chat) batch 2 re-run মিলিয়েছে। ফল: dot prompt এর পর ফোঁটা আসছে, কিন্তু অনেক জায়গায় ভুল অঙ্কের উপর (p15, 16, 18, 20 এ ১০+ সংখ্যা; gemini-3.6-flash এর p19 এও ৪টা)। তাই Claude নিজে ছবি দেখে p11, 14, 15, 16, 18, 19, 20 ঠিক করেছে (p18, p20 পুরো নতুন করে লেখা, "[MANUAL" দিয়ে শুরু)। পুরোনো reading গুলো .before_dotfix.txt / .flashlite.txt নামে রাখা আছে।

নিয়ম: backend/ frontend/ বদলাবে না। OCR text delete করবে না। key প্রিন্ট করবে না।

## কাজ ১ — guard বাড়াও
`is_manually_fixed()` এখন থেকে `paper/check/MANUAL_PAGES.txt` (এক লাইনে একটা `book/page_N.txt`) পড়বে, + আগের "[MANUAL" marker check। এই ফাইলে থাকা পেজ --force, --reprocess-only, STALE_PILOT কোনো অবস্থাতেই overwrite হবে না। hardcoded page_8/10 লিস্ট সরিয়ে এই ফাইলে নির্ভর করো (ফাইলে ওগুলো আছে)। সরাসরি test করো (সব ১১টা পেজ force করে দেখাও 0 call, ফাইল অপরিবর্তিত)।

## কাজ ২ — `has_recurring_dots` flag
কোনো পেজে U+0307 থাকলে CURRENT_BATCH.md এর Note কলামে **has_recurring_dots (N)** লিখবে, যাতে Claude (chat) ওই পেজগুলো zoom করে প্রতিটা ফোঁটা মেলায়। (escalation না — শুধু flag।)

## কাজ ৩ — `\frac` বন্ধনী
`\frac{a - b}{c}` → `(a - b)/c` (লব বা হরে +, −, -, space থাকলে বন্ধনী দাও)। একইভাবে হর এর জন্য। শুধু ভবিষ্যতের পেজে লাগবে (হাতে ঠিক করা পেজ ছোঁবে না)।

## কাজ ৪ — পরের batch
তারপর FULL_OCR.md Step 4 অনুযায়ী batch 3 চালাও: class_9_General_math_bn পৃষ্ঠা 21-30। শেষে "Batch ready" লিখে থামো।
