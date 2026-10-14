# FIX_BATCH7 — ভগ্নাংশ-সহগ + batch 8

Claude (chat) batch 7 (p61-70) মিলিয়েছে (ERRORS_LOG batch=7)। p63-67, 69, 70 এখন MANUAL_PAGES.txt এ।
নিয়ম আগের মতো (backend/frontend নয়, delete নয়, MANUAL_PAGES ছোঁবে না, key নয়)।

## কাজ ১ — prompt এ যোগ
"When a fraction multiplies something (a fraction coefficient), wrap the fraction in parentheses: write (1/27)(3a + 1), (1/2)x², f(−(1/2)a) — never 1/27(3a + 1) or 1/2x², which read as a different expression."
## কাজ ২ — post_process()
- `\underline{X}` → X, `\;` `\,` `\!` `\phantom{...}` মুছে দাও
- `X_0`..`X_9` (একক অঙ্কের subscript) → `X₀`..`X₉`; `\%` → `%`
- `f (` → `f(` (ফাংশনের নামের পরে space)
## কাজ ৩ — QC flag `fraction_coefficient`
প্যাটার্ন `\d+/\d+[a-zA-Z(]` (যেমন `1/2x`, `1/27(`) পেলে flag (বদলাবে না)।
## কাজ ৪ — batch 8
FULL_OCR.md Step 4: class_9_General_math_bn পৃষ্ঠা 71-80। শেষে "Batch ready" লিখে থামো।
