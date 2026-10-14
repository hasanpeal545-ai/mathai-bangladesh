# FIX_BATCH12 — RECITATION এর নতুন সমাধান + batch 13

Claude (chat) batch 12 (p111-120) মিলিয়েছে (ERRORS_LOG batch=12)। p111, 113, 114, 116-120 MANUAL_PAGES.txt এ। p117, 119, 120 (অধ্যায় ৬ এর বর্ণনামূলক পেজ) পুরো RECITATION — Claude হাতে লিখেছে। অধ্যায় ৬ এ এমন পেজ আরও আসবে, তাই:
নিয়ম আগের মতো (backend/frontend নয়, delete নয়, MANUAL_PAGES ছোঁবে না, key নয়)।

## কাজ ১ — escalation ladder এ নতুন ধাপ (Tesseract fallback এর আগে): "split page"
পেজের ছবি উপর-নিচে দুই ভাগে কাটো (মাঝে ~৫% overlap), প্রতিটা ভাগ আলাদা call এ flash-lite দিয়ে পড়াও, তারপর জোড়া লাগাও (overlap এর ডুপ্লিকেট লাইন বাদ দাও)। ছোট টুকরো সাধারণত RECITATION এড়ায়। এটা কাজ করলে RUN_LOG এ `escalate_split` লেখো।
প্রথমে MANUAL নয় এমন একটা blocked পেজে test করো — না পেলে নতুন batch এর blocked পেজে।
## কাজ ২ — prompt এ যোগ
"Transcribe exactly as printed — do not replace any word with a synonym or 'correct' the book's wording."
## কাজ ৩ — batch 13
FULL_OCR.md Step 4: class_9_General_math_bn পৃষ্ঠা 121-130। শেষে "Batch ready" লিখে থামো।
