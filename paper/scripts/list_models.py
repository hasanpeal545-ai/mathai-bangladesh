"""Step 3d.1: list available Gemini models via raw REST (models.list), bypassing
the outdated google-generativeai==0.8.2 SDK entirely (per FULL_OCR.md: "Do NOT
touch backend/venv. Create a separate venv... or call the REST API with
requests" -- using requests, already present in backend/venv, with no package
install/upgrade of any kind). Free call, no token cost.

Writes paper/results/AVAILABLE_MODELS.md.
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND_DIR = os.path.join(ROOT, "backend")
sys.path.insert(0, BACKEND_DIR)

from config import settings  # noqa: E402

import requests  # noqa: E402

API_BASE = "https://generativelanguage.googleapis.com/v1beta"
OUT_PATH = os.path.join(ROOT, "paper", "results", "AVAILABLE_MODELS.md")


def list_models():
    models = []
    page_token = None
    while True:
        params = {"key": settings.gemini_api_key, "pageSize": 1000}
        if page_token:
            params["pageToken"] = page_token
        resp = requests.get(f"{API_BASE}/models", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        models.extend(data.get("models", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return models


def main():
    models = list_models()
    lines = [f"# Available Gemini models for this API key ({len(models)} total)\n"]
    lines.append("Fetched via raw REST `GET /v1beta/models` (free, no token cost) -- bypasses the "
                  "outdated `google-generativeai==0.8.2` SDK installed in backend/venv entirely.\n")
    lines.append("| name | displayName | supportedGenerationMethods | inputTokenLimit | outputTokenLimit |")
    lines.append("|---|---|---|---|---|")
    flash_like = []
    for m in sorted(models, key=lambda x: x.get("name", "")):
        name = m.get("name", "")
        display = m.get("displayName", "")
        methods = ", ".join(m.get("supportedGenerationMethods", []))
        in_limit = m.get("inputTokenLimit", "")
        out_limit = m.get("outputTokenLimit", "")
        lines.append(f"| `{name}` | {display} | {methods} | {in_limit} | {out_limit} |")
        if "flash" in name.lower():
            flash_like.append(m)

    lines.append("\n## Full raw JSON for every model whose name contains \"flash\" (for thinking-field inspection)\n")
    for m in flash_like:
        lines.append(f"### `{m.get('name')}`")
        lines.append("```json")
        lines.append(json.dumps(m, indent=2, ensure_ascii=False))
        lines.append("```")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"Wrote {OUT_PATH} ({len(models)} models, {len(flash_like)} flash-like)")
    for m in flash_like:
        print(" -", m.get("name"))


if __name__ == "__main__":
    main()
