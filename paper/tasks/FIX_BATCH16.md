# FIX_BATCH16 — ∠ এর জায়গায় "/", heading এ Latin অঙ্ক, MCQ ক্রম, \Delta + batch 17

Claude (chat) batch 16 (p151-160) মিলিয়েছে (ERRORS_LOG batch=16)। p151, 153-156, 158-160 MANUAL_PAGES.txt এ। p152, p157 পরিষ্কার। কোনো পৃষ্ঠা পুরো হাতে লিখতে হয়নি — FIX_BATCH15 এর page_number_fixed (p154) ঠিকঠাক কাজ করেছে। RECITATION হয়নি।
নিয়ম আগের মতো: শুধু paper/scripts/full_gemini_ocr.py বদলাবে, কিছু delete না, MANUAL_PAGES এর পৃষ্ঠা ছোঁবে না, API key দেখাবে না, prompt এ বাংলা উদাহরণ যোগ করবে না।

## কাজ ১ — `\Delta` → `Δ`
তোমার প্রশ্নের উত্তর: এই বইয়ে `\Delta` সবসময় ত্রিভুজ চিহ্ন (p159: "\Delta OAE ≅ \Delta OCF")। LaTeX map এ `\Delta` → `Δ` যোগ করো। (পরিবর্তন/"change in x" অর্থে এই বইগুলোতে এটা আসেনি; এলে Claude (chat) চেকে ধরবে।)

## কাজ ২ — ∠ এর জায়গায় "/"
p154 এ ∠ চিহ্ন তিনবার "/" হয়ে এসেছে: "একটি কোণ /B = 60°", "/ABE", "/ABC"।
- নিয়ম: "/" এর ঠিক আগে space বা লাইনের শুরু বা "(" এবং ঠিক পরে ১-৩টা বড় হাতের Latin অক্ষর (তারপর অক্ষর নয় এমন কিছু) → "/" কে "∠" বানাও। qc note `angle_slash_fixed: N`।
- ভগ্নাংশ যেন না ধরে: "a/2", "p/3", "(1/2)AB", "AB/CD" — "/" এর আগে অক্ষর/অঙ্ক/")" থাকলে বদলাবে না। Test করো: "কোণ /B = 60°" → "কোণ ∠B = 60°"; "a/2 = OC" → অপরিবর্তিত; "AB/CD" → অপরিবর্তিত।

## কাজ ৩ — heading এর নম্বরে Latin অঙ্ক
p153 এ "উদাহরণ ৪." এসেছে "উদাহরণ 8." (বাংলা ৪ কে Latin 8 পড়েছে) — dropdown এই নম্বরে চলে।
- নিয়ম: লাইনের শুরুতে (উদাহরণ|অনুশীলনী|উপপাদ্য|সম্পাদ্য|অনুসিদ্ধান্ত|অধ্যায়) এর পরে Latin অঙ্ক/অঙ্ক.অঙ্ক থাকলে → বাংলা অঙ্কে বদলাও (বই এসব heading এ সবসময় বাংলা অঙ্ক দেয়)। 8 → ৪ বিশেষভাবে test করো। qc note `heading_digit_fixed`।
- শুধু এই heading শব্দগুলোর ঠিক পরে — বাকি লেখার Latin অঙ্কে হাত দেবে না (prompt এর "same script" নিয়ম বহাল)।

## কাজ ৪ — দুই কলামের MCQ এর ক্রম
p154 এ অপশন এসেছে ক), গ), খ), ঘ) ক্রমে (কলাম ধরে পড়া)। পরপর ৪ লাইন যদি ঠিক ক) গ) খ) ঘ) ক্রমে শুরু হয় → ক) খ) গ) ঘ) ক্রমে সাজাও, qc note `mcq_reordered`। অন্য কোনো ক্রম হলে শুধু flag।

## কাজ ৫ — batch 17
FULL_OCR.md Step 4: class_9_General_math_bn পৃষ্ঠা 161-170। CURRENT_BATCH.md আগের মতো (কাজ ১-৪ live কোথায় fire করল + টেবিল + খরচ)।

## কাজ ৬ — commit + push
"Batch ready" এর আগে: `git status` দেখো (.env/key/venv যেন না থাকে), সব পরিবর্তন commit — "Batch 17: OCR p161-170 + FIX_BATCH16 (angle slash, heading digits, MCQ order, \Delta)" — তারপর `git push origin main`। ফল CURRENT_BATCH.md এ এক লাইনে। শেষে "Batch ready" লিখে থামো।
