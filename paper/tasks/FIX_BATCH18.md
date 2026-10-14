# FIX_BATCH18 — Unicode normalisation (জরুরি), দুটি নিয়ম, ৭↔৯ পৃষ্ঠা নম্বর, script leak + batch 19

Claude (chat) batch 18 (p171-180) মিলিয়েছে (ERRORS_LOG batch=18)। p171-180 সব MANUAL_PAGES.txt এ (বেশিরভাগ ছোট ঠিক; p180 এর চিত্র/সারণি পুনর্গঠন)। RECITATION হয়নি। p180 এর figure_values_lost flag খুব কাজে লেগেছে — ধন্যবাদ।
নিয়ম আগের মতো: শুধু paper/scripts/full_gemini_ocr.py বদলাবে, কিছু delete না, MANUAL_PAGES এর পৃষ্ঠা ছোঁবে না, API key দেখাবে না, prompt এ বাংলা উদাহরণ যোগ করবে না।

## কাজ ১ — জরুরি: Unicode normalisation (নিয়ম চুপচাপ fire করছে না)
`_LOKKHONIYO_RE` এ "য়" লেখা আছে দুই code point এ (U+09AF য + U+09BC ়), কিন্তু Gemini p174 এ লিখেছে এক code point এ (U+09DF য়)। তাই নিয়মটা p174 এ fire করেনি। একই ঝুঁকি য়/ড়/ঢ় আছে এমন **সব** regex এ।
- post_process() এর একদম শুরুতে টেক্সট `unicodedata.normalize("NFC", text)` করো, আর সব regex pattern ও replacement string ও module load এ একইভাবে NFC করো (একটা helper দিয়ে) — যাতে দুই পাশ সবসময় একই রূপে থাকে। (NFC এ U+09DF → U+09AF U+09BC হয়; দুই দিক একই হলেই হলো।)
- Test: "লক্ষনীয়" দুই রূপেই (09DF এবং 09AF+09BC) → "লক্ষণীয়"। p174.raw.txt এ চালিয়ে দেখাও এখন fire করে।
- Regression: page_1..180 এর .raw.txt এ পুরো post_process আগে আর পরে চালিয়ে কোন কোন নিয়মের fire সংখ্যা বদলাল — টেবিল CURRENT_BATCH.md এ দাও (এটা paper এর জন্য একটা সংখ্যা)।

## কাজ ২ — দুটি → দুইটি নিয়ম বন্ধ করো
বই বেশিরভাগ জায়গায় "দুইটি" লেখে, কিন্তু p178 এ সত্যিই "দুটি" ছাপা — আমাদের নিয়ম সঠিক পড়াকে ভুল বানিয়েছে। `_DUTI_RE` এর replacement বন্ধ করো (নিয়মটা রেখে শুধু flag: `duti_seen: N`)। কারণ: বই নিজেই দুটো রূপ ব্যবহার করে, তাই নিয়ম দিয়ে ঠিক করা যায় না; Claude (chat) ছবি দেখে ঠিক করবে।

## কাজ ৩ — পৃষ্ঠা নম্বর ৭↔৯
p175-177 এ header ১৭০/১৭১/১৭২ এসেছে ১৯০/১৯১/১৯২ হয়ে। FIX_BATCH15 এর `page_number_fixed` নিয়ম শুধু ৪↔৮ ধরে। বাড়াও: পড়া নম্বর আর expected নম্বর যদি ঠিক একটা অঙ্কে আলাদা হয় এবং সেই জোড়া {৪,৮} বা {৭,৯} হয় → expected বসাও, qc note এ জোড়াটাও লেখো। অন্য পার্থক্য → শুধু flag। Test: ১৯০ (expected ১৭০) → ১৭০; ১৮০ (expected ১৪০) → ১৪০; ১৩৫ (expected ১২৮) → শুধু flag।

## কাজ ৪ — script leak flag এ মালয়ালম/আসামি
p175 এ "অন্তর্লিখিত" এর ভেতরে মালয়ালম ര্ + ZWJ (U+0D30 U+0D4D U+200D) এসেছে; p176 এ আসামি ৰ (U+09F0)। `count_script_leak()` এ U+0D00-U+0D7F (Malayalam) আর U+0B80-U+0BFF (Tamil), U+0C00-U+0C7F (Telugu) যোগ করো, আর বাংলা শব্দের ভেতরে U+200D (ZWJ) থাকলে flag। ৰ → র (U+09F0 → U+09B0) এর নিরাপদ বদল যোগ করো (বাংলা বইয়ে ৰ কখনো আসে না)।

## কাজ ৫ — batch 19
FULL_OCR.md Step 4: class_9_General_math_bn পৃষ্ঠা 181-190। CURRENT_BATCH.md আগের মতো (কাজ ১-৪ live কোথায় fire করল + টেবিল + খরচ)।

## কাজ ৬ — commit + push
"Batch ready" এর আগে: `git status` দেখো, সব পরিবর্তন commit — "Batch 19: OCR p181-190 + FIX_BATCH18 (NFC normalisation, DUTI flag-only, page no 7/9, script leaks)" — তারপর `git push origin main`। ফল CURRENT_BATCH.md এ এক লাইনে। শেষে "Batch ready" লিখে থামো।
