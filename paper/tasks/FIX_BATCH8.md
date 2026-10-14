# FIX_BATCH8 — script-leak fix + batch 9

Claude (chat) batch 8 (p71-80) মিলিয়েছে (ERRORS_LOG batch=8)। p73, 75-78, 80 MANUAL_PAGES.txt এ।
নিয়ম আগের মতো (backend/frontend নয়, delete নয়, MANUAL_PAGES ছোঁবে না, key নয়)।

## কাজ ১ — script_leak flag বাড়াও
Odia (U+0B00–U+0B7F) যোগ করো। সাথে Gurmukhi/Gujarati/Tamil ব্লকও (U+0A00–U+0BFF) — এক রেঞ্জে।
## কাজ ২ — prompt এ যোগ
"Keep digits in the same script as printed: Latin digits (0-9) stay Latin and Bangla digits (০-৯) stay Bangla — never convert between them."
## কাজ ৩ — fix_known_bangla_typos(): `নিয়ামাবলি`→`নিয়মাবলি`, `ফর্মী`→`ফর্মা`
## কাজ ৪ — batch 9
FULL_OCR.md Step 4: class_9_General_math_bn পৃষ্ঠা 81-90। শেষে "Batch ready" লিখে থামো।
