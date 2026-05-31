"""
Learnova AI Routes
==================
Registers all AI endpoints on the main FastAPI app.

HOW TO INTEGRATE — one edit in backend/main.py:
    from backend.routes.ai import router as ai_router
    app.include_router(ai_router, prefix="/api/ai", tags=["ai"])
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from backend.services.ai_service import AIService
from backend.services.ollama_client import (
    OllamaClient,
    OllamaError,
    SummaryOllamaSettings,
    QuizOllamaSettings,
)
from backend.services.schemas import (
    AnalyzeResultsRequest,
    AnalyzeResultsResponse,
    CompareProgressRequest,
    CompareProgressResponse,
    FollowUpQuizRequest,
    FollowUpQuizResponse,
    LearningModuleRequest,
    LearningModuleResponse,
    QuizRequest,
    QuizResponse,
    ResourceRecommendationRequest,
    ResourceRecommendationResponse,
    SummaryRequest,
    SummaryResponse,
)

router = APIRouter()

# ── Service (dual-Mac) ────────────────────────────────────────────────────────
_service = AIService(
    client=OllamaClient(SummaryOllamaSettings()),   # Mac 1 — gpt-oss     — summarise
    quiz_client=OllamaClient(QuizOllamaSettings()), # Mac 2 — deepseek    — quiz
)

# ── In-memory job store ───────────────────────────────────────────────────────
# Each entry: { "status": "pending"|"done"|"error", "result": QuizResponse|None, "error": str|None }
_quiz_jobs: dict[str, dict[str, Any]] = {}


# ── Helpers ───────────────────────────────────────────────────────────────────
def _handle(exc: Exception) -> None:
    import traceback
    print(f"[ai_route] ERROR type={type(exc).__name__} msg={exc}", flush=True)
    traceback.print_exc()
    if isinstance(exc, OllamaError):
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    raise HTTPException(status_code=500, detail="Unexpected AI service error.") from exc


# ── Schemas for combined endpoint ─────────────────────────────────────────────
class SummarizeAndQueueRequest(BaseModel):
    title: str
    text: str
    question_count: int = 6
    difficulty: str = "medium"
    exclude_questions: list[str] = []


class SummarizeAndQueueResponse(BaseModel):
    summary: SummaryResponse
    job_id: str
    quiz_status: str = "pending"


class QuizStatusResponse(BaseModel):
    job_id: str
    status: str               # "pending" | "done" | "error"
    result: QuizResponse | None = None
    error: str | None = None


# ── Background quiz job ───────────────────────────────────────────────────────
def _run_quiz_job(job_id: str, payload: QuizRequest) -> None:
    """Runs in the background — generates quiz on Mac 2, stores result in job store."""
    try:
        result = _service.generate_quiz(payload)
        _quiz_jobs[job_id] = {"status": "done", "result": result, "error": None}
    except Exception as exc:
        _quiz_jobs[job_id] = {"status": "error", "result": None, "error": str(exc)}


# ── Health ────────────────────────────────────────────────────────────────────
@router.get("/health")
def ai_health() -> dict:
    """Check both Macs and report status separately."""
    summary_status, quiz_status = "ok", "ok"
    try:
        _service.client.health()
    except OllamaError:
        summary_status = "unavailable"
    try:
        _service.quiz_client.health()
    except OllamaError:
        quiz_status = "unavailable"

    summary_settings = SummaryOllamaSettings()
    quiz_settings    = QuizOllamaSettings()
    return {
        "summary_service": {
            "status": summary_status,
            "model": summary_settings.model,
            "url": summary_settings.base_url,
        },
        "quiz_service": {
            "status": quiz_status,
            "model": quiz_settings.model,
            "url": quiz_settings.base_url,
        },
    }


# ── Combined endpoint — summary now, quiz later ───────────────────────────────
@router.post("/summarize-and-queue-quiz", response_model=SummarizeAndQueueResponse)
async def summarize_and_queue_quiz(
    payload: SummarizeAndQueueRequest,
    background_tasks: BackgroundTasks,
) -> SummarizeAndQueueResponse:
    """
    1. Calls Mac 1 (gpt-oss) synchronously for the summary — returns immediately.
    2. Fires quiz generation on Mac 2 (deepseek-r1:8b) as a background task.
    3. Returns the summary + a job_id to poll with GET /ai/quiz-status/{job_id}.
    """
    # Step 1 — summarise on Mac 1 (blocks until done)
    try:
        summary = _service.summarize(SummaryRequest(title=payload.title, text=payload.text))
    except Exception as exc:
        _handle(exc)

    # Step 2 — queue quiz on Mac 2
    job_id = str(uuid.uuid4())
    _quiz_jobs[job_id] = {"status": "pending", "result": None, "error": None}

    quiz_payload = QuizRequest(
        title=payload.title,
        summary=summary,
        question_count=max(6, min(8, payload.question_count)),
        difficulty=payload.difficulty,
        exclude_questions=payload.exclude_questions,
    )
    background_tasks.add_task(_run_quiz_job, job_id, quiz_payload)

    return SummarizeAndQueueResponse(summary=summary, job_id=job_id, quiz_status="pending")


# ── Polling endpoint ──────────────────────────────────────────────────────────
@router.get("/quiz-status/{job_id}", response_model=QuizStatusResponse)
def quiz_status(job_id: str) -> QuizStatusResponse:
    """Frontend polls this every 3 seconds until status is 'done' or 'error'."""
    job = _quiz_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"No quiz job found for id: {job_id}")
    return QuizStatusResponse(
        job_id=job_id,
        status=job["status"],
        result=job.get("result"),
        error=job.get("error"),
    )


# ── Existing endpoints (unchanged) ────────────────────────────────────────────
@router.post("/summarize", response_model=SummaryResponse)
def summarize(payload: SummaryRequest) -> SummaryResponse:
    try:
        return _service.summarize(payload)
    except Exception as exc:
        _handle(exc)


@router.post("/quiz", response_model=QuizResponse)
def quiz(payload: QuizRequest) -> QuizResponse:
    try:
        return _service.generate_quiz(payload)
    except Exception as exc:
        _handle(exc)


@router.post("/analyze-results", response_model=AnalyzeResultsResponse)
def analyze_results(payload: AnalyzeResultsRequest) -> AnalyzeResultsResponse:
    try:
        return _service.analyze_results(payload)
    except Exception as exc:
        _handle(exc)


@router.post("/learning-module", response_model=LearningModuleResponse)
def learning_module(payload: LearningModuleRequest) -> LearningModuleResponse:
    try:
        return _service.generate_learning_module(payload)
    except Exception as exc:
        _handle(exc)


@router.post("/recommend-resources", response_model=ResourceRecommendationResponse)
def recommend_resources(payload: ResourceRecommendationRequest) -> ResourceRecommendationResponse:
    try:
        return _service.recommend_resources(payload)
    except Exception as exc:
        _handle(exc)


@router.post("/follow-up-quiz", response_model=FollowUpQuizResponse)
def follow_up_quiz(payload: FollowUpQuizRequest) -> FollowUpQuizResponse:
    try:
        return _service.generate_follow_up_quiz(payload)
    except Exception as exc:
        _handle(exc)


@router.post("/compare-progress", response_model=CompareProgressResponse)
def compare_progress(payload: CompareProgressRequest) -> CompareProgressResponse:
    try:
        return _service.compare_progress(payload)
    except Exception as exc:
        _handle(exc)