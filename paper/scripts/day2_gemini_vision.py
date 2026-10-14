"""Day 2 / Task B: Gemini Vision transcription of the 5 selected page images.

Reuses the Gemini call pattern + API key loading from backend/test_gemini_vision.py
and backend/config.py (model name comes from settings.gemini_model, never hardcoded
here). Sends each of paper/page_images/{lang}_page_{N}.png the exact prompt specified
in paper/tasks/DAY2.md and saves the output to
paper/gemini_vision/{lang}_page_{N}.txt (UTF-8).

Budget rule (DAY2.md): "Max 5 Gemini API requests in total (plus at most 1 retry per
failed page)." There are exactly 5 images, so this script makes exactly 1 generateContent
call per image (5 total) unless a call raises, in which case it retries that SAME image
once more. If a failure looks like the configured model name itself being invalid
(a 404 / NotFound from the API), the script stops immediately and does NOT touch the
remaining images or silently fall back to a different model name -- per DAY2.md: "If the
model name fails, STOP and ask Peal."

Optionally restrict which pages to run via CLI args, e.g.:
    python day2_gemini_vision.py en_page_30 en_page_38
(used by DAY3.md Task A to retry just the 2 pages that failed on quota in Day 2).
With no args, runs the full default TARGETS list (original Day 2 behaviour). Each run
is APPENDED to RUN_LOG.md (not overwritten) so earlier runs' history is kept.
"""
import datetime
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND_DIR = os.path.join(ROOT, "backend")
sys.path.insert(0, BACKEND_DIR)

from config import settings  # noqa: E402  (reuses backend's .env loading)

import google.generativeai as genai  # noqa: E402
import google.api_core.exceptions as gexc  # noqa: E402
from PIL import Image  # noqa: E402

IMG_DIR = os.path.join(ROOT, "paper", "page_images")
OUT_DIR = os.path.join(ROOT, "paper", "gemini_vision")
LOG_PATH = os.path.join(OUT_DIR, "RUN_LOG.md")

TARGETS = ["bn_page_30", "bn_page_36", "bn_page_44", "en_page_30", "en_page_38"]

PROMPT = (
    "Transcribe this textbook page exactly as printed. Keep Bangla text in Bangla "
    "script and English in English. Write mathematical symbols as Unicode "
    "(∈ ∉ ∪ ∩ ∅ ∴ × − ⊂ ⊆, superscripts "
    "like ² ⁿ). Keep line breaks. Do not correct, translate, summarise, add "
    "or skip anything. Output only the transcription."
)

TEMPERATURE = 0  # deterministic, literal transcription -- no creative sampling wanted
GENERATION_CONFIG = {"temperature": TEMPERATURE}


def is_model_not_found(exc):
    """True only for errors that indicate the *model name itself* is invalid,
    as opposed to transient/quota/safety errors that deserve a per-page retry."""
    if isinstance(exc, gexc.NotFound):
        return True
    msg = str(exc).lower()
    return "not found" in msg and "model" in msg


def call_gemini(model, image_path):
    image = Image.open(image_path)
    response = model.generate_content(
        [PROMPT, image], generation_config=GENERATION_CONFIG
    )
    return response.text


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    targets = sys.argv[1:] if len(sys.argv) > 1 else TARGETS

    genai.configure(api_key=settings.gemini_api_key)
    model_name = settings.gemini_model
    model = genai.GenerativeModel(model_name)

    run_started = datetime.datetime.now().isoformat(timespec="seconds")
    log_rows = []  # (name, status, char_count, error)
    stopped_early = None

    for name in targets:
        image_path = os.path.join(IMG_DIR, f"{name}.png")
        if not os.path.exists(image_path):
            log_rows.append((name, "SKIPPED", 0, f"image not found: {image_path}"))
            print(f"[SKIP] {name}: image not found at {image_path}")
            continue

        attempt = 1
        last_error = None
        while attempt <= 2:
            try:
                text = call_gemini(model, image_path)
                out_path = os.path.join(OUT_DIR, f"{name}.txt")
                with open(out_path, "w", encoding="utf-8") as fh:
                    fh.write(text)
                log_rows.append((name, f"OK (attempt {attempt})", len(text), ""))
                print(f"[OK] {name}: {len(text)} chars -> {os.path.relpath(out_path, ROOT)}")
                last_error = None
                break
            except Exception as e:  # noqa: BLE001 -- need to inspect any API error
                last_error = e
                if is_model_not_found(e):
                    print(f"[STOP] Model name '{model_name}' appears invalid: {e}")
                    stopped_early = (name, str(e))
                    break
                print(f"[WARN] {name} attempt {attempt} failed: {e}")
                attempt += 1

        if stopped_early:
            log_rows.append((name, "MODEL_NAME_FAILED", 0, str(last_error)))
            break
        if last_error is not None:
            log_rows.append((name, "FAILED (both attempts)", 0, str(last_error)))
            print(f"[FAIL] {name}: giving up after 2 attempts -- {last_error}")

    write_run_log(run_started, model_name, log_rows, stopped_early)

    if stopped_early:
        print()
        print("=" * 70)
        print(f"STOPPED: model '{model_name}' failed on {stopped_early[0]}.")
        print("Per DAY2.md instructions, not silently switching models.")
        print("Ask Peal for the correct Gemini model name before re-running.")
        print("=" * 70)
        sys.exit(1)


def write_run_log(run_started, model_name, log_rows, stopped_early):
    is_new_file = not os.path.exists(LOG_PATH)
    lines = []
    if is_new_file:
        lines.append("# Day 2 Gemini Vision run log\n")
    else:
        lines.append(f"---\n\n## Run @ {run_started}\n")
    lines.append(f"- Run started: {run_started}")
    lines.append(f"- Model requested (from backend/config.py settings.gemini_model): `{model_name}`")
    lines.append(
        "- Exact model name returned by the API: **not available** -- the installed "
        "`google-generativeai` SDK (v0.8.2, v1beta REST API) does not include a "
        "`model_version` field on `GenerateContentResponse` (checked the proto: only "
        "`candidates`, `prompt_feedback`, `usage_metadata` are present). The only "
        "confirmation available is that the call succeeded (no 404/NotFound) using the "
        "name above -- this is reported honestly rather than guessed."
    )
    lines.append(f"- Temperature: {TEMPERATURE}")
    lines.append(f"- Generation config: `{GENERATION_CONFIG}`")
    lines.append("- Prompt sent (identical for every page):")
    lines.append("  ```")
    lines.append(f"  {PROMPT}")
    lines.append("  ```")
    lines.append("")
    lines.append("## Per-page results")
    lines.append("")
    lines.append("| Page | Status | Characters | Error |")
    lines.append("|---|---|---|---|")
    for name, status, chars, error in log_rows:
        err = error.replace("\n", " ")[:300] if error else ""
        lines.append(f"| {name} | {status} | {chars} | {err} |")
    lines.append("")
    if stopped_early:
        lines.append(
            f"## STOPPED EARLY\nModel `{model_name}` failed on page `{stopped_early[0]}` "
            f"with what looks like a model-not-found error:\n\n```\n{stopped_early[1]}\n```\n\n"
            "Per DAY2.md: stopped and did not silently switch to a different model name. "
            "Remaining pages were not attempted. Needs Peal's decision on the correct "
            "model name before re-running this script."
        )
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"\nRUN_LOG {'written' if is_new_file else 'appended'} -> {os.path.relpath(LOG_PATH, ROOT)}")


if __name__ == "__main__":
    main()
