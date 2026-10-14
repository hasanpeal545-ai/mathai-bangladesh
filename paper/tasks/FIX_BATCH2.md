# FIX_BATCH2 — আবৃত্ত দশমিকের ফোঁটা (recurring dot) হারানো

Claude (chat) batch 2 (class_9_General_math_bn p11-20) image vs text মিলিয়েছে। বিস্তারিত: paper/check/ERRORS_LOG.csv (batch=2)।
**মূল সমস্যা:** flash-lite বেশিরভাগ পেজে আবৃত্ত দশমিকের উপরের ফোঁটা পুরো বাদ দিচ্ছে (p12, 14, 15, 16, 18, 20)। 0.2̇4̇ হয়ে যাচ্ছে 0.24 — অর্থ বদলে যায়, tutor এর জন্য মারাত্মক। p13 এ একই model ঠিক রেখেছে, p19 এ gemini-3.6-flash ঠিক রেখেছে — তাই prompt এ স্পষ্ট বললে কাজ করার কথা।

নিয়ম: backend/ frontend/ বদলাবে না। OCR text delete করবে না। key প্রিন্ট করবে না। page_8.txt, page_9.txt, page_10.txt, page_17.txt (Claude এর হাতে ঠিক করা; 9 আর 17 "[MANUAL" দিয়ে শুরু) কখনো overwrite করবে না — স্ক্রিপ্টে এই guard যোগ করো (প্রথম লাইন "[MANUAL" হলে --force দিলেও skip)।

## কাজ ১ — prompt এ যোগ করো
"A dot printed ABOVE a digit marks a recurring decimal and MUST be kept: write that digit followed by U+0307 (e.g. 0.2̇4̇, 5.234̇57̇). Never drop these dots, and never read a dotted 1 as the letter i. Also keep fractions on one line as a/b even inside worked solutions."

## কাজ ২ — post-processing (deterministic)
- `আবৃ্ত` → `আবৃত্ত`; শব্দ হিসেবে `আবৃত` (পরে ্ত নেই) → `আবৃত্ত`, `অনাবৃত` → `অনাবৃত্ত` (এই বইগুলোতে "আবৃত" প্রায় সবসময় আবৃত্ত এর ভুল পড়া)
- `মস্তব্য` → `মন্তব্য`
- কতগুলো বদলাল RUN_LOG এ লেখো।

## কাজ ৩ — নতুন QC flag `missing_recurring_dot`
পেজে "আবৃত্ত" বা "পৌনঃপুনিক" শব্দ আছে + দশমিক সংখ্যা আছে, কিন্তু একটাও U+0307 নেই → flag।
flag হলে স্বয়ংক্রিয়ভাবে সেই পেজ gemini-3.6-flash (thinkingLevel minimal) দিয়ে আবার পড়বে; নতুন reading এ U+0307 থাকলে সেটা promote করবে। এই escalation এর খরচ আলাদা লিখবে।

## কাজ ৪ — আবার চালাও
`--force` দিয়ে class_9_General_math_bn pages 11,12,14,15,16,18,20 আবার পড়াও (13, 17, 19 বাদ — 17 manual, 13/19 ঠিক আছে; 19 এ শুধু কাজ ২ এর post-processing লাগাও --reprocess-only দিয়ে)।
প্রতি পেজে U+0307 কতগুলো এলো তার টেবিল CURRENT_BATCH.md এ দাও।

## কাজ ৫
খরচ লেখো। শেষে লেখো: "Fix ready: batch 2 re-check. Ask Claude (chat) to check it." তারপর থামো।
