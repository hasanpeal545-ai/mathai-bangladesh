"""Step 3d.2-3d.5: test gemini-3.6-flash vs a Flash-Lite model, both at the
lowest thinkingLevel, via raw REST (bypassing the outdated SDK -- it has no way
to express thinkingConfig at all, confirmed in paper/results/FULL_OCR_MODEL_TEST.md).

Per FULL_OCR.md Step 3d: ONE call per page per setting (no bn double-call in
this test), same current prompt (margin-ignore + plain-fraction, imported
directly from full_gemini_ocr.py so it can't drift from the real pipeline
prompt), temperature 0.

Pages (fixed, not --sample-picked): the 3 bn pages with hand-verified ground
truth (class_9_General_math_bn p30/p36/p44) + the 2 known digit-error pages
(class_6_math_bn p156, class_7_math_bn p14).

Settings:
  A: gemini-3.6-flash,      thinkingLevel=minimal
  B: gemini-3.5-flash-lite, thinkingLevel=minimal
     (chosen over the "gemini-flash-lite-latest" alias for reproducibility --
     "latest" can silently point at a different model later; 3.5-flash-lite is
     the specific, pinned Flash-Lite release in the same Gemini-3 generation as
     gemini-3.6-flash, confirmed via paper/results/AVAILABLE_MODELS.md to also
     report "thinking": true and to accept thinkingLevel the same way.)

Budget safety: tracks real cumulative cost as it goes (using the real Flash
price for setting A, and a third-party-sourced Flash-Lite price for setting B
-- see the report for that caveat) and stops immediately, before making any
further call, if projected to exceed $0.45 (leaving margin under the task's
$0.50 cap for this whole step, which also includes the free discovery calls
already made).

Outputs saved to paper/results/model_test_outputs/<setting>/<book>_p<page>.txt
(kept, for Peal/Claude-chat to inspect) -- NOT backend/data/ocr_gemini (that's
the main corpus pipeline's output location; this is a one-off comparison test).
"""
import base64
import csv
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND_DIR = os.path.join(ROOT, "backend")
SCRIPTS_DIR = os.path.join(ROOT, "paper", "scripts")
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, SCRIPTS_DIR)

from config import settings  # noqa: E402
import full_gemini_ocr as pipeline  # noqa: E402  (reuse PROMPT + render_page_image)

import requests  # noqa: E402

API_BASE = "https://generativelanguage.googleapis.com/v1beta"
OUT_DIR = os.path.join(ROOT, "paper", "results", "model_test_outputs")
LOG_PATH = os.path.join(ROOT, "paper", "results", "model_test_log.csv")

PDF_ROOT = pipeline.PDF_ROOT
PAGES = [
    {"book": "class_9_General_math_bn", "page": 30, "pdf": os.path.join(PDF_ROOT, "bangla", "class_9_General_math_bn.pdf")},
    {"book": "class_9_General_math_bn", "page": 36, "pdf": os.path.join(PDF_ROOT, "bangla", "class_9_General_math_bn.pdf")},
    {"book": "class_9_General_math_bn", "page": 44, "pdf": os.path.join(PDF_ROOT, "bangla", "class_9_General_math_bn.pdf")},
    {"book": "class_6_math_bn", "page": 156, "pdf": os.path.join(PDF_ROOT, "bangla", "class_6_math_bn.pdf")},
    {"book": "class_7_math_bn", "page": 14, "pdf": os.path.join(PDF_ROOT, "bangla", "class_7_math_bn.pdf")},
]

SETTINGS = [
    {"label": "A_gemini-3.6-flash_minimal", "model": "gemini-3.6-flash", "thinking_level": "minimal"},
    {"label": "B_gemini-3.5-flash-lite_minimal", "model": "gemini-3.5-flash-lite", "thinking_level": "minimal"},
]

# Real published price ($1.50/1M in, $7.50/1M out) confirmed by Peal for gemini-3.6-flash.
PRICE = {
    "gemini-3.6-flash": {"in": 1.50 / 1000, "out": 7.50 / 1000},  # $ per 1K tokens
    # Third-party-sourced (not confirmed directly off an official Google pricing
    # page the way the Flash price was) -- flagged in the report.
    "gemini-3.5-flash-lite": {"in": 0.30 / 1000, "out": 2.50 / 1000},
}

BUDGET_STOP_USD = 0.45


def image_to_base64_png(pdf_path, page_number):
    img = pipeline.render_page_image(pdf_path, page_number)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def call_rest(model, thinking_level, prompt, image_b64):
    url = f"{API_BASE}/models/{model}:generateContent"
    body = {
        "contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/png", "data": image_b64}}]}],
        "generationConfig": {"temperature": 0, "thinkingConfig": {"thinkingLevel": thinking_level}},
    }
    resp = requests.post(url, params={"key": settings.gemini_api_key}, json=body, timeout=120)
    data = resp.json()
    return resp.status_code, data


def extract_text_and_usage(data):
    usage = data.get("usageMetadata", {})
    in_tok = usage.get("promptTokenCount", 0)
    total_tok = usage.get("totalTokenCount", 0)
    cand_tok = usage.get("candidatesTokenCount", 0)
    out_tok = max(0, total_tok - in_tok)  # same "total - prompt" convention as the pipeline
    candidates = data.get("candidates", [])
    finish_reason = candidates[0].get("finishReason") if candidates else None
    text = ""
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts)
    return text, in_tok, out_tok, cand_tok, total_tok, finish_reason


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = []
    cumulative_cost = 0.0

    for setting in SETTINGS:
        model = setting["model"]
        price = PRICE[model]
        for page_info in PAGES:
            book, page, pdf = page_info["book"], page_info["page"], page_info["pdf"]
            print(f"[{setting['label']}] {book} p{page} ...")

            image_b64 = image_to_base64_png(pdf, page)
            status, data = call_rest(model, setting["thinking_level"], pipeline.PROMPT, image_b64)

            if status != 200:
                print(f"  HTTP {status}: {json.dumps(data, ensure_ascii=False)[:300]}")
                rows.append(
                    {"setting": setting["label"], "model": model, "book": book, "page": page,
                     "status": f"HTTP_{status}", "input_tokens": 0, "output_tokens": 0,
                     "candidates_tokens": 0, "total_tokens": 0, "finish_reason": "", "cost_usd": 0.0}
                )
                continue

            text, in_tok, out_tok, cand_tok, total_tok, finish_reason = extract_text_and_usage(data)
            cost = (in_tok / 1000) * price["in"] + (out_tok / 1000) * price["out"]
            cumulative_cost += cost

            out_file = os.path.join(OUT_DIR, setting["label"], f"{book}_p{page}.txt")
            os.makedirs(os.path.dirname(out_file), exist_ok=True)
            with open(out_file, "w", encoding="utf-8") as fh:
                fh.write(text)

            print(f"  in={in_tok} out={out_tok} (candidates={cand_tok}, total={total_tok}) "
                  f"finish={finish_reason} cost=${cost:.5f} cumulative=${cumulative_cost:.4f}")

            rows.append(
                {"setting": setting["label"], "model": model, "book": book, "page": page,
                 "status": "OK", "input_tokens": in_tok, "output_tokens": out_tok,
                 "candidates_tokens": cand_tok, "total_tokens": total_tok,
                 "finish_reason": finish_reason, "cost_usd": round(cost, 6)}
            )

            if cumulative_cost >= BUDGET_STOP_USD:
                print(f"[STOP] cumulative cost ${cumulative_cost:.4f} reached the ${BUDGET_STOP_USD} safety stop.")
                write_log(rows)
                return

    write_log(rows)
    print(f"\nDone. Total cost this run: ${cumulative_cost:.4f}")


def write_log(rows):
    fieldnames = ["setting", "model", "book", "page", "status", "input_tokens", "output_tokens",
                  "candidates_tokens", "total_tokens", "finish_reason", "cost_usd"]
    with open(LOG_PATH, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {os.path.relpath(LOG_PATH, ROOT)}")


if __name__ == "__main__":
    main()
