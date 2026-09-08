# Multi-LLM solver
from dataclasses import dataclass, field
from typing import List, Optional

from retrieval.glossary_engine import find_english_terms_in_text, find_terms_in_text
from retrieval.retriever import retrieve
from solving.class_standards import get_class_standard
from solving.cross_checker import CrossCheckResult, cross_check

_NO_RAG_CONTEXT_NOTE = "RAG context পাওয়া যায়নি"


_SSC_FORMAT_EXAMPLE_BN = (
    "উদাহরণঃ\n"
    "প্রশ্নঃ একটি ত্রিভুজের ভূমি ৮ সেমি এবং উচ্চতা ৫ সেমি, ক্ষেত্রফল কত?\n"
    "সমাধানঃ\n"
    "দেওয়া আছে,\n"
    "ত্রিভুজের ভূমি = ৮ সেমি\n"
    "উচ্চতা = ৫ সেমি\n"
    "আমরা জানি,\n"
    "ক্ষেত্রফল = ½ × ভূমি × উচ্চতা\n"
    "সূত্রমতে,\n"
    "ক্ষেত্রফল = ½ × ৮ × ৫\n"
    "= ২০ বর্গ সেমি (উত্তর)"
)

_SSC_FORMAT_EXAMPLE_EN = (
    "Example:\n"
    "Question: The base of a triangle is 8 cm and the height is 5 cm. Find the area.\n"
    "Solution:\n"
    "Given,\n"
    "Base of the triangle = 8 cm\n"
    "Height = 5 cm\n"
    "We know,\n"
    "Area = ½ × base × height\n"
    "By the formula,\n"
    "Area = ½ × 8 × 5\n"
    "= 20 sq. cm (Answer)"
)


def _apply_glossary_hints(query: str, glossary_terms: List[dict]) -> str:
    if not glossary_terms:
        return query
    hints = "; ".join(f"{t['bn_term']} = {t['en_term']}" for t in glossary_terms)
    return f"{query}\n\n[Glossary reference — সঠিক পরিভাষা: {hints}]"


def build_prompt(
    query: str,
    class_number: Optional[int],
    glossary_terms: List[dict],
    language: str = "bn",
) -> str:
    query_with_hints = _apply_glossary_hints(query, glossary_terms)

    if class_number is None:
        if language == "en":
            return f"Answer in English.\n\nQuestion: {query_with_hints}"
        return query_with_hints

    standard = get_class_standard(class_number)

    if class_number in (9, 10):
        if language == "en":
            return (
                f"{_SSC_FORMAT_EXAMPLE_EN}\n\n"
                "Following the exact format of the example above — without copying its labels "
                "verbatim — fill in the real numbers and calculations at each step and write the "
                "complete solution to the question below, in English. The answer must start with "
                "'Solution:' and end with '(Answer)'.\n\n"
                f"Question: {query_with_hints}"
            )
        return (
            f"{_SSC_FORMAT_EXAMPLE_BN}\n\n"
            "উপরের উদাহরণের ঠিক এই ফরম্যাট অনুসরণ করে, লেবেলগুলো কপি না করে প্রতিটি ধাপে "
            "আসল সংখ্যা ও হিসাব বসিয়ে নিচের প্রশ্নের সম্পূর্ণ সমাধান লেখো। "
            "উত্তর অবশ্যই 'সমাধানঃ' শব্দ দিয়ে শুরু করবে এবং শেষে '(উত্তর)' লিখে শেষ করবে।\n\n"
            f"প্রশ্নঃ {query_with_hints}"
        )

    if language == "en":
        return (
            "You are a Bangladesh math teacher. Explain the solution step by step in English, "
            f"at a complexity appropriate for class {standard.class_range}.\n\n"
            f"Question: {query_with_hints}"
        )
    return (
        "তুমি একজন Bangladesh Math শিক্ষক। বাংলায় ধাপে ধাপে সমাধান করবে।\n"
        f"নিয়মঃ {standard.style_description}\n\n"
        f"প্রশ্নঃ {query_with_hints}"
    )


@dataclass
class SolveResult:
    cross_check: CrossCheckResult
    query_glossary_terms: List[dict]
    solution_glossary_terms: List[dict]
    retrieved_chunks: List[dict] = field(default_factory=list)
    rag_note: Optional[str] = None


def _apply_rag_context(prompt: str, chunks: List[dict]) -> str:
    context = "\n\n".join(c["text"] for c in chunks)
    return (
        f"নিচের NCTB পাঠ্যবই থেকে প্রাসঙ্গিক অংশ:\n{context}\n\n"
        "উপরের অংশটি ব্যবহার করে নিচের প্রশ্নের সমাধান দাও।\n\n"
        f"{prompt}"
    )


def solve(
    query: str,
    mode: str = "direct",
    class_number: Optional[int] = None,
    language: str = "bn",
    book_type: Optional[str] = None,
    chapter: Optional[int] = None,
    exercise: Optional[str] = None,
    problem_number: Optional[int] = None,
) -> SolveResult:
    query_glossary_terms = find_terms_in_text(query)
    base_prompt = build_prompt(query, class_number, query_glossary_terms, language)

    if mode == "reference":
        # Reference mode: narrow retrieval to the exact class/book/chapter/exercise
        # the student pointed at.
        retrieved_chunks = retrieve(
            query,
            class_number=class_number,
            book_type=book_type,
            chapter=chapter,
            exercise=exercise,
            problem_number=problem_number,
            language=language,
        )
    else:
        # Direct mode: pure semantic search, no structural filters (only scoped to
        # the query's own language so an English question doesn't pull Bangla chunks).
        retrieved_chunks = retrieve(query, language=language)

    if retrieved_chunks:
        rag_note = None
        prompt = _apply_rag_context(base_prompt, retrieved_chunks)
    else:
        rag_note = _NO_RAG_CONTEXT_NOTE
        prompt = base_prompt

    result = cross_check(prompt)
    solution_glossary_terms = find_english_terms_in_text(result.final_answer or "")

    return SolveResult(
        cross_check=result,
        query_glossary_terms=query_glossary_terms,
        solution_glossary_terms=solution_glossary_terms,
        retrieved_chunks=retrieved_chunks,
        rag_note=rag_note,
    )
