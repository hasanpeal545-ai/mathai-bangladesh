# Environment variable / app config
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    groq_api_key: str = ""
    gemini_api_key: str = ""
    qdrant_url: str = ""
    qdrant_api_key: str = ""

    groq_model: str = "llama-3.3-70b-versatile"
    gemini_model: str = "gemini-2.5-flash"
    tiebreak_model: str = "openai/gpt-oss-120b"


settings = Settings()

# Admin PDF-preprocessing mode: True = admin OCR+LLM-fix pipeline is active (students never
# see this); False = production mode (students only get pre-approved, already-clean content).
PREPROCESSING_MODE = True
