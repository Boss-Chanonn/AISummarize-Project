"""
schemas.py  —  Pydantic models for Learnova backend services
=============================================================
Defines all request/response data models used by the AI service layer.
These schemas enforce validation rules (field lengths, ranges, defaults)
so that every service method receives well-formed data.

Cross-references:
  - ai_service.py imports every model from this module
  - pptx_service.py imports SummaryResponse
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


def _clamp_question_count(value: int) -> int:
    """Clamp question count to the range [6, 8] as required by quiz endpoints."""
    return max(6, min(8, value))


# ── Summary ──────────────────────────────────────────────────────────────────

class SummaryRequest(BaseModel):
    """Input: raw document text + optional title to be summarised.

    Fields:
        text     — The full document body (min 200 chars).
        title    — Optional document title; defaults to "Untitled document".
        metadata — Arbitrary key/value pairs passed through from the client.
    """
    text: str = Field(..., min_length=200)
    title: str = Field(default="Untitled document", min_length=1, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SummaryResponse(BaseModel):
    """Output: AI-generated summary with structured sections.

    Fields:
        summary_title — Short title for the summary itself.
        authors       — Comma-separated author names extracted from text.
        overview      — 2-3 sentence high-level summary.
        body          — Array of 2-4 paragraph-length explanations.
        takeaways     — Array of 3-5 specific, falsifiable claims.
        topics        — Array of 3-6 noun-phrase study topics.
        chunks_used   — How many chunks the original text was split into (for long docs).
    """
    summary_title: str = Field(..., min_length=1, max_length=200)
    authors: str = Field(default="Unknown authors", max_length=200)
    overview: str = Field(default="", max_length=2000)
    body: list[str] = Field(default_factory=list, max_length=4)
    takeaways: list[str] = Field(default_factory=list, max_length=5)
    topics: list[str] = Field(default_factory=list, max_length=6)
    chunks_used: int = Field(default=1, ge=1)


class SummaryResponse(BaseModel):
    summary_title: str = Field(..., min_length=1, max_length=200)
    authors: str = Field(default="Unknown authors", max_length=200)
    overview: str = Field(default="", max_length=2000)
    body: list[str] = Field(default_factory=list, max_length=4)
    takeaways: list[str] = Field(default_factory=list, max_length=5)
    topics: list[str] = Field(default_factory=list, max_length=6)
    chunks_used: int = Field(default=1, ge=1)


# ── Quiz ──────────────────────────────────────────────────────────────────────

class QuizQuestion(BaseModel):
    """A single multiple-choice question with 4 options.

    Fields:
        question      — The question stem (never a verbatim copy from the summary).
        options       — Exactly 4 answer choices (A, B, C, D).
        correct_index — Index into options (0-3) of the correct answer.
        explanation   — Why the correct answer is right + why the top distractor is wrong.
        topic         — Noun-phrase topic this question belongs to (max 80 chars).
    """
    question: str = Field(..., min_length=1)
    options: list[str] = Field(default_factory=list, max_length=4)
    correct_index: int = Field(default=0, ge=0, le=3)
    explanation: str = Field(default="")
    topic: str = Field(default="General", max_length=80)


class QuizRequest(BaseModel):
    """Input: parameters for AI quiz generation.

    Fields:
        title             — Document title for context.
        summary           — Pre-generated SummaryResponse to ground questions.
        question_count    — Desired number of questions (clamped to 6-8).
        difficulty        — One of "easy", "intermediate", "hard", "targeted remediation".
        exclude_questions — Previous question stems to avoid repetition.
    """
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
    """Output: AI-generated quiz with the requested number of questions.

    Fields:
        title          — Quiz title (usually matches the document title).
        question_count — Actual number of questions generated (6-8).
        questions      — Array of QuizQuestion objects.
    """
    title: str = Field(..., min_length=1, max_length=200)
    question_count: int = Field(..., ge=6, le=8)
    questions: list[QuizQuestion] = Field(default_factory=list, max_length=8)


# ── Analysis & Review ──────────────────────────────────────────────────────────

class QuizAnswer(BaseModel):
    """A single user-submitted answer to a quiz question."""
    question_index: int = Field(..., ge=0)
    chosen_index: int = Field(..., ge=-1, le=3)      # -1 means "skipped"


class ReviewedQuestion(BaseModel):
    """A quiz question paired with the user's answer and correctness flag.

    This is the result of comparing a QuizQuestion with a QuizAnswer.
    Used in AnalyzeResultsResponse and as input to the learning module generator.
    """
    question: str = Field(..., min_length=1)
    topic: str = Field(default="General", max_length=80)
    user_answer: str = Field(default="Skipped")
    correct_answer: str = Field(default="")
    is_correct: bool = False
    explanation: str = Field(default="")


class AnalyzeResultsRequest(BaseModel):
    """Input: user's answers for a completed quiz, plus the original quiz/summary."""
    title: str = Field(..., min_length=1, max_length=200)
    summary: SummaryResponse
    questions: list[QuizQuestion] = Field(..., min_length=6, max_length=8)
    answers: list[QuizAnswer] = Field(default_factory=list, max_length=8)


class AnalyzeResultsResponse(BaseModel):
    """Output: scored quiz with AI-derived strengths, weaknesses, and recommendations."""
    score_percent: int = Field(..., ge=0, le=100)
    correct_count: int = Field(..., ge=0)
    total_questions: int = Field(..., ge=6, le=8)
    strengths: list[str] = Field(default_factory=list, max_length=4)
    weaknesses: list[str] = Field(default_factory=list, max_length=4)
    weak_topics: list[str] = Field(default_factory=list, max_length=4)
    study_recommendations: list[str] = Field(..., min_length=2, max_length=4)
    reviewed_questions: list[ReviewedQuestion] = Field(..., min_length=6, max_length=8)


# ── Learning Module ────────────────────────────────────────────────────────────

class MissedQuestion(BaseModel):
    """Lightweight version of ReviewedQuestion used as input for revision module generation."""
    question: str = Field(..., min_length=1)
    topic: str = Field(default="General", max_length=80)
    user_answer: str = Field(default="Skipped")
    correct_answer: str = Field(default="")
    explanation: str = Field(default="")


class LearningModuleRequest(BaseModel):
    """Input: quiz results used to generate a targeted revision module."""
    title: str = Field(..., min_length=1, max_length=200)
    summary: SummaryResponse
    weak_topics: list[str] = Field(default_factory=list, max_length=4)
    missed_questions: list[MissedQuestion] = Field(default_factory=list, max_length=8)


class LearningModuleSection(BaseModel):
    """One revision section within a LearningModule, focused on a single weak topic."""
    topic: str = Field(..., min_length=1, max_length=80)
    explanation: str = Field(default="", max_length=1000)
    why_it_matters: str = Field(default="", max_length=500)
    practice_tip: str = Field(default="", max_length=500)


class LearningModuleResponse(BaseModel):
    """Output: AI-generated revision module targeting the student's weak areas."""
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    focus_areas: list[str] = Field(default_factory=list, max_length=4)
    sections: list[LearningModuleSection] = Field(default_factory=list, max_length=4)
    study_plan: list[str] = Field(default_factory=list, max_length=5)


# ── Resource Recommendations ──────────────────────────────────────────────────

class ResourceRecommendation(BaseModel):
    """A single external resource (article, video, or podcast) recommended to the student."""
    topic: str = Field(..., min_length=2, max_length=80)
    title: str = Field(..., min_length=8, max_length=240)
    url: str = Field(..., min_length=8, max_length=1000)
    source: str = Field(..., min_length=2, max_length=120)
    snippet: str = Field(..., min_length=12, max_length=400)
    resource_type: str = Field(..., min_length=5, max_length=24)


class ResourceRecommendationRequest(BaseModel):
    """Input: context for AI to find relevant external resources."""
    title: str = Field(..., min_length=1, max_length=200)
    summary: SummaryResponse
    learning_module: LearningModuleResponse | None = None
    weak_topics: list[str] = Field(default_factory=list, max_length=4)


class ResourceRecommendationResponse(BaseModel):
    """Output: list of 2-6 deduplicated resource recommendations."""
    resources: list[ResourceRecommendation] = Field(..., min_length=2, max_length=6)


# ── Follow-Up Quiz ───────────────────────────────────────────────────────────

class FollowUpQuizRequest(BaseModel):
    """Input: parameters for a follow-up quiz targeting previously weak topics."""
    title: str = Field(..., min_length=1, max_length=200)
    summary: SummaryResponse
    weak_topics: list[str] = Field(default_factory=list, max_length=4)
    learning_module: LearningModuleResponse | None = None
    previous_questions: list[str] = Field(default_factory=list)
    question_count: int = Field(default=6)

    @field_validator("question_count")
    @classmethod
    def validate_question_count(cls, value: int) -> int:
        return _clamp_question_count(value)


class FollowUpQuizResponse(QuizResponse):
    """Output: follow-up quiz with an extra field identifying which topics were targeted."""
    target_topics: list[str] = Field(..., min_length=1, max_length=4)


# ── Progress Comparison ──────────────────────────────────────────────────────

class CompareProgressRequest(BaseModel):
    """Input: the student's initial and follow-up quiz results for comparison."""
    initial_result: AnalyzeResultsResponse
    follow_up_result: AnalyzeResultsResponse


class CompareProgressResponse(BaseModel):
    """Output: AI-generated progress narrative comparing two quiz attempts."""
    score_delta: int
    improved_topics: list[str] = Field(default_factory=list, max_length=4)
    remaining_weak_topics: list[str] = Field(default_factory=list, max_length=4)
    improvement_summary: str = Field(..., min_length=40)
    next_steps: list[str] = Field(..., min_length=2, max_length=4)