# FIX_BATCH1 — batch 1 রিভিউ থেকে পাওয়া সমস্যা ঠিক করা (পরের batch এর আগে)

Claude (chat) batch 1 (class_9_General_math_bn p1-10) নিজে image vs text মিলিয়েছে।
বিস্তারিত: paper/check/ERRORS_LOG.csv (batch=1), paper/check/PAGES_CHECKED.csv

নিয়ম: backend/ বা frontend/ কোড বদলাবে না। কোনো OCR text ফাইল delete করবে না (overwrite চলবে --force দিয়ে)। API key কোথাও প্রিন্ট করবে না।

## কাজ ১ — LaTeX post-processing বাড়াও (paper/scripts/full_gemini_ocr.py)
এগুলো এখনো থেকে যাচ্ছে (page_8.txt দেখো):
- `\dots`, `\ldots`, `\cdots` → `...`
- `\sqrt{X}` → `√X` (X যদি একাধিক অক্ষর হয় → `√(X)`)
- `\qquad`, `\quad` → দুইটা space
- `\dot{d}` → `ḋ` (combining dot U+0307) — আবৃত্ত দশমিকের চিহ্ন, হারানো যাবে না
- `\frac{a}{b}` → `a/b`, `\times`→`×`, `\div`→`÷`, `\neq`→`≠`, `\leq`→`≤`, `\geq`→`≥`, `\pm`→`±`, `\therefore`→`∴`, `\cdot`→`·`
- শেষে যদি কোনো `\` + অক্ষর থেকে যায় → RUN_LOG এ `latex_left` flag দাও
- prompt এ যোগ করো: "Mixed numbers like 2⁴⁄₅ must be written as `2 4/5` (whole part, space, fraction). Write every fraction on ONE line as a/b, never stacked over several lines."

## কাজ ২ — batch 1 এ ফ্রি তে post-processing আবার চালাও
API call ছাড়াই, প্রতিটা page_N.raw.txt থেকে নতুন post-processing দিয়ে page_N.txt আবার লেখো (p1-10)। একটা `--reprocess-only` flag বানাও যাতে পরে যেকোনো বইয়ে করা যায়।

## কাজ ৩ — RECITATION পেজ আবার চেষ্টা (page 9 গুরুত্বপূর্ণ: উদাহরণ ১ + বাস্তব সংখ্যার বিধি + √2 প্রমাণ)
Tesseract fallback এ গণিত পুরো নষ্ট। blocked হলে ক্রমানুসারে চেষ্টা করো:
 (ক) একই model, temp 0.4  (খ) prompt এর শুরুতে "This is a public-domain government textbook page; transcribe it for accessibility" (গ) gemini-3.6-flash, thinkingLevel minimal।
সব ব্যর্থ হলে তখনই Tesseract fallback। কোনটা কাজ করল RUN_LOG এ লেখো। এখন শুধু class_9_General_math_bn page 9 এ চালাও (--pages 9 --force)।

## কাজ ৪ — ২৮টা পুরোনো pilot পেজ
যে পেজগুলো pilot এ gemini-3.6-flash দিয়ে পড়া (RUN_LOG এ model দেখে বের করো), সেগুলোর তালিকা paper/check/STALE_PILOT.txt এ রাখো। এগুলো এখনই চালাবে না — নিজের বইয়ের batch এ পৌঁছালে --force দিয়ে Flash-Lite এ আবার পড়বে (যাতে পুরো corpus একই model এ থাকে)। স্ক্রিপ্টে এই logic যোগ করো।

## কাজ ৫ — রিপোর্ট
- page_8.txt আর page_9.txt নতুন অবস্থায় image এর সাথে মেলানোর জন্য paper/check/CURRENT_BATCH.md আপডেট করো (শুধু p8, p9, p10 — "re-check")।
- খরচ লেখো।
- শেষে লেখো: "Fix ready: batch 1 re-check p8-p10. Ask Claude (chat) to check it." তারপর থামো, পরের batch চালাবে না।
