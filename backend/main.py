# FastAPI entry point
import json
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import config
from ingestion.pdf_extractor import (
    APPROVED_DIR,
    COMPARISON_DIR,
    build_summary,
    process_page_with_llm_fix,
)
from solving.solver import solve

app = FastAPI(title="MathAI Bangladesh API")

# Dev frontend runs on Vite's default port; without this the browser blocks
# /api/chat calls from localhost:5173 with a CORS error before they reach here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_CONFIDENCE_SCORE_MAP = {
    "HIGH": 0.95,
    "MEDIUM": 0.7,
    "SINGLE_SOURCE": 0.5,
    "LOW": 0.4,
    "FAILED": 0.0,
}


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


class ChatRequest(BaseModel):
    query: str = Field(min_length=1)
    mode: Literal["reference", "direct"]
    class_: Optional[int] = Field(default=None, ge=6, le=10, alias="class")
    chapter: Optional[int] = Field(default=None, ge=1)
    exercise: Optional[int] = Field(default=None, ge=1)
    step_mode: bool = False
    practice_mode: bool = False
    exam_mode: bool = False
    language: Literal["bn", "en"] = "bn"


class ChatResponse(BaseModel):
    solution: str
    explanation: str
    figure: Optional[dict] = None
    next_step: Optional[str] = None
    practice_question: Optional[str] = None
    confidence_score: float
    llm_agreement: bool
    error_analysis: Optional[str] = None
    glossary_terms: Optional[List[dict]] = None


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    solve_result = solve(request.query, request.class_, request.language)
    result = solve_result.cross_check
    glossary_terms = solve_result.query_glossary_terms + solve_result.solution_glossary_terms

    if result.final_answer is None:
        return ChatResponse(
            solution="দুঃখিত, এই মুহূর্তে কোনো LLM থেকে উত্তর পাওয়া যায়নি। একটু পর আবার চেষ্টা করো।",
            explanation=f"groq_error={result.groq_error}, gemini_error={result.gemini_error}",
            confidence_score=0.0,
            llm_agreement=False,
            error_analysis="both LLM providers failed or rate-limited",
            glossary_terms=glossary_terms or None,
        )

    return ChatResponse(
        solution=result.final_answer,
        explanation=(
            f"confidence={result.confidence}, groq_gemini_match={result.match}, "
            f"tiebreak_used={result.tiebreak_used}"
        ),
        confidence_score=_CONFIDENCE_SCORE_MAP.get(result.confidence, 0.0),
        llm_agreement=result.match,
        glossary_terms=glossary_terms or None,
    )


class PreprocessRequest(BaseModel):
    pdf_path: str
    page_number: int = Field(ge=1)


@app.post("/api/admin/preprocess")
def admin_preprocess(request: PreprocessRequest):
    if not config.PREPROCESSING_MODE:
        raise HTTPException(status_code=403, detail="PREPROCESSING_MODE is off (production mode) — preprocessing disabled")

    pdf_path = Path(request.pdf_path)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"PDF not found: {pdf_path}")

    return process_page_with_llm_fix(pdf_path, request.page_number)


@app.get("/api/admin/comparison/{page}")
def admin_comparison(page: int):
    path = COMPARISON_DIR / f"page_{page}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No comparison saved for page {page}")
    return json.loads(path.read_text(encoding="utf-8"))


@app.post("/api/admin/approve/{page}")
def admin_approve(page: int):
    path = COMPARISON_DIR / f"page_{page}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No comparison saved for page {page}")

    data = json.loads(path.read_text(encoding="utf-8"))
    data["approved"] = True
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    APPROVED_DIR.mkdir(parents=True, exist_ok=True)
    chunks_path = APPROVED_DIR / "chunks.json"
    chunks = json.loads(chunks_path.read_text(encoding="utf-8")) if chunks_path.exists() else []
    chunks.append({"page": data["page"], "chapter": data["chapter"], "content": data["fixed"]})
    chunks_path.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"page": page, "status": "approved", "chunks_total": len(chunks)}


@app.post("/api/admin/reject/{page}")
def admin_reject(page: int):
    path = COMPARISON_DIR / f"page_{page}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No comparison saved for page {page}")

    data = json.loads(path.read_text(encoding="utf-8"))
    data["approved"] = False
    data["manual_review_needed"] = True
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"page": page, "status": "rejected", "manual_review_needed": True}


@app.get("/api/admin/summary")
def admin_summary():
    return build_summary()
