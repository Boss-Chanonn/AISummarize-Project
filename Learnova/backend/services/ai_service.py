"""
ai_service.py  —  Learnova AI layer  (v2)
=========================================
Key improvements over v1:
  1. Richer prompts with concrete examples and Bloom's taxonomy levels
  2. AI-powered analysis and progress comparison (not just Python set ops)
  3. Learning module sections grounded in the actual document text
  4. Difficulty calibration with real behavioural descriptions
  5. Condensed merge prompt (sends overviews, not full JSON dumps)
  6. Consistent timeout/fallback on all external HTTP calls
  7. Smarter weak-topic detection using question-level evidence
  8. Quiz uniqueness check is case-and-punctuation normalised
"""
from __future__ import annotations

import json
import os
import re
from collections import Counter
from html import unescape
from typing import TypeVar
from urllib.error import URLError
from urllib.parse import quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

from pydantic import BaseModel, ValidationError

from .ollama_client import OllamaClient, OllamaError, SummaryOllamaSettings, QuizOllamaSettings
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
    ResourceRecommendation,
    ResourceRecommendationRequest,
    ResourceRecommendationResponse,
    ReviewedQuestion,
    SummaryRequest,
    SummaryResponse,
)

ModelT = TypeVar("ModelT", bound=BaseModel)  # Generic bound for structured output parsing

# ── Difficulty descriptors ────────────────────────────────────────────────────
_DIFFICULTY_DESCRIPTORS: dict[str, str] = {
    "easy": (
        "Questions must target direct recall — facts, definitions, and named concepts "
        "that appear explicitly in the text. A student who read once should get 80%+."
    ),
    "intermediate": (
        "Mix recall (40%) with comprehension (40%) and simple application (20%). "
        "Ask students to explain why something is true, compare two ideas, or identify "
        "the implication of a finding. Avoid trivially googleable answers."
    ),
    "hard": (
        "Prioritise analysis, evaluation, and synthesis (Bloom levels 4-6). "
        "Questions should require connecting ideas across sections, identifying "
        "unstated assumptions, evaluating evidence quality, or applying concepts to "
        "new scenarios described in the options. A student who skimmed should score below 50%."
    ),
    "targeted remediation": (
        "Every question must directly address a topic the student got wrong before. "
        "Ask the same concept from a different angle — new scenario, different phrasing, "
        "or testing a prerequisite they may have missed. Never reword a previous question."
    ),
}

_DEFAULT_DIFFICULTY = "intermediate"


class AIService:
    """Central AI orchestration layer for Learnova.

    Manages two OllamaClient instances:
      - client (Mac 1 / gpt-oss) for summarisation, analysis, and learning modules
      - quiz_client (Mac 2 / deepseek-r1:8b) for quiz generation

    Every public method accepts a Pydantic request model and returns a Pydantic
    response model, ensuring type safety and validation throughout the pipeline.

    Cross-references:
      - Most methods delegate prompt construction to private _*_prompt() methods.
      - Response normalisation is handled by _normalize_model_payload().
      - Resource search uses DuckDuckGo HTML scraping and YouTube search.
    """

    def __init__(
        self,
        client: OllamaClient | None = None,
        quiz_client: OllamaClient | None = None,
    ) -> None:
        """Initialise with two optional Ollama clients.

        If not provided, defaults are created:
          - client:      SummaryOllamaSettings() → gpt-oss on Mac 1
          - quiz_client: QuizOllamaSettings()    → deepseek-r1:8b on Mac 2
        """
        self.client      = client      or OllamaClient(SummaryOllamaSettings())  # Mac 1 — gpt-oss
        self.quiz_client = quiz_client or OllamaClient(QuizOllamaSettings())     # Mac 2 — deepseek

    # ── Public API ────────────────────────────────────────────────────────────

    def summarize(self, payload: SummaryRequest) -> SummaryResponse:
        """Generate an AI summary of the given document.

        For long documents (> 4000 chars), the text is split into chunks,
        each chunk is summarised independently, and the chunk summaries are
        merged into a single cohesive summary.

        Args:
            payload: SummaryRequest with text (min 200 chars) and optional title.

        Returns:
            SummaryResponse with overview, body, takeaways, topics, etc.

        Raises:
            ValueError: If the cleaned text is shorter than 200 characters.
        """
        text = self._clean_text(payload.text)
        if len(text) < 200:
            raise ValueError("Document text is too short. Provide at least 200 characters.")

        chunks = self._chunk_text(text)
        if len(chunks) == 1:
            summary = self._generate_structured(
                self._summary_prompt(payload.title, chunks[0]),
                SummaryResponse,
            )
            return summary.model_copy(update={"chunks_used": 1})

        chunk_summaries = [
            self._generate_structured(
                self._chunk_summary_prompt(payload.title, i + 1, len(chunks), chunk),
                SummaryResponse,
            )
            for i, chunk in enumerate(chunks)
        ]
        merged = self._generate_structured(
            self._merge_summary_prompt(payload.title, chunk_summaries),
            SummaryResponse,
        )
        return merged.model_copy(update={"chunks_used": len(chunks)})

    def generate_quiz(self, payload: QuizRequest) -> QuizResponse:
        """Generate a multiple-choice quiz based on a document summary.

        Args:
            payload: QuizRequest with summary, difficulty, question count, etc.

        Returns:
            QuizResponse with generated questions, each having 4 options.
        """
        question_count = max(6, min(8, payload.question_count))
        prompt = self._quiz_prompt(
            title=payload.title,
            summary=payload.summary,
            question_count=question_count,
            difficulty=payload.difficulty,
            exclude_questions=payload.exclude_questions,
            follow_up=False,
        )
        response = self._generate_structured(prompt, QuizResponse, use_quiz_client=True)
        self._assert_unique_questions(response.questions)
        return response.model_copy(update={"question_count": question_count})

    def analyze_results(self, payload: AnalyzeResultsRequest) -> AnalyzeResultsResponse:
        """Score the user's quiz answers and derive AI-powered strengths/weaknesses.

        Delegates to the AI for rich analysis (v2 improvement over simple topic counting)
        but falls back to Python logic (_derive_strengths, _derive_weak_topics) if the
        AI call fails.

        Args:
            payload: AnalyzeResultsRequest with questions and user answers.

        Returns:
            AnalyzeResultsResponse with score, strengths, weaknesses, and review.
        """
        review = self._build_reviewed_questions(payload)
        correct_count = sum(1 for item in review if item.is_correct)
        total_questions = len(review)
        score_percent = round((correct_count / total_questions) * 100)

        # Use AI to derive rich analysis — not just Counter logic
        analysis = self._ai_analyze_results(
            title=payload.title,
            summary=payload.summary,
            review=review,
            score_percent=score_percent,
        )

        return AnalyzeResultsResponse(
            score_percent=score_percent,
            correct_count=correct_count,
            total_questions=total_questions,
            strengths=analysis.get("strengths", self._derive_strengths(review, payload.summary.topics)),
            weaknesses=analysis.get("weaknesses", self._derive_weak_topics(review, payload.summary.topics)[:4]),
            weak_topics=analysis.get("weak_topics", self._derive_weak_topics(review, payload.summary.topics)),
            study_recommendations=analysis.get("study_recommendations", self._derive_recommendations([], payload.summary.topics)),
            reviewed_questions=review,
        )

    def generate_learning_module(self, payload: LearningModuleRequest) -> LearningModuleResponse:
        """Generate a targeted revision module for the student's weak areas.

        The AI creates focus areas, explanation sections, and a study plan
        grounded in the specific questions the student got wrong.

        Args:
            payload: LearningModuleRequest with missed questions and weak topics.

        Returns:
            LearningModuleResponse with sections and study plan.
        """
        prompt = self._learning_module_prompt(payload)
        return self._generate_structured(prompt, LearningModuleResponse)

    def generate_follow_up_quiz(self, payload: FollowUpQuizRequest) -> FollowUpQuizResponse:
        """Generate a follow-up quiz targeting the student's previously weak topics.

        Uses "targeted remediation" difficulty — every question directly addresses
        a topic the student got wrong before, from a different angle.

        Args:
            payload: FollowUpQuizRequest with weak topics and previous questions.

        Returns:
            FollowUpQuizResponse with questions + target_topics field.
        """
        question_count = max(6, min(8, payload.question_count))
        prompt = self._quiz_prompt(
            title=payload.title,
            summary=payload.summary,
            question_count=question_count,
            difficulty="targeted remediation",
            exclude_questions=payload.previous_questions,
            follow_up=True,
            weak_topics=payload.weak_topics,
            module=payload.learning_module,
        )
        response = self._generate_structured(prompt, FollowUpQuizResponse, use_quiz_client=True)
        self._assert_unique_questions(response.questions)
        self._assert_no_repeated_questions(response.questions, payload.previous_questions)
        return response.model_copy(
            update={"question_count": question_count, "target_topics": payload.weak_topics[:4]}
        )

    def recommend_resources(
        self, payload: ResourceRecommendationRequest
    ) -> ResourceRecommendationResponse:
        """Search for external learning resources (articles, videos, podcasts).

        Searches DuckDuckGo HTML results, YouTube, ListenNotes, and Wikipedia
        for each relevant topic. Deduplicates by URL and caps at 4 resources.

        Args:
            payload: ResourceRecommendationRequest with weak topics / module.

        Returns:
            ResourceRecommendationResponse with up to 4 deduplicated resources.
        """
        # Safe topic extraction — learning_module may be None
        lm_focus = []
        if payload.learning_module and hasattr(payload.learning_module, "focus_areas"):
            lm_focus = payload.learning_module.focus_areas or []

        # Truncate topics to 80 chars max (ResourceRecommendation.topic limit)
        def _safe_topic(t: str) -> str:
            t = t.strip()
            return t[:77] + "..." if len(t) > 80 else t

        raw_topics = (
            payload.weak_topics[:3]
            or lm_focus[:3]
            or payload.summary.topics[:3]
            or [payload.title]
        )
        target_topics = [_safe_topic(t) for t in raw_topics]

        resources: list[ResourceRecommendation] = []

        for topic in target_topics:
            # Only add what's actually found — no forced article+video+podcast per topic
            try:
                video = self._search_video_resource(payload.title, topic)
                if video:
                    resources.append(video)
            except Exception:
                pass

            try:
                article = self._search_article_resource(payload.title, topic)
                if article:
                    resources.append(article)
            except Exception:
                pass

            try:
                podcast = self._search_podcast_resource(payload.title, topic)
                if podcast:
                    resources.append(podcast)
            except Exception:
                pass

            # Stop once we have 4 resources
            if len(resources) >= 4:
                break

        # Deduplicate by URL, cap at 4
        deduped: list[ResourceRecommendation] = []
        seen_urls: set[str] = set()
        for resource in resources:
            if resource.url in seen_urls:
                continue
            deduped.append(resource)
            seen_urls.add(resource.url)
            if len(deduped) == 4:
                break

        return ResourceRecommendationResponse(resources=deduped)

    def compare_progress(self, payload: CompareProgressRequest) -> CompareProgressResponse:
        """Compare the student's initial and follow-up quiz results.

        First attempts AI-powered analysis (_ai_compare_progress) for a rich
        narrative. Falls back to set-based Python logic (topic subtraction +
        score delta) if the AI call fails.

        Args:
            payload: CompareProgressRequest with initial and follow-up results.

        Returns:
            CompareProgressResponse with score_delta, improved/remaining topics, etc.
        """
        # Use AI for meaningful progress insight instead of pure set subtraction
        analysis = self._ai_compare_progress(payload)
        if analysis:
            return analysis

        # Fallback to Python logic if AI fails
        initial_weak = set(payload.initial_result.weak_topics)
        follow_weak  = set(payload.follow_up_result.weak_topics)
        improved     = sorted(initial_weak - follow_weak)
        remaining    = sorted(follow_weak)
        score_delta  = payload.follow_up_result.score_percent - payload.initial_result.score_percent

        return CompareProgressResponse(
            score_delta=score_delta,
            improved_topics=improved[:4],
            remaining_weak_topics=remaining[:4],
            improvement_summary=self._build_improvement_summary(score_delta, improved, remaining),
            next_steps=self._build_next_steps(improved, remaining),
        )

    # ── Core generation ───────────────────────────────────────────────────────

    def _generate_structured(
        self,
        prompt: str,
        model_type: type[ModelT],
        retries: int = 2,
        use_quiz_client: bool = False,
    ) -> ModelT:
        """Send a prompt to Ollama and parse the response into a Pydantic model.

        Retries up to `retries` times (default 2) on OllamaError or ValidationError.
        Uses the quiz_client (Mac 2 / deepseek) when use_quiz_client is True,
        otherwise uses the default client (Mac 1 / gpt-oss).

        Args:
            prompt:      The full prompt string for the AI model.
            model_type:  The Pydantic model class to validate against.
            retries:     Number of additional retries on failure.
            use_quiz_client: If True, uses quiz_client instead of the default client.

        Returns:
            An instance of model_type with validated data.

        Raises:
            ValueError: If all retries are exhausted without valid output.
        """
        errors: list[str] = []
        for _ in range(retries + 1):
            try:
                active_client = self.quiz_client if use_quiz_client else self.client
                data = active_client.generate_json(prompt)
                data = self._normalize_model_payload(model_type, data)
                return model_type.model_validate(data)
            except (OllamaError, ValidationError) as exc:
                errors.append(str(exc))
        raise ValueError("AI output validation failed: " + " | ".join(errors))

    # ── AI-powered analysis (v2 improvements) ─────────────────────────────────

    def _ai_analyze_results(
        self,
        title: str,
        summary: SummaryResponse,
        review: list[ReviewedQuestion],
        score_percent: int,
    ) -> dict:
        """
        Use the AI to derive strengths, weaknesses and recommendations
        from the actual question-answer evidence rather than just counting topics.
        Falls back to Python logic on failure.
        """
        correct   = [r for r in review if r.is_correct]
        incorrect = [r for r in review if not r.is_correct]

        correct_json   = json.dumps([{"question": r.question, "topic": r.topic} for r in correct])
        incorrect_json = json.dumps([
            {"question": r.question, "topic": r.topic,
             "user_answer": r.user_answer, "correct_answer": r.correct_answer,
             "explanation": r.explanation}
            for r in incorrect
        ])

        prompt = f"""You are a learning coach analysing a student's quiz results.
Return strict JSON only with these exact keys:
strengths, weaknesses, weak_topics, study_recommendations

Rules:
- strengths: 2-4 strings naming what the student understands well (topic + why).
- weaknesses: 2-4 strings naming specific gaps (not just topic names — explain the gap).
- weak_topics: 2-4 short topic labels the student struggled with most.
- study_recommendations: 2-4 concrete, actionable next steps tied to the missed content.
  Example good recommendation: "Re-read the methodology section and focus on how X differs from Y."
  Example bad recommendation: "Review core concepts."
- Be specific to this document. Never write generic advice.

Document: {title}
Score: {score_percent}%
Topics in document: {', '.join(summary.topics)}

Correct answers ({len(correct)} questions):
{correct_json}

Incorrect answers ({len(incorrect)} questions):
{incorrect_json}
"""
        try:
            data = self.client.generate_json(prompt)
            return {
                "strengths": self._ensure_string_list(data.get("strengths", []), max_items=4),
                "weaknesses": self._ensure_string_list(data.get("weaknesses", []), max_items=4),
                "weak_topics": self._ensure_string_list(data.get("weak_topics", []), max_items=4),
                "study_recommendations": self._ensure_string_list(data.get("study_recommendations", []), max_items=4),
            }
        except Exception:
            return {}

    def _ai_compare_progress(self, payload: CompareProgressRequest) -> CompareProgressResponse | None:
        """Use AI to generate a meaningful progress narrative. Returns None on failure."""
        initial  = payload.initial_result
        followup = payload.follow_up_result
        delta    = followup.score_percent - initial.score_percent

        prompt = f"""You are a learning coach comparing two quiz results for the same student.
Return strict JSON only with these exact keys:
score_delta, improved_topics, remaining_weak_topics, improvement_summary, next_steps

Rules:
- score_delta: integer (positive = improvement).
- improved_topics: list of 0-4 topics that clearly improved.
- remaining_weak_topics: list of 0-4 topics still needing work.
- improvement_summary: 1-2 sentences. Be specific about what changed and why it matters.
  Good: "Your score improved by 15 points, with notably stronger answers on methodology —
        the practice tip on study design appears to have worked."
  Bad: "You improved on some topics."
- next_steps: 2-4 specific actions. Reference actual topic names.
- Never be generic. Every sentence must relate to these specific results.

Initial quiz:  score={initial.score_percent}%, weak_topics={initial.weak_topics}
Follow-up quiz: score={followup.score_percent}%, weak_topics={followup.weak_topics}
Score delta: {delta}
Initial strengths: {initial.strengths}
Follow-up strengths: {followup.strengths}
"""
        try:
            data = self.client.generate_json(prompt)
            return CompareProgressResponse(
                score_delta=int(data.get("score_delta", delta)),
                improved_topics=self._ensure_string_list(data.get("improved_topics", []), max_items=4),
                remaining_weak_topics=self._ensure_string_list(data.get("remaining_weak_topics", []), max_items=4),
                improvement_summary=str(data.get("improvement_summary", ""))[:600] or self._build_improvement_summary(delta, [], []),
                next_steps=self._ensure_string_list(data.get("next_steps", []), max_items=4),
            )
        except Exception:
            return None

    # ── Prompts ───────────────────────────────────────────────────────────────

    def _summary_prompt(self, title: str, text: str) -> str:
        return f"""You are generating a learner-friendly academic summary for a study platform.
Return strict JSON only with these exact keys:
summary_title, authors, overview, body, takeaways, topics, chunks_used

Field rules:
- summary_title: concise title (max 100 chars). If the document has a clear title, use it.
- authors: real names if found in the text, otherwise "Unknown authors".
- overview: 2-3 sentences capturing the document's central argument or purpose. Be specific.
- body: array of 2-4 paragraphs. Each paragraph must cover a distinct section of the document
  (e.g. background, method, findings, implications). Do not repeat the overview.
  Each paragraph must be 40-100 words.
- takeaways: array of 3-5 strings. Each must be a specific, falsifiable claim from the document.
  Good example: "The study found a 23% reduction in error rate when using method X."
  Bad example: "The document covers important findings."
- topics: array of 3-6 specific study topics a student should know after reading. Use noun phrases.
- chunks_used: 1

Document title: {title}
Document text (full):
\"\"\"{text[:5500]}\"\"\"
"""

    def _chunk_summary_prompt(self, title: str, index: int, total: int, text: str) -> str:
        return f"""You are summarizing chunk {index} of {total} from an academic document.
Return strict JSON only with these exact keys:
summary_title, authors, overview, body, takeaways, topics, chunks_used

Rules:
- Focus only on what this chunk covers — do not invent content from other parts.
- body: exactly 2 paragraphs, each 40-80 words.
- takeaways: exactly 3 specific claims from this chunk.
- topics: 2-4 study topics found in this chunk.
- authors: extract if visible, otherwise "Unknown authors".
- chunks_used: 1

Document title: {title}
Chunk {index} of {total}:
\"\"\"{text[:5500]}\"\"\"
"""

    def _merge_summary_prompt(self, title: str, chunk_summaries: list[SummaryResponse]) -> str:
        # Send condensed versions — overviews and takeaways only, not full JSON
        condensed = [
            f"Chunk {i + 1}: {s.overview}\nKey points: {'; '.join(s.takeaways)}\nTopics: {', '.join(s.topics)}"
            for i, s in enumerate(chunk_summaries)
        ]
        combined = "\n\n".join(condensed)
        return f"""You are merging {len(chunk_summaries)} chunk summaries into one cohesive academic summary.
Return strict JSON only with these exact keys:
summary_title, authors, overview, body, takeaways, topics, chunks_used

Rules:
- Remove repetition ruthlessly — if the same point appears in multiple chunks, keep it once.
- body: 2-4 paragraphs telling the document's story from start to finish.
- takeaways: 3-5 most important specific claims across all chunks.
- topics: 3-6 study topics that span the whole document.
- chunks_used: {len(chunk_summaries)}

Document title: {title}
Chunk summaries:
{combined}
"""

    def _quiz_prompt(
        self,
        *,
        title: str,
        summary: SummaryResponse,
        question_count: int,
        difficulty: str,
        exclude_questions: list[str],
        follow_up: bool,
        weak_topics: list[str] | None = None,
        module: LearningModuleResponse | None = None,
    ) -> str:
        difficulty_key  = difficulty.lower().strip()
        difficulty_desc = _DIFFICULTY_DESCRIPTORS.get(difficulty_key, _DIFFICULTY_DESCRIPTORS[_DEFAULT_DIFFICULTY])
        exclude_json    = json.dumps(exclude_questions[:20], ensure_ascii=True)
        weak_topics_str = ", ".join(weak_topics or []) or "none specified"

        module_context = ""
        if module and follow_up:
            module_context = f"""
Learning module focus areas: {', '.join(module.focus_areas)}
Study plan: {'; '.join(module.study_plan[:3])}
"""

        return f"""You are writing a multiple-choice quiz for a study platform.
Return strict JSON only with these exact keys:
title, question_count, questions{', target_topics' if follow_up else ''}

Each question object must have exactly these keys:
question, options, correct_index, explanation, topic

Question rules:
- Generate exactly {question_count} questions.
- DIFFICULTY: {difficulty_desc}
- Each question must have exactly 4 options (A, B, C, D).
- correct_index is 0-3 (0=A, 1=B, 2=C, 3=D).
- explanation must say WHY the correct answer is right AND why the most tempting wrong answer is wrong.
  Minimum 25 words. Be specific to this document.
- topic must be a specific noun phrase (2-6 words) from the document's subject matter.
  Bad: "general", "document", "content". Good: "experimental methodology", "carbon cycle feedback".
- Questions must cover a spread of topics — no more than 2 questions on the same topic.
- Never copy a sentence from the summary verbatim as a question stem.
- Distractors (wrong answers) must be plausible — not obviously absurd.

{'FOLLOW-UP INSTRUCTIONS: These topics were weak in the initial quiz — weight them heavily: ' + weak_topics_str if follow_up else ''}
{module_context}

Document: {title}
Summary overview: {summary.overview}
Key topics: {', '.join(summary.topics)}
Key takeaways: {'; '.join(summary.takeaways[:3])}

Excluded questions (do not repeat or lightly reword these):
{exclude_json}
"""

    def _learning_module_prompt(self, payload: LearningModuleRequest) -> str:
        missed_json = json.dumps(
            [{"question": m.question, "topic": m.topic,
              "user_answer": m.user_answer, "correct_answer": m.correct_answer,
              "explanation": m.explanation}
             for m in payload.missed_questions],
            ensure_ascii=True,
        )
        weak_topics_str = ", ".join(payload.weak_topics)

        return f"""You are building a targeted revision module after a student struggled with a quiz.
Return strict JSON only with these exact keys:
title, description, focus_areas, sections, study_plan

Field rules:
- title: "Targeted revision: [most important weak topic]" (max 100 chars)
- description: 2-3 sentences explaining what this module covers and why. Reference the document title.
- focus_areas: 2-4 specific topic labels the student needs to revisit.
- sections: 2-4 objects. Each must have:
    topic: the specific weak topic (2-6 words)
    explanation: 3-5 sentences explaining the concept using content from the document.
      Reference specific findings, methods, or arguments from the summary.
      Do NOT write generic textbook definitions.
    why_it_matters: 1-2 sentences connecting this topic to the document's main argument.
    practice_tip: 1 concrete action (e.g. "Redraw Figure 2 from memory and label the feedback loops").
- study_plan: 3-5 specific next actions. Each must be actionable and tied to the document content.
  Good: "Re-read the methodology section focusing on how X was operationalised."
  Bad: "Review the topic."

Document: {payload.title}
Document summary: {payload.summary.overview}
Key topics from document: {', '.join(payload.summary.topics)}
Student's weak topics: {weak_topics_str}

Missed questions (what the student got wrong):
{missed_json}
"""

    # ── Normalisation helpers (unchanged from v1 — these are solid) ───────────

    def _normalize_model_payload(self, model_type: type[ModelT], data: dict) -> dict:
        normalized = dict(data)

        list_fields = [
            "body", "takeaways", "topics", "focus_areas", "study_plan",
            "study_recommendations", "strengths", "weaknesses", "weak_topics",
            "target_topics", "improved_topics", "remaining_weak_topics", "next_steps",
        ]
        max_sizes = {
            "body": 4, "takeaways": 5, "topics": 6, "focus_areas": 4,
            "study_plan": 5, "study_recommendations": 4, "strengths": 4,
            "weaknesses": 4, "weak_topics": 4, "target_topics": 4,
            "improved_topics": 4, "remaining_weak_topics": 4, "next_steps": 4,
        }
        for field in list_fields:
            if field in normalized:
                normalized[field] = self._ensure_string_list(
                    normalized[field], max_items=max_sizes.get(field, 4)
                )

        if "authors" in normalized:
            normalized["authors"] = self._normalize_authors(normalized["authors"])

        if "questions" in normalized and isinstance(normalized["questions"], list):
            normalized["questions"] = [self._normalize_question(item) for item in normalized["questions"]]

        if "reviewed_questions" in normalized and isinstance(normalized["reviewed_questions"], list):
            normalized["reviewed_questions"] = [
                self._normalize_reviewed_question(item) for item in normalized["reviewed_questions"]
            ]

        if "sections" in normalized and isinstance(normalized["sections"], list):
            normalized["sections"] = [self._normalize_section(item) for item in normalized["sections"]]

        if model_type.__name__ == "SummaryResponse":
            normalized["chunks_used"] = int(normalized.get("chunks_used") or 1)
        if model_type.__name__ == "LearningModuleResponse":
            normalized = self._normalize_learning_module(normalized)

        return normalized

    def _normalize_authors(self, value: object) -> str:
        if isinstance(value, list):
            cleaned = [self._clean_list_item(item) for item in value]
            return ", ".join(item for item in cleaned if item)
        if value is None:
            return ""
        return re.sub(r"\s+", " ", str(value)).strip()

    def _normalize_question(self, item: dict) -> dict:
        normalized = dict(item)
        normalized["options"] = self._ensure_string_list(normalized.get("options", []), max_items=4)
        if len(normalized["options"]) > 4:
            normalized["options"] = normalized["options"][:4]
        if "correct_index" in normalized:
            try:
                normalized["correct_index"] = int(normalized["correct_index"])
            except (TypeError, ValueError):
                normalized["correct_index"] = 0
        return normalized

    def _normalize_reviewed_question(self, item: dict) -> dict:
        normalized = dict(item)
        if "is_correct" in normalized:
            normalized["is_correct"] = bool(normalized["is_correct"])
        return normalized

    def _normalize_section(self, item: dict) -> dict:
        normalized = dict(item)
        topic = str(normalized.get("topic") or "Core concept").strip()
        normalized["topic"] = topic[:80]
        normalized["explanation"] = self._pad_min_text(
            normalized.get("explanation"),
            f"Review how {topic} is described in the document and connect it to the main argument.",
            50,
        )
        normalized["why_it_matters"] = self._pad_min_text(
            normalized.get("why_it_matters"),
            f"{topic} matters because it shapes how the document's evidence should be interpreted.",
            25,
        )
        normalized["practice_tip"] = self._pad_min_text(
            normalized.get("practice_tip"),
            f"Summarise {topic} in your own words and write one example from the document.",
            20,
        )
        return normalized

    def _normalize_learning_module(self, normalized: dict) -> dict:
        focus = normalized.get("focus_areas") or []
        while len(focus) < 2:
            focus.append("Core argument" if not focus else "Evidence and examples")
        normalized["focus_areas"] = focus[:4]

        sections = normalized.get("sections") or []
        while len(sections) < 2:
            topic = normalized["focus_areas"][len(sections) % len(normalized["focus_areas"])]
            sections.append(self._normalize_section({"topic": topic}))
        normalized["sections"] = sections[:4]

        study_plan = normalized.get("study_plan") or []
        while len(study_plan) < 3:
            study_plan.append("Review one missed question, explain the correct answer, and connect it to the summary.")
        normalized["study_plan"] = study_plan[:5]
        normalized["description"] = self._pad_min_text(
            normalized.get("description"),
            "This targeted module turns your quiz feedback into focused revision tasks before the follow-up quiz.",
            60,
        )
        return normalized

    def _pad_min_text(self, value: object, fallback: str, min_length: int) -> str:
        text = re.sub(r"\s+", " ", str(value or "").strip())
        if not text:
            text = fallback
        while len(text) < min_length:
            text = f"{text} {fallback}"
        return text

    def _ensure_string_list(self, value: object, *, max_items: int) -> list[str]:
        if isinstance(value, list):
            cleaned = [self._clean_list_item(item) for item in value]
            return [item for item in cleaned if item][:max_items]
        if isinstance(value, str):
            parts = re.split(r"\n+|(?:^|\s)[-•]\s+|\s*\d+\.\s+", value)
            cleaned = [self._clean_list_item(item) for item in parts]
            cleaned = [item for item in cleaned if item]
            if cleaned:
                return cleaned[:max_items]
            fallback = self._split_paragraphs(value, max_items=max_items)
            return fallback if fallback else [value.strip()]
        if value is None:
            return []
        return [str(value).strip()][:max_items]

    def _clean_list_item(self, item: object) -> str:
        return re.sub(r"\s+", " ", str(item)).strip(" -•\n\t")

    def _split_paragraphs(self, value: str, *, max_items: int) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", value.strip())
        if len(sentences) <= 1:
            return []
        chunks: list[str] = []
        current = ""
        for sentence in sentences:
            candidate = f"{current} {sentence}".strip()
            if len(candidate) > 220 and current:
                chunks.append(current.strip())
                current = sentence
            else:
                current = candidate
        if current:
            chunks.append(current.strip())
        return chunks[:max_items]

    # ── Text helpers ──────────────────────────────────────────────────────────

    def _clean_text(self, text: str) -> str:
        """Normalise whitespace and truncate to the configured max character limit.

        Reads AI_SUMMARY_MAX_CHARS from env (default 12000). Truncation
        happens at the last space before the limit to avoid word-splitting.

        Args:
            text: Raw input text from the user.

        Returns:
            Cleaned and truncated text string.
        """
        cleaned = re.sub(r"\s+", " ", text).strip()
        max_chars = int(os.getenv("AI_SUMMARY_MAX_CHARS", "12000"))
        if max_chars > 0 and len(cleaned) > max_chars:
            return cleaned[:max_chars].rsplit(" ", 1)[0]
        return cleaned

    def _chunk_text(self, text: str, chunk_size: int = 4000) -> list[str]:
        """Split long text into sentence-aware chunks for batch processing.

        Reads AI_SUMMARY_CHUNK_SIZE from env (default 4000). Splits on
        sentence boundaries to keep paragraphs intact where possible.

        Args:
            text:       The cleaned document text.
            chunk_size: Target size per chunk in characters.

        Returns:
            List of text chunks, each ≤ chunk_size characters.
        """
        chunk_size = int(os.getenv("AI_SUMMARY_CHUNK_SIZE", str(chunk_size)))
        if len(text) <= chunk_size:
            return [text]
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks: list[str] = []
        current = ""
        for sentence in sentences:
            if len(current) + len(sentence) + 1 > chunk_size and current:
                chunks.append(current.strip())
                current = sentence
            else:
                current = f"{current} {sentence}".strip()
        if current:
            chunks.append(current)
        return chunks

    # ── Analysis helpers ──────────────────────────────────────────────────────

    def _build_reviewed_questions(self, payload: AnalyzeResultsRequest) -> list[ReviewedQuestion]:
        """Pair each quiz question with the user's answer and mark correctness.

        Matches answers to questions by index. Unanswered questions are marked
        as "Skipped" with chosen_index = -1.

        Args:
            payload: AnalyzeResultsRequest containing questions and user answers.

        Returns:
            List of ReviewedQuestion objects.
        """
        reviewed: list[ReviewedQuestion] = []
        answers_by_index = {item.question_index: item for item in payload.answers}
        for index, question in enumerate(payload.questions):
            answer = answers_by_index.get(index)
            chosen_index = answer.chosen_index if answer else -1
            user_answer    = "Skipped" if chosen_index < 0 else question.options[chosen_index]
            correct_answer = question.options[question.correct_index]
            reviewed.append(ReviewedQuestion(
                question=question.question,
                topic=question.topic,
                user_answer=user_answer,
                correct_answer=correct_answer,
                is_correct=chosen_index == question.correct_index,
                explanation=question.explanation,
            ))
        return reviewed

    def _derive_strengths(
        self, reviewed_questions: list[ReviewedQuestion], fallback_topics: list[str]
    ) -> list[str]:
        """Identify the student's strongest topics by counting correct answers.

        Falls back to the first 2 summary topics if no questions were correct.

        Args:
            reviewed_questions: List of ReviewedQuestion with is_correct flags.
            fallback_topics:    Topics from the document summary to use as fallback.

        Returns:
            Up to 4 topic names the student performed well on.
        """
        correct_topics = [item.topic for item in reviewed_questions if item.is_correct]
        ranked = [topic for topic, _ in Counter(correct_topics).most_common(4)]
        return ranked or fallback_topics[:2]

    def _derive_weak_topics(
        self, reviewed_questions: list[ReviewedQuestion], fallback_topics: list[str]
    ) -> list[str]:
        """Identify the student's weakest topics by counting incorrect answers.

        If fewer than 2 wrong topics are found, supplements with a mix of
        fallback topics and the student's correct topics to ensure at least
        4 candidates are returned.

        Args:
            reviewed_questions: List of ReviewedQuestion with is_correct flags.
            fallback_topics:    Topics from the document summary.

        Returns:
            Up to 4 topic names the student needs to improve on.
        """
        wrong_topics = [item.topic for item in reviewed_questions if not item.is_correct]
        if not wrong_topics:
            return []
        ranked_wrong = [topic for topic, _ in Counter(wrong_topics).most_common(4)]
        if len(ranked_wrong) >= 2:
            return ranked_wrong[:4]
        correct_topics = [item.topic for item in reviewed_questions if item.is_correct]
        ranked_correct = [topic for topic, _ in Counter(correct_topics).most_common(4)]
        candidates: list[str] = []
        for topic in ranked_wrong + fallback_topics + ranked_correct:
            if topic and topic not in candidates:
                candidates.append(topic)
            if len(candidates) == 4:
                break
        return candidates[:4] or ["Core concepts", "Key findings"]

    def _derive_recommendations(self, weak_topics: list[str], summary_topics: list[str]) -> list[str]:
        """Generate generic study recommendations when AI analysis is unavailable.

        Args:
            weak_topics:    List of weak topic names.
            summary_topics: Topics from the document summary.

        Returns:
            Up to 4 recommendation strings.
        """
        if not weak_topics:
            return [
                "No urgent revision needed. Review the summary once to keep recall fresh.",
                "Try the follow-up quiz for reinforcement or move to a new document.",
            ]
        base_topics = weak_topics or summary_topics[:2]
        return [f"Review {topic} using the learning module." for topic in base_topics[:4]]

    def _build_improvement_summary(
        self, score_delta: int, improved: list[str], remaining: list[str]
    ) -> str:
        """Build a human-readable improvement summary for progress comparison.

        Handles four scenarios: improved with specific topics, improved without specifics,
        no improvement with remaining weak areas, and stable performance.

        Args:
            score_delta: Change in score percentage (may be negative).
            improved:    Topics the student improved on.
            remaining:   Topics still needing work.

        Returns:
            A 1-2 sentence summary string.
        """
        if score_delta > 0 and improved:
            return (
                f"Your follow-up quiz improved by {score_delta} points. "
                f"Understanding was stronger in {', '.join(improved[:3])}."
            )
        if score_delta > 0:
            return f"Your follow-up quiz improved by {score_delta} points with more consistent topic recall."
        if remaining:
            return (
                "The follow-up quiz shows weak areas still need attention, especially "
                + ", ".join(remaining[:3]) + "."
            )
        return "The follow-up quiz kept performance stable, but more targeted revision is still recommended."

    def _build_next_steps(self, improved: list[str], remaining: list[str]) -> list[str]:
        """Generate next-step recommendations based on progress comparison.

        Args:
            improved:  Topics the student improved on.
            remaining: Topics still needing work.

        Returns:
            Up to 4 actionable next-step strings.
        """
        steps: list[str] = []
        if improved:
            steps.append(f"Keep reinforcing {improved[0]} with another short recall session.")
        for topic in remaining[:2]:
            steps.append(f"Revisit {topic} and answer another set of targeted questions.")
        if len(steps) < 2:
            steps.append("Review the learning module summary before your next quiz.")
        return steps[:4]

    # ── Resource search ───────────────────────────────────────────────────────

    def _search_resource(
        self,
        *,
        query: str,
        resource_type: str,
        topic: str,
        preferred_domains: list[str],
    ) -> ResourceRecommendation | None:
        """Search DuckDuckGo HTML results for a matching resource.

        Parses the DuckDuckGo HTML result page looking for result links with
        titles and snippets. Filters by preferred_domains if specified.

        Args:
            query:            Full search query string.
            resource_type:    One of "article", "video", "podcast".
            topic:            The topic label for the recommendation.
            preferred_domains: List of domain tokens to filter by (e.g. ["khanacademy.org"]).

        Returns:
            ResourceRecommendation if a match is found, None otherwise.
        """
        try:
            html = self._fetch_search_results(query)
        except (URLError, OSError):
            return None

        # Try to match results with both title and snippet
        matches = re.findall(
            r'<a[^>]+class="result__a"[^>]+href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>.*?'
            r'<a[^>]+class="result__snippet"[^>]*>(?P<snippet>.*?)</a>',
            html, flags=re.S,
        )
        # Fallback: match title only if snippet pattern doesn't match
        if not matches:
            matches = re.findall(
                r'<a[^>]+class="result__a"[^>]+href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>',
                html, flags=re.S,
            )
            matches = [(href, title, "") for href, title in matches]

        for href, title, snippet in matches:
            url = self._extract_result_url(href)
            if not url or not url.startswith(("http://", "https://")):
                continue
            domain = urlparse(url).netloc.lower()
            if preferred_domains and not any(token in domain for token in preferred_domains):
                continue
            clean_title   = self._strip_html(title)
            clean_snippet = self._strip_html(snippet) or f"Recommended {resource_type} covering {topic}."
            source = domain.replace("www.", "") or resource_type.title()
            return ResourceRecommendation(
                topic=topic,
                title=clean_title[:240],
                url=url,
                source=source[:120],
                snippet=clean_snippet[:400],
                resource_type=resource_type,
            )
        return None

    def _search_resource_variants(
        self,
        *,
        topic: str,
        resource_type: str,
        queries: list[str],
        preferred_domains: list[str],
    ) -> ResourceRecommendation | None:
        """Try multiple search queries for a resource type and return the first match.

        Args:
            topic:             Topic label for the recommendation.
            resource_type:     One of "article", "video", "podcast".
            queries:           Ordered list of search query strings to try.
            preferred_domains: Domain filter passed to _search_resource.

        Returns:
            First ResourceRecommendation found, or None.
        """
        for query in queries:
            match = self._search_resource(
                query=query,
                resource_type=resource_type,
                topic=topic,
                preferred_domains=preferred_domains,
            )
            if match:
                return match
        return None

    def _search_article_resource(self, title: str, topic: str) -> ResourceRecommendation | None:
        """Search for an educational article about the topic.

        Skips Wikipedia in favour of more reliable educational sources
        (Khan Academy, Britannica, ScienceDaily, .edu domains, OpenStax).

        Args:
            title: Document title (used for context in search).
            topic: Topic to search for.

        Returns:
            ResourceRecommendation or None.
        """
        # No Wikipedia — search real educational sources directly
        return self._search_resource_variants(
            topic=topic,
            resource_type="article",
            queries=[
                f"{topic} site:khanacademy.org",
                f"{topic} site:britannica.com",
                f"{topic} site:sciencedaily.com",
                f"{title} {topic} explained site:.edu",
                f"{topic} overview site:openstax.org",
            ],
            preferred_domains=["khanacademy.org", "britannica.com", "sciencedaily.com", ".edu", "openstax.org"],
        )

    def _search_video_resource(self, title: str, topic: str) -> ResourceRecommendation | None:
        """Search for an educational video about the topic.

        Tries YouTube first via _search_youtube_video, then falls back
        to DuckDuckGo search for YouTube/ted.com/khanacademy.org results.

        Args:
            title: Document title.
            topic: Topic to search for.

        Returns:
            ResourceRecommendation or None.
        """
        youtube = self._search_youtube_video(f"{title} {topic} explainer", topic)
        if youtube:
            return youtube
        return self._search_resource_variants(
            topic=topic,
            resource_type="video",
            queries=[
                f"{title} {topic} site:youtube.com/watch",
                f"{topic} explainer site:youtube.com/watch",
            ],
            preferred_domains=["youtube.com", "youtu.be", "ted.com", "khanacademy.org"],
        )

    def _search_podcast_resource(self, title: str, topic: str) -> ResourceRecommendation | None:
        """Search for an educational podcast episode about the topic.

        Tries ListenNotes first (scraped), then Apple Podcasts / Spotify
        via DuckDuckGo, and finally falls back to an Apple Podcasts search URL.

        Args:
            title: Document title.
            topic: Topic to search for.

        Returns:
            ResourceRecommendation or None.
        """
        ln_result = self._search_listennotes(topic, title)
        if ln_result:
            return ln_result
        ddg_result = self._search_resource_variants(
            topic=topic,
            resource_type="podcast",
            queries=[
                f"{topic} {title} podcast episode site:podcasts.apple.com",
                f"{topic} educational podcast episode site:open.spotify.com/episode",
            ],
            preferred_domains=["podcasts.apple.com", "open.spotify.com", "anchor.fm", "buzzsprout.com"],
        )
        if ddg_result:
            return ddg_result
        from urllib.parse import quote_plus
        search_url = f"https://podcasts.apple.com/search?term={quote_plus(topic + ' ' + title)}"
        return ResourceRecommendation(
            topic=topic,
            title=f"{topic}: educational podcast episodes",
            url=search_url,
            source="podcasts.apple.com",
            snippet=f"Search Apple Podcasts for episodes covering {topic}.",
            resource_type="podcast",
        )

    def _search_listennotes(self, topic: str, doc_title: str) -> ResourceRecommendation | None:
        """Search ListenNotes for podcast episodes matching the topic.

        Scrapes the ListenNotes search HTML and ranks results by how many
        topic tokens appear in the episode title. Returns the best match.

        Args:
            topic:     Topic to search for.
            doc_title: Document title for additional search context.

        Returns:
            ResourceRecommendation or None.
        """
        try:
            req = Request(
                f"https://www.listennotes.com/search/?q={quote_plus(topic + ' ' + doc_title)}&type=episode",
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                    ),
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            with urlopen(req, timeout=12) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            # Extract episode links with titles from the search results
            episodes = re.findall(
                r'href="(/e/[A-Za-z0-9]+/)"[^>]*>[\s\S]{0,60}?<[^>]+class="[^"]*title[^"]*"[^>]*>([^<]{8,200})',
                html,
            )
            if not episodes:
                return None

            # Score each episode by topic token overlap in the title
            topic_tokens = self._topic_tokens(topic)
            best_score, best_ep = -1, None
            for path, ep_title in episodes[:8]:
                score = sum(1 for t in topic_tokens if t in ep_title.lower())
                if score > best_score:
                    best_score, best_ep = score, (path, ep_title.strip())

            if not best_ep or best_score < 1:
                return None

            path, ep_title = best_ep
            return ResourceRecommendation(
                topic=topic,
                title=ep_title[:240],
                url=f"https://www.listennotes.com{path}",
                source="listennotes.com",
                snippet=f"Podcast episode covering {topic}.",
                resource_type="podcast",
            )
        except Exception:
            return None

    def _fetch_search_results(self, query: str) -> str:
        """Fetch DuckDuckGo HTML search results for a query.

        Uses the DuckDuckGo lite HTML endpoint (html.duckduckgo.com/html)
        which returns plain HTML without JavaScript.

        Args:
            query: URL-encoded search query.

        Returns:
            Raw HTML string of the search results page.

        Raises:
            URLError: If the request fails or times out.
        """
        req = Request(
            f"https://html.duckduckgo.com/html/?q={quote_plus(query)}",
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                )
            },
        )
        with urlopen(req, timeout=18) as response:
            return response.read().decode("utf-8", errors="ignore")

    def _search_wikipedia_article(self, topic: str) -> ResourceRecommendation | None:
        """Search Wikipedia via the OpenSearch API for articles matching the topic.

        This is currently unused in the main resource pipeline (Wikipedia is
        explicitly avoided in _search_article_resource) but kept for potential
        future use as a last-resort fallback.

        Args:
            topic: Topic to search for.

        Returns:
            ResourceRecommendation or None.
        """
        try:
            req = Request(
                "https://en.wikipedia.org/w/api.php"
                f"?action=opensearch&search={quote_plus(topic)}&limit=1&namespace=0&format=json",
                headers={"User-Agent": "LearnovaAI/2.0"},
            )
            with urlopen(req, timeout=12) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, list) or len(payload) < 4 or not payload[1]:
                return None
            title_str   = str(payload[1][0])
            description = str(payload[2][0]) if payload[2] else f"Reference article for {topic}."
            url         = str(payload[3][0]) if payload[3] else ""
            if not url:
                return None
            return ResourceRecommendation(
                topic=topic,
                title=f"{topic} — {title_str}",
                url=url,
                source="wikipedia.org",
                snippet=description[:400],
                resource_type="article",
            )
        except Exception:
            return None

    def _search_youtube_video(self, query: str, topic: str) -> ResourceRecommendation | None:
        """Search YouTube for a video matching the topic.

        Scrapes YouTube search result HTML for video IDs and titles,
        then scores the titles by topic token overlap.

        Args:
            query: Full search query string.
            topic: Topic label for scoring relevance.

        Returns:
            ResourceRecommendation or None.
        """
        try:
            req = Request(
                f"https://www.youtube.com/results?search_query={quote_plus(query)}",
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                    )
                },
            )
            with urlopen(req, timeout=18) as response:
                html = response.read().decode("utf-8", errors="ignore")
        except (URLError, OSError):
            return None

        # Extract video IDs and titles from YouTube's initial data payload
        candidates = re.findall(
            r'"videoId":"(?P<video_id>[A-Za-z0-9_-]{11})".{0,400}?"title":\{"runs":\[\{"text":"(?P<title>[^"]+)"',
            html, flags=re.S,
        )
        if not candidates:
            return None

        best: tuple[int, str, str] | None = None
        for video_id, title_text in candidates[:12]:
            score = self._score_video_title_match(topic, title_text)
            if best is None or score > best[0]:
                best = (score, video_id, title_text)

        if best is None or best[0] < 2:
            return None

        _, video_id, title_text = best
        return ResourceRecommendation(
            topic=topic,
            title=title_text,
            url=f"https://www.youtube.com/watch?v={video_id}",
            source="youtube.com",
            snippet=f"Video matched to topic: {topic}.",
            resource_type="video",
        )

    def _score_video_title_match(self, topic: str, title_text: str) -> int:
        """Score how well a YouTube video title matches the topic.

        Awards 2 points per topic token found in the title, +1 bonus for
        educational keywords (explainer, tutorial, etc.), -2 penalty for
        non-educational content (music, trailer, vlog, etc.).

        Args:
            topic:      The topic to match against.
            title_text: The YouTube video title.

        Returns:
            Integer relevance score.
        """
        topic_tokens  = self._topic_tokens(topic)
        if not topic_tokens:
            return 0
        lowered = title_text.lower()
        score   = sum(2 for token in topic_tokens if token in lowered)
        if any(w in lowered for w in ("explainer", "introduction", "overview", "tutorial", "explained")):
            score += 1
        if any(w in lowered for w in ("music", "trailer", "reaction", "vlog", "podcast")):
            score -= 2
        return score

    def _topic_tokens(self, topic: str) -> list[str]:
        """Split a topic string into meaningful tokens for search matching.

        Removes common stop words and single-character tokens.

        Args:
            topic: A topic string like "experimental methodology".

        Returns:
            List of lowercase tokens with length > 2, excluding stop words.
        """
        stop_words = {"the", "and", "for", "with", "from", "into", "your", "this", "that"}
        tokens = re.findall(r"[a-zA-Z0-9]+", topic.lower())
        return [token for token in tokens if len(token) > 2 and token not in stop_words]

    def _extract_result_url(self, href: str) -> str:
        """Extract the actual URL from a DuckDuckGo redirect link.

        DuckDuckGo wraps external URLs in /l/?uddg=<encoded_url>. This
        function extracts and decodes the uddg parameter.

        Args:
            href: The href attribute from a DuckDuckGo result link.

        Returns:
            The decoded destination URL, or the original if not a DDG redirect.
        """
        if "duckduckgo.com/l/?" not in href:
            return unescape(href)
        match = re.search(r"[?&]uddg=([^&]+)", href)
        if not match:
            return ""
        return unescape(unquote(match.group(1)))

    def _strip_html(self, value: str) -> str:
        """Remove HTML tags and decode HTML entities from a string.

        Args:
            value: Raw HTML string.

        Returns:
            Clean text with tags removed and entities decoded.
        """
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", unescape(value))).strip()

    def _build_article_fallback(self, topic: str) -> ResourceRecommendation:
        """Build a fallback Wikipedia search URL when no article is found.

        This is used as a last resort if all article searches fail.

        Args:
            topic: Topic to link to.

        Returns:
            ResourceRecommendation pointing to a Wikipedia search page.
        """
        search_url = f"https://en.wikipedia.org/w/index.php?search={quote_plus(topic.strip())}"
        return ResourceRecommendation(
            topic=topic,
            title=f"{topic} — overview",
            url=search_url,
            source="wikipedia.org",
            snippet=f"Reference page for {topic}.",
            resource_type="article",
        )

    # ── Validation helpers ────────────────────────────────────────────────────

    def _assert_unique_questions(self, questions: list) -> None:
        """Raise ValueError if any two questions are duplicates (case/punctuation normalised)."""
        def normalise(q: str) -> str:
            return re.sub(r"[^a-z0-9 ]", "", q.strip().lower())

        normalised = [normalise(item.question) for item in questions]
        if len(normalised) != len(set(normalised)):
            raise ValueError("AI output validation failed: quiz contains duplicate questions.")

    def _assert_no_repeated_questions(self, questions: list, previous_questions: list[str]) -> None:
        """Raise ValueError if any question repeats one from an earlier quiz."""
        def normalise(q: str) -> str:
            return re.sub(r"[^a-z0-9 ]", "", q.strip().lower())

        previous = {normalise(item) for item in previous_questions}
        if any(normalise(question.question) in previous for question in questions):
            raise ValueError("AI output validation failed: follow-up quiz repeated a previous question.")