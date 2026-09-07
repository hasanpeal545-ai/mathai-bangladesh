# 3-tier glossary engine
from typing import List, Optional

from fastembed import TextEmbedding

from retrieval import term_learner, vector_store

EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
EMBEDDING_DIM = 1024
SIMILARITY_THRESHOLD = 0.85

MATH_GLOSSARY_SEED = {
    # জ্যামিতি
    "সমকোণী ত্রিভুজ": "Right-angled Triangle",
    "অতিভুজ": "Hypotenuse",
    "লম্ব": "Perpendicular",
    "ভূমি": "Base",
    "উচ্চতা": "Height",
    "বর্গক্ষেত্র": "Square",
    "আয়তক্ষেত্র": "Rectangle",
    "সামান্তরিক": "Parallelogram",
    "ট্রাপিজিয়াম": "Trapezium",
    "বৃত্ত": "Circle",
    "ব্যাসার্ধ": "Radius",
    "ব্যাস": "Diameter",
    "পরিধি": "Circumference",
    "চাপ": "Arc",
    "জ্যা": "Chord",
    "স্পর্শক": "Tangent",
    "কেন্দ্র": "Centre",
    "ক্ষেত্রফল": "Area",

    # বীজগণিত
    "সমীকরণ": "Equation",
    "চলক": "Variable",
    "সহগ": "Coefficient",
    "ধ্রুবক": "Constant",
    "বহুপদী": "Polynomial",
    "উৎপাদক": "Factor",
    "লসাগু": "LCM",
    "গসাগু": "GCD/HCF",
    "বর্গমূল": "Square Root",
    "ঘনমূল": "Cube Root",
    "সূচক": "Index/Exponent",
    "লগারিদম": "Logarithm",

    # পাটিগণিত
    "মূলধন": "Principal",
    "সুদ": "Interest",
    "মুনাফা": "Profit",
    "ক্ষতি": "Loss",
    "শতকরা": "Percentage",
    "অনুপাত": "Ratio",
    "সমানুপাত": "Proportion",
    "গড়": "Average/Mean",

    # ত্রিকোণমিতি
    "সাইন": "Sine",
    "কোসাইন": "Cosine",
    "ট্যানজেন্ট": "Tangent",
    "কোণ": "Angle",
    "সূক্ষ্মকোণ": "Acute Angle",
    "স্থূলকোণ": "Obtuse Angle",
    "সমকোণ": "Right Angle",

    # পরিসংখ্যান
    "মধ্যক": "Median",
    "প্রচুরক": "Mode",
    "গণসংখ্যা": "Frequency",
    "শ্রেণি": "Class Interval",
    "আয়তলেখ": "Histogram",
    "গণসংখ্যা বহুভুজ": "Frequency Polygon",
}

_embedder = TextEmbedding(model_name=EMBEDDING_MODEL)


# intfloat/e5 models are trained with asymmetric "query: " / "passage: " prefixes —
# text being stored/searched-over uses "passage: ", the search text uses "query: ".
def _embed_passage(text: str) -> list:
    return list(_embedder.embed([f"passage: {text}"]))[0].tolist()


def _embed_query(text: str) -> list:
    return list(_embedder.embed([f"query: {text}"]))[0].tolist()


def ensure_collection() -> None:
    if not vector_store.collection_exists(vector_store.GLOSSARY_COLLECTION):
        vector_store.create_collection(vector_store.GLOSSARY_COLLECTION, EMBEDDING_DIM)


def rebuild_collection() -> None:
    if vector_store.collection_exists(vector_store.GLOSSARY_COLLECTION):
        vector_store.delete_collection(vector_store.GLOSSARY_COLLECTION)
    vector_store.create_collection(vector_store.GLOSSARY_COLLECTION, EMBEDDING_DIM)


def embed_seed_glossary() -> int:
    rebuild_collection()
    points = []
    for idx, (bn_term, en_term) in enumerate(MATH_GLOSSARY_SEED.items()):
        points.append(
            {
                "id": idx,
                "vector": _embed_passage(bn_term),
                "payload": {"bn_term": bn_term, "en_term": en_term},
            }
        )
    vector_store.upsert_points(vector_store.GLOSSARY_COLLECTION, points)
    return len(points)


def lookup_exact(term: str) -> Optional[str]:
    return MATH_GLOSSARY_SEED.get(term.strip())


def lookup_semantic(term: str) -> Optional[dict]:
    vector = _embed_query(term.strip())
    results = vector_store.search(vector_store.GLOSSARY_COLLECTION, vector, limit=1)
    if not results:
        return None
    top = results[0]
    if top["score"] < SIMILARITY_THRESHOLD:
        return None
    return {
        "bn_term": top["payload"]["bn_term"],
        "en_term": top["payload"]["en_term"],
        "score": top["score"],
    }


def translate(term: str) -> dict:
    exact = lookup_exact(term)
    if exact is not None:
        return {"tier": 1, "bn_term": term, "en_term": exact, "score": 1.0}

    semantic = lookup_semantic(term)
    if semantic is not None:
        return {"tier": 2, **semantic}

    learned = term_learner.learn_term(term, _embed_passage)
    return {"tier": 3, "bn_term": term, "en_term": learned["en_term"], "score": None}


def find_terms_in_text(text: str) -> List[dict]:
    """Find known Bangla glossary terms appearing in a piece of text (e.g. a student query)."""
    found = []
    covered_spans = []
    for bn_term, en_term in sorted(MATH_GLOSSARY_SEED.items(), key=lambda kv: -len(kv[0])):
        start = text.find(bn_term)
        if start == -1:
            continue
        end = start + len(bn_term)
        if any(s <= start and end <= e for s, e in covered_spans):
            continue  # already covered by a longer overlapping match
        covered_spans.append((start, end))
        found.append({"bn_term": bn_term, "en_term": en_term})
    return found


def find_english_terms_in_text(text: str) -> List[dict]:
    """Find known glossary English terms leaking into a piece of text (e.g. an LLM's Bangla solution)."""
    found = []
    seen_en = set()
    text_lower = text.lower()
    for bn_term, en_term in MATH_GLOSSARY_SEED.items():
        if en_term in seen_en:
            continue
        if en_term.lower() in text_lower:
            found.append({"bn_term": bn_term, "en_term": en_term})
            seen_en.add(en_term)
    return found
