# FIX_BATCH6 — ছোট post-processing + batch 7

Claude (chat) batch 6 (p51-60) মিলিয়েছে (ERRORS_LOG batch=6)। p53-55, 57-60 এখন MANUAL_PAGES.txt এ।
নিয়ম আগের মতো (backend/frontend নয়, delete নয়, MANUAL_PAGES ছোঁবে না, key নয়)।

## কাজ ১ — post_process()
- `\because` → `∵`, `\therefore` → `∴` (আছে কিনা দেখো)
- `\frac{X}{Y}` এ Y যদি একাধিক অক্ষর/সংখ্যা+অক্ষর হয় (যেমন `3bc`, `2x`) → হরে বন্ধনী: `X/(3bc)`। লবের জন্যও একই (একক টোকেন না হলে বন্ধনী)।
- প্রশ্ন নম্বর: লাইনের শুরুতে `৩। ` → `৩. ` (বই ফুলস্টপ ব্যবহার করে)
## কাজ ২ — QC flag
- Cyrillic (U+0400–U+04FF) বা Assamese ৰ/ৱ অক্ষর পেলে flag `script_leak` (আগের devanagari_leak এর সাথে)
## কাজ ৩ — batch 7
FULL_OCR.md Step 4: class_9_General_math_bn পৃষ্ঠা 61-70। শেষে "Batch ready" লিখে থামো।
