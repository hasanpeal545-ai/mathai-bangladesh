# LLM cross-check logic
import re
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from groq import Groq, RateLimitError

from config import settings

_groq_client = Groq(api_key=settings.groq_api_key)
genai.configure(api_key=settings.gemini_api_key)

_BANGLA_TO_ARABIC_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
_RATE_LIMIT_ERRORS = (RateLimitError, ResourceExhausted)


def extract_number(text: str) -> Optional[str]:
    normalized = text.translate(_BANGLA_TO_ARABIC_DIGITS)
    matches = re.findall(r"-?\d+(?:\.\d+)?", normalized)
    return matches[-1] if matches else None


def solve_with_groq(query: str, model: Optional[str] = None) -> str:
    completion = _groq_client.chat.completions.create(
        model=model or settings.groq_model,
        messages=[{"role": "user", "content": query}],
        max_tokens=600,
    )
    return completion.choices[0].message.content.strip()


def solve_with_gemini(query: str) -> str:
    model = genai.GenerativeModel(settings.gemini_model)
    response = model.generate_content(query)
    return response.text.strip()


def _safe_solve(solve_fn: Callable[[str], str], query: str) -> Tuple[Optional[str], Optional[str]]:
    try:
        return solve_fn(query), None
    except _RATE_LIMIT_ERRORS:
        return None, "rate_limited"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


@dataclass
class CrossCheckResult:
    query: str
    groq_answer: Optional[str] = None
    gemini_answer: Optional[str] = None
    groq_number: Optional[str] = None
    gemini_number: Optional[str] = None
    groq_error: Optional[str] = None
    gemini_error: Optional[str] = None
    tiebreak_used: bool = False
    tiebreak_answer: Optional[str] = None
    tiebreak_number: Optional[str] = None
    tiebreak_error: Optional[str] = None
    final_answer: Optional[str] = None
    final_number: Optional[str] = None
    match: bool = False
    confidence: str = "FAILED"  # HIGH | MEDIUM | LOW | SINGLE_SOURCE | FAILED


def cross_check(query: str) -> CrossCheckResult:
    groq_answer, groq_error = _safe_solve(solve_with_groq, query)
    gemini_answer, gemini_error = _safe_solve(solve_with_gemini, query)

    result = CrossCheckResult(
        query=query,
        groq_answer=groq_answer,
        gemini_answer=gemini_answer,
        groq_number=extract_number(groq_answer) if groq_answer else None,
        gemini_number=extract_number(gemini_answer) if gemini_answer else None,
        groq_error=groq_error,
        gemini_error=gemini_error,
    )

    if groq_answer and gemini_answer:
        _resolve_both_available(result)
    elif groq_answer:
        result.confidence = "SINGLE_SOURCE"
        result.final_answer = groq_answer
        result.final_number = result.groq_number
    elif gemini_answer:
        result.confidence = "SINGLE_SOURCE"
        result.final_answer = gemini_answer
        result.final_number = result.gemini_number
    else:
        result.confidence = "FAILED"

    return result


def _resolve_both_available(result: CrossCheckResult) -> None:
    if result.groq_number is not None and result.groq_number == result.gemini_number:
        result.match = True
        result.confidence = "HIGH"
        result.final_answer = result.groq_answer
        result.final_number = result.groq_number
        return

    result.tiebreak_used = True
    tiebreak_answer, tiebreak_error = _safe_solve(
        lambda q: solve_with_groq(q, model=settings.tiebreak_model), result.query
    )
    result.tiebreak_answer = tiebreak_answer
    result.tiebreak_error = tiebreak_error
    result.tiebreak_number = extract_number(tiebreak_answer) if tiebreak_answer else None

    if result.tiebreak_number is not None and result.tiebreak_number == result.groq_number:
        result.confidence = "MEDIUM"
        result.final_answer = result.groq_answer
        result.final_number = result.groq_number
    elif result.tiebreak_number is not None and result.tiebreak_number == result.gemini_number:
        result.confidence = "MEDIUM"
        result.final_answer = result.gemini_answer
        result.final_number = result.gemini_number
    else:
        result.confidence = "LOW"
        result.final_answer = result.groq_answer
        result.final_number = result.groq_number
