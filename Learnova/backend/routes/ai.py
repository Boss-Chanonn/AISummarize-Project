"""
Learnova AI Routes  —  feature/ai-service-kunal
================================================
Drop-in router for the main FastAPI app.

HOW TO INTEGRATE (one edit in backend/main.py):
    from backend.routes.ai import router as ai_router
    app.include_router(ai_router, prefix="/api/ai", tags=["ai"])

All endpoints are protected by the same JWT dependency already
used across the project — just import and pass it as a dependency
if/when the team wants to add auth guards here too.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.services import (
    AIService,
    OllamaError,
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
_service = AIService()


def _handle(exc: Exception) -> None:
    """Translate service errors into clean HTTP responses."""
    if isinstance(exc, OllamaError):
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    raise HTTPException(status_code=500, detail="Unexpected AI service error.") from exc


@router.get("/health")
def ai_health() -> dict:
    """Quick health-check — returns Ollama status and active model."""
    from backend.services import OllamaSettings
    settings = OllamaSettings()
    try:
        _service.client.health()
        status = "ok"
    except OllamaError:
        status = "unavailable"
    return {"status": status, "model": settings.model, "ollama_base_url": settings.base_url}


@router.post("/summarize", response_model=SummaryResponse)
def summarize(payload: SummaryRequest) -> SummaryResponse:
    """Generate a structured summary from document text."""
    try:
        return _service.summarize(payload)
    except Exception as exc:
        _handle(exc)


@router.post("/quiz", response_model=QuizResponse)
def quiz(payload: QuizRequest) -> QuizResponse:
    """Generate a multiple-choice quiz from a document summary."""
    try:
        return _service.generate_quiz(payload)
    except Exception as exc:
        _handle(exc)


@router.post("/analyze-results", response_model=AnalyzeResultsResponse)
def analyze_results(payload: AnalyzeResultsRequest) -> AnalyzeResultsResponse:
    """Score answers and return strengths, weak topics, and study recommendations."""
    try:
        return _service.analyze_results(payload)
    except Exception as exc:
        _handle(exc)


@router.post("/learning-module", response_model=LearningModuleResponse)
def learning_module(payload: LearningModuleRequest) -> LearningModuleResponse:
    """Build a targeted learning module focused on the user's weak topics."""
    try:
        return _service.generate_learning_module(payload)
    except Exception as exc:
        _handle(exc)


@router.post("/recommend-resources", response_model=ResourceRecommendationResponse)
def recommend_resources(payload: ResourceRecommendationRequest) -> ResourceRecommendationResponse:
    """Search and return real article / video / podcast links per weak topic."""
    try:
        return _service.recommend_resources(payload)
    except Exception as exc:
        _handle(exc)


@router.post("/follow-up-quiz", response_model=FollowUpQuizResponse)
def follow_up_quiz(payload: FollowUpQuizRequest) -> FollowUpQuizResponse:
    """Generate a follow-up quiz targeting topics the user got wrong."""
    try:
        return _service.generate_follow_up_quiz(payload)
    except Exception as exc:
        _handle(exc)


@router.post("/compare-progress", response_model=CompareProgressResponse)
def compare_progress(payload: CompareProgressRequest) -> CompareProgressResponse:
    """Compare initial vs follow-up quiz performance and surface improvement metrics."""
    try:
        return _service.compare_progress(payload)
    except Exception as exc:
        _handle(exc)
