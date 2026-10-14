# FIX_BATCH15 — পৃষ্ঠা নম্বর ৪↔৮, ASCII-art চিত্র, Markdown/Latin leak, LaTeX চিহ্ন + batch 16

Claude (chat) batch 15 (p141-150, অধ্যায় ৭ ব্যবহারিক জ্যামিতি) মিলিয়েছে (ERRORS_LOG batch=15)। p142-150 MANUAL_PAGES.txt এ; p148, p150 পুরো হাতে লেখা। p141 পরিষ্কার। RECITATION হয়নি।
নিয়ম আগের মতো: শুধু paper/scripts/full_gemini_ocr.py বদলাবে, কিছু delete না, MANUAL_PAGES এর পৃষ্ঠা ছোঁবে না, API key দেখাবে না, prompt এ কোনো বাংলা উদাহরণ যোগ করবে না।

## কাজ ১ — পৃষ্ঠা নম্বর: ৪↔৮ নিজে ঠিক করো
এই batch এ ১০টার মধ্যে ৪টা header এ ৪ কে ৮ পড়েছে (p145 ১৮০→১৪০, p147 ১৮২→১৪২, p149 ১৪৮→১৪৪, p150 ১৮৫→১৪৫), আর flag ধরেছে মাত্র ২টা। একটায় (p144) নম্বরই নেই।
- `detect_page_number_mismatch()` যেখানে expected নম্বর জানে: পড়া নম্বর আর expected নম্বর যদি **শুধু ৪↔৮ অঙ্কে** আলাদা হয় (একই দৈর্ঘ্য, বাকি অঙ্ক এক) → header এর নম্বরটা expected দিয়ে বদলাও, qc note এ `page_number_fixed: ১৮০->১৪০`। অন্য কোনো পার্থক্য হলে আগের মতো শুধু flag।
- p147, p150 এ flag কেন fire করেনি দেখো (primary reading এ header নম্বর আলাদা লাইনে / tab এর পরে ছিল?) — ঠিক করো এবং CURRENT_BATCH.md এ কারণ লেখো।
- header এ নম্বর না থাকলে (p144) → flag `page_number_missing` (নিজে বসাবে না)।
- Test: "১৮০\nগণিত" (expected ১৪০) → "১৪০"; "১২৮" (expected ১২৮) → অপরিবর্তিত; "১৩৫" (expected ১২৮) → শুধু flag।

## কাজ ২ — ASCII-art চিত্র
p147 আর p150 এ model চিত্রগুলো ASCII art দিয়ে **এঁকে** দিয়েছে (`_.-'|`, `/___`, `a__________________`, `-----+-----` ইত্যাদি লাইন), টেক্সটের মাঝে।
- prompt এ যোগ করো (ইংরেজিতে, কোনো উদাহরণ ছাড়া): "Do not draw figures or diagrams; skip them."
- post-process: যে লাইনে ≥ 4টা পরপর `_` বা `-` আছে, অথবা লাইনের non-space অক্ষরের ≥ 50% হলো `_ - | / \ * . ' +` — সেটা ASCII-art লাইন। এমন ২+ লাইনের run (মাঝে ফাঁকা লাইন বা শুধু label লাইন থাকলেও একটা run) বাদ দাও, qc note এ `ascii_figure_removed: N`। একা একটা `----` লাইন বাদ দেবে না, শুধু flag।
- সাবধান: ভগ্নাংশ বা বিয়োগ চিহ্ন (`a − b`, `1/2`) যেন না ধরে — test করো "AB − AC = d" অপরিবর্তিত থাকে।

## কাজ ৩ — Markdown আর Latin leak
- `**...**` আর `__...__` (Markdown bold) → ভেতরের লেখা রেখে চিহ্ন বাদ (p150 "**সম্পাদ্য ৪.**")। qc note `markdown_stripped: N`।
- বাংলা অক্ষরের ঠিক পরে বা আগে ছোট হাতের Latin অক্ষর (একই শব্দে, মাঝে space নেই) → flag `latin_in_bangla_word: <শব্দ>` (p149 "নিমne")। শুধু flag, বদলাবে না। (বড় হাতের A-Z বাদ — "ABC" এর মতো গণিতের নাম পাশে বসতে পারে।)

## কাজ ৪ — LaTeX map এ চিহ্ন যোগ
batch 15 এ `\angle`, `\circ`, `\perp` টেক্সটে থেকে গেছে (p147, p148)। LaTeX→Unicode map এ যোগ করো: `\angle`→`∠`, `\perp`→`⊥`, `\parallel`→`∥`, `\triangle`→`Δ`, `\cong`→`≅`, `\circ`→`°`, আর `^\circ` / `^{\circ}` → `°` (আগে ^ টা সরিয়ে)। Test: "60^\circ" → "60°", "\angle BAD" → "∠BAD"।

## কাজ ৫ — figure_values_lost এ header নম্বর বাদ
p148 এ flag পৃষ্ঠার নিজের header নম্বর (১৪৩) কে চিত্রের মান ধরেছে। প্রথম ২ লাইনের পৃষ্ঠা নম্বর বাদ দিয়ে গোনো।

## কাজ ৬ — batch 16
FULL_OCR.md Step 4: class_9_General_math_bn পৃষ্ঠা 151-160। CURRENT_BATCH.md আগের মতো (কাজ ১-৫ live কোথায় fire করল + টেবিল + খরচ)।

## কাজ ৭ — commit + push
"Batch ready" এর আগে: `git status` দেখো (.env/key/venv যেন না থাকে), সব পরিবর্তন commit — "Batch 16: OCR p151-160 + FIX_BATCH15 (page no ৪/৮ fix, ASCII figures, markdown/latin leak, LaTeX symbols)" — তারপর `git push origin main`। ফল CURRENT_BATCH.md এ এক লাইনে। শেষে "Batch ready" লিখে থামো।
