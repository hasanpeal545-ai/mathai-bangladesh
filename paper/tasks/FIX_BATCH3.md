# FIX_BATCH3 — নতুন post-processing + batch 4

Claude (chat) batch 3 (p21-30) মিলিয়েছে, সব ঠিক করা হয়েছে (paper/check/ERRORS_LOG.csv batch=3)। p21-27, 29, 30 এখন MANUAL_PAGES.txt এ। p30 = Peal এর যাচাই করা ground truth (Flash-Lite primary CER 5.15%, alt reading 0.36%)।

নিয়ম: backend/ frontend/ বদলাবে না। OCR text delete করবে না। MANUAL_PAGES.txt এর পেজ ছোঁবে না। key প্রিন্ট করবে না।

## কাজ ১ — post_process() এ যোগ করো
- `<bos>`, `<eos>`, `<pad>` এর মতো model token মুছে দাও; flag `token_leak`
- `\subseteq` / `⊂eq` → `⊆`, `\supseteq` → `⊇`, `\setminus` → `\` , `\overline{X}` → `X̄`-এর বদলে শুধু `X` রেখে flag `overline` (Claude দেখবে)
- `\text{...}` → ভেতরের লেখা
- nested `\frac` ঠিক করো: ভেতর থেকে বাইরে convert (innermost first), প্রতিটা অংশ বন্ধনীতে
- শব্দের শুরুতে একই বাংলা অক্ষর দুবার (`উউদাহরণ`, `মমন্তব্য`) → একবার; শুধু এই নির্দিষ্ট শব্দগুলোর তালিকা দিয়ে (উদাহরণ, মন্তব্য, সমাধান), সাধারণ নিয়ম না
- Devanagari (U+0900–U+097F) অক্ষর পেলে flag `devanagari_leak` (বদলাবে না)
## কাজ ২ — QC: primary vs alt কোনটা ভালো?
p30 এ alt (temp 0.4) reading primary এর চেয়ে অনেক ভালো ছিল। bn পেজে দুই reading এর মধ্যে যেটায় LaTeX leftover/token_leak/devanagari কম, সেটাকে promote করো; টাই হলে primary। কোনটা নিলে RUN_LOG এ লেখো।
## কাজ ৩ — batch 4
FULL_OCR.md Step 4: class_9_General_math_bn পৃষ্ঠা 31-40। শেষে "Batch ready" লিখে থামো।
