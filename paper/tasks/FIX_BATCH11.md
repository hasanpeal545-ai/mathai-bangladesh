# FIX_BATCH11 — batch 12

Claude (chat) batch 11 (p101-110) মিলিয়েছে (ERRORS_LOG batch=11)। p101, 102, 104-109 MANUAL_PAGES.txt এ।
নিয়ম আগের মতো (backend/frontend নয়, delete নয়, MANUAL_PAGES ছোঁবে না, key নয়)।

## কাজ ১ — QC flag `script_digit_mismatch`
পেজে গণিত-লাইনে (যেখানে x, y, =, +, − আছে) বাংলা অঙ্ক (০-৯) বেশি থাকলে → flag। (p101 এ Flash-Lite সব Latin অঙ্ক বাংলায় বদলে দিয়েছিল, prompt নিয়ম সত্ত্বেও।) flag হলে secondary reading এ Latin অঙ্ক বেশি থাকলে সেটা promote করো।
## কাজ ২ — fix_known_bangla_typos(): `দ্বিমাত`→`দ্বিঘাত`, `বহুমপদী`→`বহুপদী`
## কাজ ৩ — post_process(): `√(N)` যেখানে N একটি মাত্র সংখ্যা → `√N`
## কাজ ৪ — batch 12
FULL_OCR.md Step 4: class_9_General_math_bn পৃষ্ঠা 111-120। শেষে "Batch ready" লিখে থামো।
