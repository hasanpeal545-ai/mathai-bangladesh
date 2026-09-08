# Smart retrieval logic — embeds a query and searches Qdrant's nctb_math_content collection
from typing import List, Optional

from retrieval import vector_store
from retrieval.glossary_engine import get_embedder

COLLECTION = "nctb_math_content"


def _build_filter(
    class_number: Optional[int],
    book_type: Optional[str],
    chapter: Optional[int],
    exercise: Optional[str],
    language: Optional[str],
) -> Optional[dict]:
    field_values = {
        "class": class_number,
        "book_type": book_type,
        "chapter": chapter,
        "exercise": exercise,
        "language": language,
    }
    conditions = [
        {"key": field, "match": {"value": value}}
        for field, value in field_values.items()
        if value is not None
    ]
    return {"must": conditions} if conditions else None


def retrieve(
    query: str,
    class_number: Optional[int] = None,
    book_type: Optional[str] = None,
    chapter: Optional[int] = None,
    exercise: Optional[str] = None,
    problem_number: Optional[int] = None,
    language: str = "bn",
    top_k: int = 3,
) -> List[dict]:
    embedder = get_embedder()
    vector = list(embedder.embed([f"query: {query}"]))[0].tolist()

    query_filter = _build_filter(class_number, book_type, chapter, exercise, language)
    results = vector_store.search(COLLECTION, vector, limit=top_k, query_filter=query_filter)

    chunks = []
    for r in results:
        payload = r.get("payload", {})
        chunks.append(
            {
                "score": r.get("score"),
                "text": payload.get("text", ""),
                "chunk_id": payload.get("chunk_id"),
                "class": payload.get("class"),
                "book_type": payload.get("book_type"),
                "language": payload.get("language"),
                "chapter": payload.get("chapter"),
                "chapter_title": payload.get("chapter_title"),
                "exercise": payload.get("exercise"),
                "problem_number": payload.get("problem_number"),
                "pages": payload.get("pages"),
                "source_file": payload.get("source_file"),
            }
        )
    return chunks
