from __future__ import annotations

import json
import re
from collections import Counter
from html import unescape
from typing import TypeVar
from urllib.parse import quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

from pydantic import BaseModel, ValidationError

from .ollama_client import OllamaClient, OllamaError
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

ModelT = TypeVar("ModelT", bound=BaseModel)


class AIService:
    def __init__(self, client: OllamaClient | None = None) -> None:
        self.client = client or OllamaClient()

    def summarize(self, payload: SummaryRequest) -> SummaryResponse:
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
                self._chunk_summary_prompt(payload.title, index + 1, chunk),
                SummaryResponse,
            )
            for index, chunk in enumerate(chunks)
        ]
        merged = self._generate_structured(
            self._merge_summary_prompt(payload.title, chunk_summaries),
            SummaryResponse,
        )
        return merged.model_copy(update={"chunks_used": len(chunks)})

    def generate_quiz(self, payload: QuizRequest) -> QuizResponse:
        question_count = max(6, min(8, payload.question_count))
        prompt = self._quiz_prompt(
            title=payload.title,
            summary=payload.summary,
            question_count=question_count,
            difficulty=payload.difficulty,
            exclude_questions=payload.exclude_questions,
            follow_up=False,
        )
        response = self._generate_structured(prompt, QuizResponse)
        self._assert_unique_questions(response.questions)
        return response.model_copy(update={"question_count": question_count})

    def analyze_results(self, payload: AnalyzeResultsRequest) -> AnalyzeResultsResponse:
        review = self._build_reviewed_questions(payload)
        correct_count = sum(1 for item in review if item.is_correct)
        total_questions = len(review)
        score_percent = round((correct_count / total_questions) * 100)
        weak_topics = self._derive_weak_topics(review, payload.summary.topics)
        strengths = self._derive_strengths(review, payload.summary.topics)
        weaknesses = weak_topics[:4]
        recommendations = self._derive_recommendations(weak_topics, payload.summary.topics)
        return AnalyzeResultsResponse(
            score_percent=score_percent,
            correct_count=correct_count,
            total_questions=total_questions,
            strengths=strengths,
            weaknesses=weaknesses,
            weak_topics=weak_topics,
            study_recommendations=recommendations,
            reviewed_questions=review,
        )

    def generate_learning_module(self, payload: LearningModuleRequest) -> LearningModuleResponse:
        prompt = self._learning_module_prompt(payload)
        return self._generate_structured(prompt, LearningModuleResponse)

    def generate_follow_up_quiz(self, payload: FollowUpQuizRequest) -> FollowUpQuizResponse:
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
        response = self._generate_structured(prompt, FollowUpQuizResponse)
        self._assert_unique_questions(response.questions)
        self._assert_no_repeated_questions(response.questions, payload.previous_questions)
        return response.model_copy(
            update={"question_count": question_count, "target_topics": payload.weak_topics[:4]}
        )

    def recommend_resources(
        self, payload: ResourceRecommendationRequest
    ) -> ResourceRecommendationResponse:
        target_topics = payload.weak_topics[:3] or payload.learning_module.focus_areas[:3] or payload.summary.topics[:3]
        resources: list[ResourceRecommendation] = []
        for topic in target_topics:
            article = self._search_article_resource(payload.title, topic)
            if article:
                resources.append(article)

            video = self._search_video_resource(payload.title, topic)
            if video:
                resources.append(video)

            if not article:
                resources.append(self._build_article_fallback(topic))

        if len(resources) < 2:
            for topic in target_topics:
                resources.append(self._build_article_fallback(topic))
                if len(resources) >= 2:
                    break

        deduped: list[ResourceRecommendation] = []
        seen_urls: set[str] = set()
        for resource in resources:
            if resource.url in seen_urls:
                continue
            deduped.append(resource)
            seen_urls.add(resource.url)
            if len(deduped) == 6:
                break

        if len(deduped) < 2:
            raise ValueError("Could not find enough resource recommendations for this module.")
        return ResourceRecommendationResponse(resources=deduped)

    def compare_progress(self, payload: CompareProgressRequest) -> CompareProgressResponse:
        initial_weak = set(payload.initial_result.weak_topics)
        follow_weak = set(payload.follow_up_result.weak_topics)
        improved = sorted(initial_weak - follow_weak)
        remaining = sorted(follow_weak)
        score_delta = payload.follow_up_result.score_percent - payload.initial_result.score_percent
        improvement_summary = self._build_improvement_summary(score_delta, improved, remaining)
        next_steps = self._build_next_steps(improved, remaining)
        return CompareProgressResponse(
            score_delta=score_delta,
            improved_topics=improved[:4],
            remaining_weak_topics=remaining[:4],
            improvement_summary=improvement_summary,
            next_steps=next_steps,
        )

    def _generate_structured(self, prompt: str, model_type: type[ModelT], retries: int = 2) -> ModelT:
        errors: list[str] = []
        for _ in range(retries + 1):
            try:
                data = self.client.generate_json(prompt)
                data = self._normalize_model_payload(model_type, data)
                return model_type.model_validate(data)
            except (OllamaError, ValidationError) as exc:
                errors.append(str(exc))
        raise ValueError("AI output validation failed: " + " | ".join(errors))

    def _normalize_model_payload(self, model_type: type[ModelT], data: dict) -> dict:
        normalized = dict(data)

        if "body" in normalized:
            normalized["body"] = self._ensure_string_list(normalized["body"], max_items=4)
        if "authors" in normalized:
            normalized["authors"] = self._normalize_authors(normalized["authors"])
        if "takeaways" in normalized:
            normalized["takeaways"] = self._ensure_string_list(normalized["takeaways"], max_items=5)
        if "topics" in normalized:
            normalized["topics"] = self._ensure_string_list(normalized["topics"], max_items=6)
        if "focus_areas" in normalized:
            normalized["focus_areas"] = self._ensure_string_list(normalized["focus_areas"], max_items=4)
        if "study_plan" in normalized:
            normalized["study_plan"] = self._ensure_string_list(normalized["study_plan"], max_items=5)
        if "study_recommendations" in normalized:
            normalized["study_recommendations"] = self._ensure_string_list(
                normalized["study_recommendations"], max_items=4
            )
        if "strengths" in normalized:
            normalized["strengths"] = self._ensure_string_list(normalized["strengths"], max_items=4)
        if "weaknesses" in normalized:
            normalized["weaknesses"] = self._ensure_string_list(normalized["weaknesses"], max_items=4)
        if "weak_topics" in normalized:
            normalized["weak_topics"] = self._ensure_string_list(normalized["weak_topics"], max_items=4)
        if "target_topics" in normalized:
            normalized["target_topics"] = self._ensure_string_list(normalized["target_topics"], max_items=4)
        if "improved_topics" in normalized:
            normalized["improved_topics"] = self._ensure_string_list(normalized["improved_topics"], max_items=4)
        if "remaining_weak_topics" in normalized:
            normalized["remaining_weak_topics"] = self._ensure_string_list(
                normalized["remaining_weak_topics"], max_items=4
            )
        if "next_steps" in normalized:
            normalized["next_steps"] = self._ensure_string_list(normalized["next_steps"], max_items=4)

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

        return normalized

    def _normalize_authors(self, value: object) -> str:
        if isinstance(value, list):
            cleaned = [self._clean_list_item(item) for item in value]
            cleaned = [item for item in cleaned if item]
            return ", ".join(cleaned)
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
        return dict(item)

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

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def _chunk_text(self, text: str, chunk_size: int = 6000) -> list[str]:
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

    def _summary_prompt(self, title: str, text: str) -> str:
        return f"""
You are generating a learner-friendly academic summary.
Return strict JSON only with these keys:
summary_title, authors, overview, body, takeaways, topics, chunks_used

Rules:
- Explain the academic meaning, not generic fluff.
- body must contain 2 to 4 short paragraphs.
- takeaways must contain 3 to 5 concise bullets as strings.
- topics must contain 3 to 6 study topics.
- chunks_used must be 1.

Document title: {title}
Document text:
\"\"\"{text}\"\"\"
"""

    def _chunk_summary_prompt(self, title: str, index: int, text: str) -> str:
        return f"""
You are summarizing one chunk of a larger academic document.
Return strict JSON only with these keys:
summary_title, authors, overview, body, takeaways, topics, chunks_used

Rules:
- Focus only on the chunk content.
- body must contain exactly 2 short paragraphs.
- takeaways must contain exactly 3 strings.
- topics must contain 3 to 5 strings.
- authors can be "Unknown authors" if not present.
- chunks_used must be 1.

Document title: {title}
Chunk number: {index}
Chunk text:
\"\"\"{text}\"\"\"
"""

    def _merge_summary_prompt(self, title: str, chunk_summaries: list[SummaryResponse]) -> str:
        payload = json.dumps([item.model_dump() for item in chunk_summaries], ensure_ascii=True)
        return f"""
You are merging chunk summaries from one academic document into one final learner-friendly summary.
Return strict JSON only with these keys:
summary_title, authors, overview, body, takeaways, topics, chunks_used

Rules:
- Remove repetition.
- Keep the most important concepts only.
- body must contain 2 to 4 short paragraphs.
- takeaways must contain 3 to 5 strings.
- topics must contain 3 to 6 strings.
- chunks_used must equal the number of chunk summaries provided.

Document title: {title}
Chunk summaries JSON:
{payload}
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
        exclude_json = json.dumps(exclude_questions, ensure_ascii=True)
        module_json = json.dumps(module.model_dump(), ensure_ascii=True) if module else "null"
        weak_topics_json = json.dumps(weak_topics or [], ensure_ascii=True)
        return f"""
You are writing a multiple-choice quiz from an academic summary.
Return strict JSON only with these keys:
title, question_count, questions{', target_topics' if follow_up else ''}

Question rules:
- Generate exactly {question_count} questions.
- Each question must test understanding, not sentence copying.
- Each question must have exactly 4 options.
- Each question must include: question, options, correct_index, explanation, topic.
- Avoid repeating or lightly rewording any excluded questions.
- Keep explanations concise and specific.
- Target document topics only.

Additional behavior:
- difficulty: {difficulty}
- follow_up_quiz: {str(follow_up).lower()}
- If follow_up_quiz is true, prioritize weak topics and ask materially different questions.

Document title: {title}
Summary JSON:
{summary.model_dump_json()}
Weak topics JSON:
{weak_topics_json}
Learning module JSON:
{module_json}
Excluded questions JSON:
{exclude_json}
"""

    def _learning_module_prompt(self, payload: LearningModuleRequest) -> str:
        missed_json = json.dumps([item.model_dump() for item in payload.missed_questions], ensure_ascii=True)
        weak_topics_json = json.dumps(payload.weak_topics, ensure_ascii=True)
        return f"""
You are creating a short remediation learning module after a quiz.
Return strict JSON only with these keys:
title, description, focus_areas, sections, study_plan

Rules:
- Focus only on weak topics.
- focus_areas must contain 2 to 4 short strings.
- sections must contain 2 to 4 objects with topic, explanation, why_it_matters, practice_tip.
- study_plan must contain 3 to 5 specific next actions.
- Keep tone clear and student-friendly.

Document title: {payload.title}
Summary JSON:
{payload.summary.model_dump_json()}
Weak topics JSON:
{weak_topics_json}
Missed questions JSON:
{missed_json}
"""

    def _build_reviewed_questions(self, payload: AnalyzeResultsRequest) -> list[ReviewedQuestion]:
        reviewed: list[ReviewedQuestion] = []
        answers_by_index = {item.question_index: item for item in payload.answers}
        for index, question in enumerate(payload.questions):
            answer = answers_by_index.get(index)
            chosen_index = answer.chosen_index if answer else -1
            user_answer = "Skipped" if chosen_index < 0 else question.options[chosen_index]
            correct_answer = question.options[question.correct_index]
            reviewed.append(
                ReviewedQuestion(
                    question=question.question,
                    topic=question.topic,
                    user_answer=user_answer,
                    correct_answer=correct_answer,
                    is_correct=chosen_index == question.correct_index,
                    explanation=question.explanation,
                )
            )
        return reviewed

    def _derive_strengths(
        self, reviewed_questions: list[ReviewedQuestion], fallback_topics: list[str]
    ) -> list[str]:
        correct_topics = [item.topic for item in reviewed_questions if item.is_correct]
        ranked = [topic for topic, _ in Counter(correct_topics).most_common(4)]
        return ranked or fallback_topics[:2]

    def _derive_weak_topics(
        self, reviewed_questions: list[ReviewedQuestion], fallback_topics: list[str]
    ) -> list[str]:
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
        if not weak_topics:
            return [
                "No urgent revision needed. Review the summary once to keep recall fresh.",
                "Try the follow-up quiz for reinforcement or move to a new document.",
            ]
        base_topics = weak_topics or summary_topics[:2]
        return [f"Review {topic} with the learning module." for topic in base_topics[:4]]

    def _build_improvement_summary(
        self, score_delta: int, improved: list[str], remaining: list[str]
    ) -> str:
        if score_delta > 0 and improved:
            return (
                f"Your follow-up quiz improved by {score_delta} points. "
                f"Understanding was stronger in {', '.join(improved[:3])}."
            )
        if score_delta > 0:
            return f"Your follow-up quiz improved by {score_delta} points, with more consistent topic recall."
        if remaining:
            return (
                "The follow-up quiz shows that some weak areas still need attention, especially "
                + ", ".join(remaining[:3])
                + "."
            )
        return "The follow-up quiz kept performance stable, but more targeted revision is still recommended."

    def _build_next_steps(self, improved: list[str], remaining: list[str]) -> list[str]:
        steps: list[str] = []
        if improved:
            steps.append(f"Keep reinforcing {improved[0]} with another short recall session.")
        for topic in remaining[:2]:
            steps.append(f"Revisit {topic} and answer another set of targeted questions.")
        if len(steps) < 2:
            steps.append("Review the learning module summary before your next quiz.")
        return steps[:4]

    def _search_resource(
        self,
        *,
        query: str,
        resource_type: str,
        topic: str,
        preferred_domains: list[str],
    ) -> ResourceRecommendation | None:
        html = self._fetch_search_results(query)
        matches = re.findall(
            r'<a[^>]+class="result__a"[^>]+href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>.*?<a[^>]+class="result__snippet"[^>]*>(?P<snippet>.*?)</a>',
            html,
            flags=re.S,
        )
        if not matches:
            matches = re.findall(
                r'<a[^>]+class="result__a"[^>]+href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>',
                html,
                flags=re.S,
            )
            matches = [(href, title, "") for href, title in matches]

        for href, title, snippet in matches:
            url = self._extract_result_url(href)
            if not url or not url.startswith(("http://", "https://")):
                continue
            domain = urlparse(url).netloc.lower()
            if preferred_domains and not any(token in domain for token in preferred_domains):
                continue
            clean_title = self._strip_html(title)
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
        wiki = self._search_wikipedia_article(topic)
        if wiki:
            return wiki
        return self._search_resource_variants(
            topic=topic,
            resource_type="article",
            queries=[
                f'{title} {topic} explainer article',
                f'{topic} site:openstax.org',
                f'{topic} site:khanacademy.org',
            ],
            preferred_domains=["wikipedia.org", ".edu", ".org", "openstax.org", "khanacademy.org"],
        )

    def _search_video_resource(self, title: str, topic: str) -> ResourceRecommendation | None:
        youtube = self._search_youtube_video(f"{title} {topic} explainer", topic)
        if youtube:
            return youtube
        return self._search_resource_variants(
            topic=topic,
            resource_type="video",
            queries=[
                f'{title} {topic} site:youtube.com/watch',
                f'{topic} explainer site:youtube.com/watch',
            ],
            preferred_domains=["youtube.com", "youtu.be", "ted.com", "khanacademy.org"],
        )

    def _fetch_search_results(self, query: str) -> str:
        request = Request(
            f"https://html.duckduckgo.com/html/?q={quote_plus(query)}",
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                )
            },
        )
        with urlopen(request, timeout=20) as response:
            return response.read().decode("utf-8", errors="ignore")

    def _search_wikipedia_article(self, topic: str) -> ResourceRecommendation | None:
        request = Request(
            "https://en.wikipedia.org/w/api.php"
            f"?action=opensearch&search={quote_plus(topic)}&limit=1&namespace=0&format=json",
            headers={"User-Agent": "LearnovaAI/1.0"},
        )
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, list) or len(payload) < 4 or not payload[1]:
            return None
        title = str(payload[1][0])
        description = str(payload[2][0]) if payload[2] else f"Reference article for {topic}."
        url = str(payload[3][0]) if payload[3] else ""
        if not url:
            return None
        return ResourceRecommendation(
            topic=topic,
            title=f"{topic} overview: {title}",
            url=url,
            source="wikipedia.org",
            snippet=description[:400],
            resource_type="article",
        )

    def _search_youtube_video(self, query: str, topic: str) -> ResourceRecommendation | None:
        request = Request(
            f"https://www.youtube.com/results?search_query={quote_plus(query)}",
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                )
            },
        )
        with urlopen(request, timeout=20) as response:
            html = response.read().decode("utf-8", errors="ignore")

        candidates = re.findall(
            r'"videoId":"(?P<video_id>[A-Za-z0-9_-]{11})".{0,400}?"title":\{"runs":\[\{"text":"(?P<title>[^"]+)"',
            html,
            flags=re.S,
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
            snippet=f"Direct video recommendation matched to {topic}.",
            resource_type="video",
        )

    def _score_video_title_match(self, topic: str, title_text: str) -> int:
        topic_tokens = self._topic_tokens(topic)
        if not topic_tokens:
            return 0
        lowered_title = title_text.lower()
        score = sum(2 for token in topic_tokens if token in lowered_title)
        if "explainer" in lowered_title or "introduction" in lowered_title or "overview" in lowered_title:
            score += 1
        if "music" in lowered_title or "trailer" in lowered_title or "reaction" in lowered_title:
            score -= 2
        return score

    def _topic_tokens(self, topic: str) -> list[str]:
        stop_words = {"the", "and", "for", "with", "from", "into", "your", "this", "that"}
        tokens = re.findall(r"[a-zA-Z0-9]+", topic.lower())
        return [token for token in tokens if len(token) > 2 and token not in stop_words]

    def _extract_result_url(self, href: str) -> str:
        if "duckduckgo.com/l/?" not in href:
            return unescape(href)
        match = re.search(r"[?&]uddg=([^&]+)", href)
        if not match:
            return ""
        return unescape(unquote(match.group(1)))

    def _strip_html(self, value: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", unescape(value))).strip()

    def _build_article_fallback(self, topic: str) -> ResourceRecommendation:
        slug = re.sub(r"\s+", "_", topic.strip())
        return ResourceRecommendation(
            topic=topic,
            title=f"{topic} overview",
            url=f"https://en.wikipedia.org/wiki/{slug}",
            source="wikipedia.org",
            snippet=f"Fallback reference page for {topic}.",
            resource_type="article",
        )

    def _assert_unique_questions(self, questions: list) -> None:
        lowered = [item.question.strip().lower() for item in questions]
        if len(lowered) != len(set(lowered)):
            raise ValueError("AI output validation failed: quiz contains duplicate questions.")

    def _assert_no_repeated_questions(self, questions: list, previous_questions: list[str]) -> None:
        previous = {item.strip().lower() for item in previous_questions}
        if any(question.question.strip().lower() in previous for question in questions):
            raise ValueError("AI output validation failed: follow-up quiz repeated a previous question.")
