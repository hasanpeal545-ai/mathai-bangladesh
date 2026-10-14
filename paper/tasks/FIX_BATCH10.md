# FIX_BATCH10 — অনুশীলনী নম্বর যাচাই + batch 11

Claude (chat) batch 10 (p91-100) মিলিয়েছে (ERRORS_LOG batch=10)। p91-93, 95-100 MANUAL_PAGES.txt এ।
নিয়ম আগের মতো (backend/frontend নয়, delete নয়, MANUAL_PAGES ছোঁবে না, key নয়)।

## কাজ ১ — QC flag `exercise_chapter_mismatch` (গুরুত্বপূর্ণ — tutor এর dropdown এটার উপর নির্ভর করে)
পেজে `অনুশীলনী X.Y` বা `উদাহরণ`/`অধ্যায়` হেডারে অধ্যায় নম্বর X যদি পেজের header লাইনের অধ্যায় নম্বরের সাথে (যেমন "অধ্যায় ৪. সূচক ও লগারিদম") বা আগের পেজের অধ্যায়ের সাথে না মেলে → flag। curriculum.json এর chapter page range ব্যবহার করে প্রত্যাশিত অধ্যায় বের করো (PDF page − 5 = printed page)।
## কাজ ২ — fix_known_bangla_typos(): `লগ্নের`→`লগের`, `বহুম্পদী`→`বহুপদী`, `সংখ্যাক`→`সংখ্যক`
## কাজ ৩ — post_process(): `log₁0`→`log₁₀`, `log_e`/`log_e `→`logₑ`
## কাজ ৪ — batch 11
FULL_OCR.md Step 4: class_9_General_math_bn পৃষ্ঠা 101-110। শেষে "Batch ready" লিখে থামো।
