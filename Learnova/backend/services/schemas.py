from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


def _clamp_question_count(value: int) -> int:
    return max(6, min(8, value))


class SummaryRequest(BaseModel):
    text: str = Field(..., min_length=200)
    title: str = Field(default="Untitled document", min_length=1, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SummaryResponse(BaseModel):
    summary_title: str = Field(..., min_length=1, max_length=200)
    authors: str = Field(default="Unknown authors", max_length=200)
    overview: str = Field(..., min_length=80)
    body: list[str] = Field(..., min_length=2, max_length=4)
    takeaways: list[str] = Field(..., min_length=3, max_length=5)
    topics: list[str] = Field(..., min_length=3, max_length=6)
    chunks_used: int = Field(default=1, ge=1)


class QuizQuestion(BaseModel):
    question: str = Field(..., min_length=12)
    options: list[str] = Field(..., min_length=4, max_length=4)
    correct_index: int = Field(..., ge=0, le=3)
    explanation: str = Field(..., min_length=20)
    topic: str = Field(..., min_length=2, max_length=80)


class QuizRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    summary: SummaryResponse
    question_count: int = Field(default=6)
    difficulty: str = Field(default="intermediate", min_length=3, max_length=24)
    exclude_questions: list[str] = Field(default_factory=list)

    @field_validator("question_count")
    @classmethod
    def validate_question_count(cls, value: int) -> int:
        return _clamp_question_count(value)


class QuizResponse(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    question_count: int = Field(..., ge=6, le=8)
    questions: list[QuizQuestion] = Field(..., min_length=6, max_length=8)


class QuizAnswer(BaseModel):
    question_index: int = Field(..., ge=0)
    chosen_index: int = Field(..., ge=-1, le=3)


class ReviewedQuestion(BaseModel):
    question: str = Field(..., min_length=12)
    topic: str = Field(..., min_length=2, max_length=80)
    user_answer: str = Field(..., min_length=1)
    correct_answer: str = Field(..., min_length=1)
    is_correct: bool
    explanation: str = Field(..., min_length=20)


class AnalyzeResultsRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    summary: SummaryResponse
    questions: list[QuizQuestion] = Field(..., min_length=6, max_length=8)
    answers: list[QuizAnswer] = Field(..., min_length=6, max_length=8)


class AnalyzeResultsResponse(BaseModel):
    score_percent: int = Field(..., ge=0, le=100)
    correct_count: int = Field(..., ge=0)
    total_questions: int = Field(..., ge=6, le=8)
    strengths: list[str] = Field(default_factory=list, max_length=4)
    weaknesses: list[str] = Field(default_factory=list, max_length=4)
    weak_topics: list[str] = Field(default_factory=list, max_length=4)
    study_recommendations: list[str] = Field(..., min_length=2, max_length=4)
    reviewed_questions: list[ReviewedQuestion] = Field(..., min_length=6, max_length=8)


class MissedQuestion(BaseModel):
    question: str = Field(..., min_length=12)
    topic: str = Field(..., min_length=2, max_length=80)
    user_answer: str = Field(..., min_length=1)
    correct_answer: str = Field(..., min_length=1)
    explanation: str = Field(..., min_length=20)


class LearningModuleRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    summary: SummaryResponse
    weak_topics: list[str] = Field(..., min_length=1, max_length=4)
    missed_questions: list[MissedQuestion] = Field(default_factory=list, max_length=8)


class LearningModuleSection(BaseModel):
    topic: str = Field(..., min_length=2, max_length=80)
    explanation: str = Field(..., min_length=50)
    why_it_matters: str = Field(..., min_length=25)
    practice_tip: str = Field(..., min_length=20)


class LearningModuleResponse(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=60)
    focus_areas: list[str] = Field(..., min_length=2, max_length=4)
    sections: list[LearningModuleSection] = Field(..., min_length=2, max_length=4)
    study_plan: list[str] = Field(..., min_length=3, max_length=5)


class ResourceRecommendation(BaseModel):
    topic: str = Field(..., min_length=2, max_length=80)
    title: str = Field(..., min_length=8, max_length=240)
    url: str = Field(..., min_length=8, max_length=1000)
    source: str = Field(..., min_length=2, max_length=120)
    snippet: str = Field(..., min_length=12, max_length=400)
    resource_type: str = Field(..., min_length=5, max_length=24)


class ResourceRecommendationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    summary: SummaryResponse
    learning_module: LearningModuleResponse
    weak_topics: list[str] = Field(default_factory=list, max_length=4)


class ResourceRecommendationResponse(BaseModel):
    resources: list[ResourceRecommendation] = Field(..., min_length=2, max_length=6)


class FollowUpQuizRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    summary: SummaryResponse
    weak_topics: list[str] = Field(..., min_length=1, max_length=4)
    learning_module: LearningModuleResponse
    previous_questions: list[str] = Field(default_factory=list)
    question_count: int = Field(default=6)

    @field_validator("question_count")
    @classmethod
    def validate_question_count(cls, value: int) -> int:
        return _clamp_question_count(value)


class FollowUpQuizResponse(QuizResponse):
    target_topics: list[str] = Field(..., min_length=1, max_length=4)


class CompareProgressRequest(BaseModel):
    initial_result: AnalyzeResultsResponse
    follow_up_result: AnalyzeResultsResponse


class CompareProgressResponse(BaseModel):
    score_delta: int
    improved_topics: list[str] = Field(default_factory=list, max_length=4)
    remaining_weak_topics: list[str] = Field(default_factory=list, max_length=4)
    improvement_summary: str = Field(..., min_length=40)
    next_steps: list[str] = Field(..., min_length=2, max_length=4)
