# Day 2 Gemini Vision run log

- Run started: 2026-10-06T14:17:37
- Model requested (from backend/config.py settings.gemini_model): `gemini-3.6-flash`
- Exact model name returned by the API: **not available** -- the installed `google-generativeai` SDK (v0.8.2, v1beta REST API) does not include a `model_version` field on `GenerateContentResponse` (checked the proto: only `candidates`, `prompt_feedback`, `usage_metadata` are present). The only confirmation available is that the call succeeded (no 404/NotFound) using the name above -- this is reported honestly rather than guessed.
- Temperature: 0
- Generation config: `{'temperature': 0}`
- Prompt sent (identical for every page):
  ```
  Transcribe this textbook page exactly as printed. Keep Bangla text in Bangla script and English in English. Write mathematical symbols as Unicode (∈ ∉ ∪ ∩ ∅ ∴ × − ⊂ ⊆, superscripts like ² ⁿ). Keep line breaks. Do not correct, translate, summarise, add or skip anything. Output only the transcription.
  ```

## Per-page results

| Page | Status | Characters | Error |
|---|---|---|---|
| bn_page_30 | OK (attempt 1) | 1836 |  |
| bn_page_36 | OK (attempt 1) | 1273 |  |
| bn_page_44 | OK (attempt 1) | 1405 |  |
| en_page_30 | FAILED (both attempts) | 0 | 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit.  * Quota exceeded for metric: generativelanguage.googlea |
| en_page_38 | FAILED (both attempts) | 0 | 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit.  * Quota exceeded for metric: generativelanguage.googlea |

---

## Run @ 2026-10-06T14:39:50

- Run started: 2026-10-06T14:39:50
- Model requested (from backend/config.py settings.gemini_model): `gemini-3.6-flash`
- Exact model name returned by the API: **not available** -- the installed `google-generativeai` SDK (v0.8.2, v1beta REST API) does not include a `model_version` field on `GenerateContentResponse` (checked the proto: only `candidates`, `prompt_feedback`, `usage_metadata` are present). The only confirmation available is that the call succeeded (no 404/NotFound) using the name above -- this is reported honestly rather than guessed.
- Temperature: 0
- Generation config: `{'temperature': 0}`
- Prompt sent (identical for every page):
  ```
  Transcribe this textbook page exactly as printed. Keep Bangla text in Bangla script and English in English. Write mathematical symbols as Unicode (∈ ∉ ∪ ∩ ∅ ∴ × − ⊂ ⊆, superscripts like ² ⁿ). Keep line breaks. Do not correct, translate, summarise, add or skip anything. Output only the transcription.
  ```

## Per-page results

| Page | Status | Characters | Error |
|---|---|---|---|
| en_page_30 | FAILED (both attempts) | 0 | 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit.  * Quota exceeded for metric: generativelanguage.googlea |
| en_page_38 | FAILED (both attempts) | 0 | 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit.  * Quota exceeded for metric: generativelanguage.googlea |

