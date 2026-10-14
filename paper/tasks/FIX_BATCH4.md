# FIX_BATCH4 — ছোট post-processing + batch 5

Claude (chat) batch 4 (p31-40) মিলিয়েছে (ERRORS_LOG batch=4)। p31-35, 37-40 এখন MANUAL_PAGES.txt এ। p36 GT তুলনা: Flash-Lite CER 1.86%।

নিয়ম আগের মতো (backend/frontend নয়, delete নয়, MANUAL_PAGES ছোঁবে না, key নয়)।

## কাজ ১ — post_process() এ যোগ করো
- `\longrightarrow`, `\rightarrow`, `\to` → `→`
- `\begin{tabular}...\end{tabular}` / `\begin{array}` → সারি প্রতি এক লাইন, ঘর `|` দিয়ে আলাদা (`x | 0 | 1 | 2`); `\hline` মুছে দাও
- `\left(` `\right)` → `(` `)`; `\mathbb{N}` → `ℕ` (R→ℝ, Z→ℤ, Q→ℚ)
- `উদাহরণ ১০।` → `উদাহরণ ১০.` (বইয়ে ফুলস্টপ)
- prompt এ যোগ: "Keep negation slashes on relation symbols (e.g. x R̸ y, ∉, ≠) — never drop them."
## কাজ ২ — batch 5
FULL_OCR.md Step 4: class_9_General_math_bn পৃষ্ঠা 41-50। শেষে "Batch ready" লিখে থামো।
