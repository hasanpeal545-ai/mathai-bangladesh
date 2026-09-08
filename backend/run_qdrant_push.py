# STEP 5: embed all_chunks.json and push into Qdrant's "nctb_math_content" collection.
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastembed import TextEmbedding

from retrieval import vector_store

COLLECTION = "nctb_math_content"
EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
EMBEDDING_DIM = 1024
BATCH_SIZE = 50
CHUNKS_PATH = Path(__file__).resolve().parent / "data" / "approved" / "all_chunks.json"

TEST_QUERY = "সেট কাকে বলে"


def main():
    # 1. Check connection
    print("Checking Qdrant connection...", flush=True)
    exists = vector_store.collection_exists(COLLECTION)
    print(f"Qdrant reachable. Collection '{COLLECTION}' exists: {exists}", flush=True)

    # 2. Create collection if needed
    if not exists:
        vector_store.create_collection(COLLECTION, EMBEDDING_DIM)
        print(f"Created collection '{COLLECTION}' (size={EMBEDDING_DIM}, distance=Cosine)", flush=True)
    else:
        print(f"Collection '{COLLECTION}' already exists — skipping creation", flush=True)

    # 3. Load chunks
    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    total = len(chunks)
    print(f"Loaded {total} chunks from {CHUNKS_PATH}", flush=True)

    # Resume support: point IDs are sequential (0..total-1) matching chunk order,
    # so however many points already exist tells us exactly where to resume —
    # needed because long embedding runs on this machine eventually hit a memory
    # fragmentation crash (ONNX/numpy), and re-running from scratch each time
    # would waste the already-completed work.
    already_done = vector_store.get_collection_info(COLLECTION)["points_count"] if exists else 0
    if already_done:
        print(f"Resuming: {already_done} points already in collection, skipping to there", flush=True)

    # 4/5. Embed + push in batches of 50
    embedder = TextEmbedding(model_name=EMBEDDING_MODEL)
    pushed = already_done

    for batch_start in range(already_done, total, BATCH_SIZE):
        batch = chunks[batch_start : batch_start + BATCH_SIZE]
        # Embedding one text at a time — this machine has very little free RAM
        # (~2.7GB) relative to this model's size (~2.24GB); batching many texts
        # into one ONNX forward pass OOM'd on the first batch of 50.
        vectors = [list(embedder.embed([f"passage: {c['text']}"]))[0] for c in batch]

        points = []
        for offset, (chunk, vector) in enumerate(zip(batch, vectors)):
            point_id = batch_start + offset  # Qdrant needs int/UUID ids; chunk's own
            # string "id" is kept in the payload as "chunk_id" for traceability.
            payload = dict(chunk)
            payload["chunk_id"] = payload.pop("id")
            points.append({"id": point_id, "vector": vector.tolist(), "payload": payload})

        vector_store.upsert_points(COLLECTION, points)
        pushed += len(points)

        if pushed % 500 == 0 or pushed == total:
            print(f"Pushed {pushed}/{total} chunks", flush=True)

    # 6. Summary
    print("\n=== DONE ===")
    print(f"Total pushed: {pushed}")

    info = vector_store.get_collection_info(COLLECTION)
    print("\n=== COLLECTION INFO ===")
    print(json.dumps(info, ensure_ascii=False, indent=2))

    # 7. Test query
    print(f"\n=== TEST QUERY: {TEST_QUERY!r} ===")
    query_vector = list(embedder.embed([f"query: {TEST_QUERY}"]))[0].tolist()
    results = vector_store.search(COLLECTION, query_vector, limit=3)
    for i, r in enumerate(results, 1):
        payload = r["payload"]
        print(f"\n--- Result {i} (score={r['score']:.4f}) ---")
        print(f"  chunk_id: {payload.get('chunk_id')}")
        print(f"  class={payload.get('class')} book_type={payload.get('book_type')} language={payload.get('language')}")
        print(f"  chapter={payload.get('chapter')} ({payload.get('chapter_title')}) exercise={payload.get('exercise')}")
        print(f"  pages={payload.get('pages')} source_file={payload.get('source_file')}")
        print(f"  text: {payload.get('text', '')[:200]}")


if __name__ == "__main__":
    main()
