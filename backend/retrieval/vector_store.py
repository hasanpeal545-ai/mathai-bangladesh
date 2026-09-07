# Qdrant Cloud setup (raw REST over httpx — see requirements.txt for why not the qdrant-client SDK)
from typing import List

import httpx

from config import settings

GLOSSARY_COLLECTION = "math_glossary"

_client = httpx.Client(
    base_url=settings.qdrant_url,
    headers={"api-key": settings.qdrant_api_key},
    timeout=30.0,
)


def collection_exists(name: str) -> bool:
    response = _client.get(f"/collections/{name}")
    return response.status_code == 200


def create_collection(name: str, vector_size: int) -> None:
    response = _client.put(
        f"/collections/{name}",
        json={"vectors": {"size": vector_size, "distance": "Cosine"}},
    )
    response.raise_for_status()


def delete_collection(name: str) -> None:
    response = _client.delete(f"/collections/{name}")
    response.raise_for_status()


def upsert_points(name: str, points: List[dict]) -> None:
    response = _client.put(
        f"/collections/{name}/points",
        params={"wait": "true"},
        json={"points": points},
    )
    response.raise_for_status()


def search(name: str, vector: List[float], limit: int = 1) -> List[dict]:
    response = _client.post(
        f"/collections/{name}/points/search",
        json={"vector": vector, "limit": limit, "with_payload": True},
    )
    response.raise_for_status()
    return response.json()["result"]
