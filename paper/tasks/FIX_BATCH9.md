# FIX_BATCH9 — সূচক/লগ অধ্যায়ের জন্য post-processing + batch 10

Claude (chat) batch 9 (p81-90, অধ্যায় ৪ সূচক) মিলিয়েছে — ১০টা পেজই ঠিক করতে হয়েছে (ERRORS_LOG batch=9)। সব MANUAL_PAGES.txt এ। ছোট helper paper/scripts/sup.py বানানো আছে (^{..} -> Unicode superscript)।
নিয়ম আগের মতো (backend/frontend নয়, delete নয়, MANUAL_PAGES ছোঁবে না, key নয়)।

## কাজ ১ — post_process()
- `^{X}` → X এর সব অক্ষর superscript এ রূপান্তরযোগ্য হলে Unicode superscript (ᵐ⁺ⁿ), না হলে `^(X)` — paper/scripts/sup.py এর fix() ব্যবহার করো। `^x` (একক অক্ষর) একইভাবে।
- `\dfrac{A}{B}`, `\tfrac` → `\frac` এর মতোই (A)/(B) নিয়মে
- `\sqrt[n]{X}` → `ⁿ√X` (n=3 হলে `∛X`, 4 হলে `∜X`); বহু-অক্ষর X হলে বন্ধনী
- `\begin{cases} A \\ B \end{cases}` → `{ A ; B }`
- HTML `<table>...</table>` → সারি প্রতি লাইন, ঘর `|` দিয়ে
- Math-italic অক্ষর (U+1D400–U+1D7FF) → সাধারণ ASCII অক্ষর
- `logᵪ`, `logᵦ` → `log_b` (log এর পরে Greek subscript); flag `greek_subscript`
## কাজ ২ — prompt এ যোগ
"Write exponents with Unicode superscripts (a², aᵐ⁺ⁿ) or as a^(…) when they contain fractions; keep each exponent attached to its base. Write log bases as log₂, log₁₀, logₐ, log_b. Never output LaTeX or HTML."
## কাজ ৩ — QC flag `exponent_detached`
প্যাটার্ন `\)\s+[a-z][⁻⁺]` (যেমন `(aᵖ) q⁻r`) → flag।
## কাজ ৪ — batch 10
FULL_OCR.md Step 4: class_9_General_math_bn পৃষ্ঠা 91-100। শেষে "Batch ready" লিখে থামো।
