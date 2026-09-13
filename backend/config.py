# Environment variable / app config
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    groq_api_key: str = ""
    gemini_api_key: str = ""
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    hf_token: str = ""

    groq_model: str = "qwen/qwen3.8-27b"
    gemini_model: str = "gemini-3.6-flash"
    tiebreak_model: str = "openai/gpt-oss-120b"


settings = Settings()

# huggingface_hub/fastembed read HF_TOKEN and HF_HUB_DISABLE_SYMLINKS_WARNING straight from
# the process environment, not from our Settings object — putting them in .env alone has no
# effect, since pydantic-settings only exposes the fields declared above. Mirror them into
# os.environ here, before fastembed's TextEmbedding is ever instantiated (glossary_engine.py,
# imported later in the chain), so they actually take effect.
if settings.hf_token:
    os.environ.setdefault("HF_TOKEN", settings.hf_token)
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

# Admin PDF-preprocessing mode: True = admin OCR+LLM-fix pipeline is active (students never
# see this); False = production mode (students only get pre-approved, already-clean content).
PREPROCESSING_MODE = True
