# Learnova AI services package
from .ai_service import AIService
from .ollama_client import OllamaClient, OllamaError, OllamaSettings
from .schemas import (
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

__all__ = [
    "AIService",
    "OllamaClient",
    "OllamaError",
    "OllamaSettings",
    "AnalyzeResultsRequest",
    "AnalyzeResultsResponse",
    "CompareProgressRequest",
    "CompareProgressResponse",
    "FollowUpQuizRequest",
    "FollowUpQuizResponse",
    "LearningModuleRequest",
    "LearningModuleResponse",
    "QuizRequest",
    "QuizResponse",
    "ResourceRecommendationRequest",
    "ResourceRecommendationResponse",
    "SummaryRequest",
    "SummaryResponse",
]
