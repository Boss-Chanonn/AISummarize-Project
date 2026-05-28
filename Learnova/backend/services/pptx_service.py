"""
pptx_service.py
===============
Handles everything PPTX-specific:
  1. Per-slide text extraction (python-pptx)
  2. Per-slide AI summarisation (Mac 1 — gpt-oss)
  3. Slice a stored summary by slide range
  4. Module unlock logic (all slides covered?)

Install dependency if not present:
    pip install python-pptx --break-system-packages
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field

from pptx import Presentation  # pip install python-pptx

from backend.services.ollama_client import OllamaClient, OllamaError, SummaryOllamaSettings
from backend.services.schemas import SummaryResponse


# ── Per-slide data structures ─────────────────────────────────────────────────

@dataclass
class SlideText:
    slide_number: int       # 1-indexed
    title: str
    body: str
    full_text: str          # title + body combined


@dataclass
class SlideSummary:
    slide_number: int
    summary_title: str
    overview: str
    topics: list[str] = field(default_factory=list)
    takeaways: list[str] = field(default_factory=list)


@dataclass
class PptxDocument:
    title: str
    total_slides: int
    slide_summaries: list[SlideSummary]


# ── Text extraction ───────────────────────────────────────────────────────────

def extract_slides(data: bytes) -> list[SlideText]:
    """Extract per-slide text from PPTX bytes. Returns one SlideText per slide."""
    prs = Presentation(io.BytesIO(data))
    slides: list[SlideText] = []

    for i, slide in enumerate(prs.slides, start=1):
        title_text = ""
        body_parts: list[str] = []

        for shape in slide.shapes:
            if not hasattr(shape, "text"):
                continue
            text = shape.text.strip()
            if not text:
                continue
            # First text frame that looks like a title
            if not title_text and hasattr(shape, "name") and "title" in shape.name.lower():
                title_text = text
            else:
                body_parts.append(text)

        # Fallback: use first shape text as title
        if not title_text and body_parts:
            title_text = body_parts.pop(0)

        body = "\n".join(body_parts)
        full_text = f"{title_text}\n{body}".strip()

        slides.append(SlideText(
            slide_number=i,
            title=title_text or f"Slide {i}",
            body=body,
            full_text=full_text,
        ))

    return slides


# ── AI summarisation per slide ────────────────────────────────────────────────

_SLIDE_SUMMARY_PROMPT = """You are an expert academic summariser.

Summarise slide {slide_number} of a presentation titled "{pptx_title}".

Slide title: {slide_title}
Slide content:
{slide_text}

Return a JSON object with these exact keys:
{{
  "summary_title": "concise title for this slide (max 80 chars)",
  "overview": "2-3 sentence explanation of what this slide covers (min 60 chars)",
  "topics": ["topic1", "topic2"],
  "takeaways": ["key point 1", "key point 2", "key point 3"]
}}

Return only the JSON object. No preamble, no markdown.
"""


def _summarise_slide(
    client: OllamaClient,
    pptx_title: str,
    slide: SlideText,
    retries: int = 2,
) -> SlideSummary:
    """Call Mac 1 to summarise a single slide. Retries on failure."""
    import json

    if len(slide.full_text.strip()) < 30:
        # Slide is nearly empty — return a stub
        return SlideSummary(
            slide_number=slide.slide_number,
            summary_title=slide.title or f"Slide {slide.slide_number}",
            overview="This slide contains minimal text content.",
            topics=[],
            takeaways=[],
        )

    prompt = _SLIDE_SUMMARY_PROMPT.format(
        slide_number=slide.slide_number,
        pptx_title=pptx_title,
        slide_title=slide.title,
        slide_text=slide.full_text[:2000],   # cap to avoid token overflow
    )

    errors: list[str] = []
    for _ in range(retries + 1):
        try:
            raw = client.generate_json(prompt)
            return SlideSummary(
                slide_number=slide.slide_number,
                summary_title=str(raw.get("summary_title", slide.title))[:80],
                overview=str(raw.get("overview", ""))[:600],
                topics=[str(t) for t in raw.get("topics", [])][:4],
                takeaways=[str(t) for t in raw.get("takeaways", [])][:4],
            )
        except (OllamaError, Exception) as exc:
            errors.append(str(exc))

    # All retries failed — return a stub with the error logged
    return SlideSummary(
        slide_number=slide.slide_number,
        summary_title=slide.title or f"Slide {slide.slide_number}",
        overview=f"Summary unavailable. ({errors[-1][:120]})",
        topics=[],
        takeaways=[],
    )


def summarise_all_slides(
    pptx_title: str,
    slides: list[SlideText],
    client: OllamaClient | None = None,
) -> list[SlideSummary]:
    """
    Summarise every slide via Mac 1 (gpt-oss).
    Called once at upload time — results are stored in MongoDB.
    """
    active_client = client or OllamaClient(SummaryOllamaSettings())
    return [_summarise_slide(active_client, pptx_title, slide) for slide in slides]


# ── Slice helpers ─────────────────────────────────────────────────────────────

def slice_summaries(
    all_summaries: list[SlideSummary],
    start: int,
    end: int,
) -> list[SlideSummary]:
    """
    Return slide summaries for a given range [start, end] (both inclusive, 1-indexed).
    This is the core of the "no re-processing" feature — slicing the cached summaries.
    """
    return [s for s in all_summaries if start <= s.slide_number <= end]


def build_range_summary_text(
    pptx_title: str,
    summaries: list[SlideSummary],
) -> str:
    """
    Flatten a list of SlideSummary objects into a single text block
    suitable for sending to the quiz generator.
    """
    parts = [f"Presentation: {pptx_title}\n"]
    for s in summaries:
        parts.append(
            f"Slide {s.slide_number}: {s.summary_title}\n"
            f"{s.overview}\n"
            f"Key topics: {', '.join(s.topics)}\n"
            f"Takeaways: {'; '.join(s.takeaways)}\n"
        )
    return "\n".join(parts)


def build_range_summary_response(
    pptx_title: str,
    summaries: list[SlideSummary],
    start: int,
    end: int,
) -> SummaryResponse:
    """
    Build a SummaryResponse-compatible object from a slide range.
    This is passed to the quiz generator as if it were a regular document summary.
    """
    all_topics: list[str] = []
    all_takeaways: list[str] = []
    overviews: list[str] = []

    for s in summaries:
        overviews.append(f"Slide {s.slide_number}: {s.overview}")
        all_topics.extend(s.topics)
        all_takeaways.extend(s.takeaways)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_topics: list[str] = []
    for t in all_topics:
        if t not in seen:
            seen.add(t)
            unique_topics.append(t)

    seen = set()
    unique_takeaways: list[str] = []
    for t in all_takeaways:
        if t not in seen:
            seen.add(t)
            unique_takeaways.append(t)

    return SummaryResponse(
        summary_title=f"{pptx_title} — Slides {start}–{end}",
        authors="Presentation",
        overview=f"Session covering slides {start} to {end} of {pptx_title}.",
        body=overviews[:4] if overviews else [f"Slides {start}–{end} of {pptx_title}."],
        takeaways=unique_takeaways[:5] if unique_takeaways else ["Review the slides."],
        topics=unique_topics[:6] if unique_topics else ["General content"],
        chunks_used=len(summaries),
    )


# ── Module unlock check ───────────────────────────────────────────────────────

def all_slides_covered(total_slides: int, sessions: list[dict]) -> bool:
    """
    Returns True when every slide from 1..total_slides has been included
    in at least one completed session.
    """
    covered: set[int] = set()
    for session in sessions:
        if session.get("done"):
            start = session.get("slide_start", 0)
            end = session.get("slide_end", 0)
            covered.update(range(start, end + 1))
    return all(i in covered for i in range(1, total_slides + 1))
