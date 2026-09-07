# Self-learning glossary
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List

from groq import Groq

from config import settings
from retrieval import vector_store

LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "glossary_learning_log.txt"

_groq_client = Groq(api_key=settings.groq_api_key)

TIER3_PROMPT = (
    "তুমি Bangladesh SSC Math teacher। এই term এর formal academic English translation দাও। "
    "Casual English use করবে না। শুধু translation দাও, অন্য কিছু লিখবে না।\n\n"
    "Term: {term}"
)


def ask_llm_for_translation(term: str) -> str:
    completion = _groq_client.chat.completions.create(
        model=settings.groq_model,
        messages=[{"role": "user", "content": TIER3_PROMPT.format(term=term)}],
        max_tokens=30,
    )
    answer = completion.choices[0].message.content.strip()
    return answer.splitlines()[0].strip(' "\'.')


def log_new_term(bn_term: str, en_term: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    line = f"[{timestamp}] নতুন term শিখেছি: {bn_term} → {en_term}. Admin approval দরকার\n"
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line)


def learn_term(term: str, embed_passage_fn: Callable[[str], List[float]]) -> dict:
    en_term = ask_llm_for_translation(term)

    vector_store.upsert_points(
        vector_store.GLOSSARY_COLLECTION,
        [
            {
                "id": str(uuid.uuid4()),
                "vector": embed_passage_fn(term),
                "payload": {
                    "bn_term": term,
                    "en_term": en_term,
                    "source": "llm_tier3",
                    "approved": False,
                },
            }
        ],
    )

    log_new_term(term, en_term)

    return {"bn_term": term, "en_term": en_term}
