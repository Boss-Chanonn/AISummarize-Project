"""
routes/pptx.py
==============
All PPTX-related endpoints.

HOW TO INTEGRATE — add two lines in backend/main.py:
    from backend.routes.pptx import router as pptx_router
    app.include_router(pptx_router, prefix="/api/pptx", tags=["pptx"])
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.database.db import db
from backend.middleware.auth_middleware import get_current_user
from backend.services.ollama_client import OllamaClient, QuizOllamaSettings, SummaryOllamaSettings
from backend.services.pptx_service import (
    all_slides_covered,
    build_range_summary_response,
    extract_slides,
    slice_summaries,
    summarise_all_slides,
)
from backend.services.ai_service import AIService
from backend.services.schemas import QuizRequest

router = APIRouter()

# ── MongoDB collection ────────────────────────────────────────────────────────
pptx_collection = db["pptx_documents"]

# ── AI service (dual-Mac) ─────────────────────────────────────────────────────
_service = AIService(
    client=OllamaClient(SummaryOllamaSettings()),
    quiz_client=OllamaClient(QuizOllamaSettings()),
)

# ── In-memory quiz job store (same pattern as ai.py) ─────────────────────────
_quiz_jobs: dict[str, dict[str, Any]] = {}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# ── Helpers ───────────────────────────────────────────────────────────────────
def _require_pro(user: dict) -> None:
    if user.get("tier") != "pro":
        raise HTTPException(
            status_code=403,
            detail="PPTX upload is a Pro feature. Upgrade to access it.",
        )


def _doc_not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="PPTX document not found.")


def _serialize(doc: dict) -> dict:
    """Convert MongoDB doc to JSON-safe dict."""
    doc["id"] = str(doc.pop("_id"))
    return doc


# ── Background jobs ───────────────────────────────────────────────────────────
def _run_slide_summarisation(doc_id: str, pptx_title: str, slides_data: list[dict]) -> None:
    """
    Background task: summarise every slide on Mac 1, then save to MongoDB.
    slides_data is a list of dicts with keys: slide_number, title, body, full_text.
    """
    from backend.services.pptx_service import SlideText, _summarise_slide
    import asyncio

    slides = [
        SlideText(
            slide_number=s["slide_number"],
            title=s["title"],
            body=s["body"],
            full_text=s["full_text"],
        )
        for s in slides_data
    ]

    summaries = summarise_all_slides(pptx_title, slides, _service.client)
    summaries_dicts = [
        {
            "slide_number": s.slide_number,
            "summary_title": s.summary_title,
            "overview": s.overview,
            "topics": s.topics,
            "takeaways": s.takeaways,
        }
        for s in summaries
    ]

    async def _update():
        await pptx_collection.update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {
                "slide_summaries": summaries_dicts,
                "status": "ready",
                "summarised_at": datetime.now(timezone.utc),
            }},
        )

    asyncio.run(_update())


def _run_quiz_job(job_id: str, payload: QuizRequest) -> None:
    """Background task: generate quiz on Mac 2 (deepseek)."""
    try:
        result = _service.generate_quiz(payload)
        _quiz_jobs[job_id] = {"status": "done", "result": result, "error": None}
    except Exception as exc:
        _quiz_jobs[job_id] = {"status": "error", "result": None, "error": str(exc)}


# ── Request / Response schemas ────────────────────────────────────────────────
class SessionStartRequest(BaseModel):
    doc_id: str
    slide_start: int
    slide_end: int
    session_label: str = ""          # e.g. "Session 2 — Slides 6–10"


class SessionStartResponse(BaseModel):
    session_id: str
    job_id: str
    quiz_status: str = "pending"
    slide_summaries: list[dict]
    summary_title: str
    overview: str
    topics: list[str]
    takeaways: list[str]
    module_unlocked: bool


class QuizStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Any = None
    error: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_pptx(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload a PPTX file (Pro only).
    1. Validates file type and size.
    2. Extracts per-slide text immediately.
    3. Saves a document record to MongoDB with status="processing".
    4. Fires slide summarisation on Mac 1 as a background task.
    5. Returns the doc_id so the frontend can poll for readiness.
    """
    _require_pro(current_user)

    filename = file.filename or "presentation.pptx"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("ppt", "pptx"):
        raise HTTPException(status_code=400, detail="Only .pptx / .ppt files are accepted.")

    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds the 10 MB limit.")

    # Extract per-slide text
    try:
        slides = extract_slides(data)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse PPTX: {exc}") from exc

    if not slides:
        raise HTTPException(status_code=422, detail="No slides found in this presentation.")

    total_slides = len(slides)

    # Persist initial record
    doc = {
        "user_id": current_user["id"],
        "title": filename.rsplit(".", 1)[0],
        "filename": filename,
        "total_slides": total_slides,
        "status": "processing",       # → "ready" after background task
        "slide_summaries": [],
        "sessions": [],
        "module_unlocked": False,
        "created_at": datetime.now(timezone.utc),
    }
    result = await pptx_collection.insert_one(doc)
    doc_id = str(result.inserted_id)

    # Serialise slide text for the background task (no pydantic objects)
    slides_data = [
        {
            "slide_number": s.slide_number,
            "title": s.title,
            "body": s.body,
            "full_text": s.full_text,
        }
        for s in slides
    ]

    background_tasks.add_task(
        _run_slide_summarisation,
        doc_id,
        doc["title"],
        slides_data,
    )

    return {
        "doc_id": doc_id,
        "title": doc["title"],
        "total_slides": total_slides,
        "status": "processing",
        "message": f"Uploaded {total_slides} slides. AI is summarising in the background.",
    }


@router.get("/status/{doc_id}")
async def pptx_status(
    doc_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Poll this endpoint after upload until status == 'ready'.
    Frontend polls every 4 seconds.
    """
    _require_pro(current_user)
    try:
        doc = await pptx_collection.find_one({"_id": ObjectId(doc_id), "user_id": current_user["id"]})
    except Exception:
        raise _doc_not_found()

    if not doc:
        raise _doc_not_found()

    return {
        "doc_id": doc_id,
        "title": doc["title"],
        "total_slides": doc["total_slides"],
        "status": doc["status"],
        "sessions": doc.get("sessions", []),
        "module_unlocked": doc.get("module_unlocked", False),
    }


@router.get("/my-documents")
async def my_pptx_documents(current_user: dict = Depends(get_current_user)):
    """Return all PPTX documents for the current user."""
    _require_pro(current_user)
    cursor = pptx_collection.find(
        {"user_id": current_user["id"]},
        {"slide_summaries": 0}   # exclude large field from list view
    ).sort("created_at", -1).limit(20)
    docs = await cursor.to_list(length=20)
    return [_serialize(d) for d in docs]


@router.post("/session/start", response_model=SessionStartResponse)
async def start_session(
    payload: SessionStartRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """
    Start a study session for a slide range.
    1. Loads the stored per-slide summaries from MongoDB (no re-processing).
    2. Slices the requested range.
    3. Queues quiz generation on Mac 2 as a background task.
    4. Returns the sliced summaries + job_id immediately.
    """
    _require_pro(current_user)

    try:
        doc = await pptx_collection.find_one({
            "_id": ObjectId(payload.doc_id),
            "user_id": current_user["id"],
        })
    except Exception:
        raise _doc_not_found()

    if not doc:
        raise _doc_not_found()

    if doc["status"] != "ready":
        raise HTTPException(
            status_code=409,
            detail="Slides are still being summarised. Please wait a moment.",
        )

    total = doc["total_slides"]
    start = max(1, payload.slide_start)
    end = min(total, payload.slide_end)

    if start > end:
        raise HTTPException(status_code=400, detail="slide_start must be ≤ slide_end.")

    # Rebuild SlideSummary objects from stored dicts
    from backend.services.pptx_service import SlideSummary
    all_summaries = [
        SlideSummary(
            slide_number=s["slide_number"],
            summary_title=s["summary_title"],
            overview=s["overview"],
            topics=s.get("topics", []),
            takeaways=s.get("takeaways", []),
        )
        for s in doc.get("slide_summaries", [])
    ]

    range_summaries = slice_summaries(all_summaries, start, end)
    if not range_summaries:
        raise HTTPException(status_code=400, detail="No summaries found for this slide range.")

    # Build a SummaryResponse to send to quiz generator
    summary_response = build_range_summary_response(doc["title"], range_summaries, start, end)

    # Create a session record in MongoDB
    session_id = str(uuid.uuid4())
    label = payload.session_label or f"Session {len(doc.get('sessions', [])) + 1} — Slides {start}–{end}"
    new_session = {
        "session_id": session_id,
        "label": label,
        "slide_start": start,
        "slide_end": end,
        "done": False,
        "score": None,
        "quiz_job_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await pptx_collection.update_one(
        {"_id": ObjectId(payload.doc_id)},
        {"$push": {"sessions": new_session}},
    )

    # Queue quiz on Mac 2
    job_id = str(uuid.uuid4())
    _quiz_jobs[job_id] = {"status": "pending", "result": None, "error": None}
    quiz_payload = QuizRequest(
        title=f"{doc['title']} — Slides {start}–{end}",
        summary=summary_response,
        question_count=6,
        difficulty="intermediate",
        exclude_questions=[],
    )
    background_tasks.add_task(_run_quiz_job, job_id, quiz_payload)

    # Update session with job_id
    await pptx_collection.update_one(
        {"_id": ObjectId(payload.doc_id), "sessions.session_id": session_id},
        {"$set": {"sessions.$.quiz_job_id": job_id}},
    )

    # Check module unlock
    updated_doc = await pptx_collection.find_one({"_id": ObjectId(payload.doc_id)})
    sessions = updated_doc.get("sessions", [])
    # Mark this session as "done" immediately for coverage tracking
    # (quiz completion is tracked separately via score)
    sessions_with_current = sessions.copy()
    for s in sessions_with_current:
        if s["session_id"] == session_id:
            s["done"] = True
    module_unlocked = all_slides_covered(total, sessions_with_current)

    if module_unlocked and not doc.get("module_unlocked"):
        await pptx_collection.update_one(
            {"_id": ObjectId(payload.doc_id)},
            {"$set": {"module_unlocked": True}},
        )

    return SessionStartResponse(
        session_id=session_id,
        job_id=job_id,
        quiz_status="pending",
        slide_summaries=[
            {
                "slide_number": s.slide_number,
                "summary_title": s.summary_title,
                "overview": s.overview,
                "topics": s.topics,
                "takeaways": s.takeaways,
            }
            for s in range_summaries
        ],
        summary_title=summary_response.summary_title,
        overview=summary_response.overview,
        topics=summary_response.topics,
        takeaways=summary_response.takeaways,
        module_unlocked=module_unlocked,
    )


@router.get("/quiz-status/{job_id}", response_model=QuizStatusResponse)
def quiz_status(job_id: str):
    """Poll for quiz readiness after starting a session."""
    job = _quiz_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"No quiz job found: {job_id}")
    return QuizStatusResponse(
        job_id=job_id,
        status=job["status"],
        result=job.get("result"),
        error=job.get("error"),
    )


@router.post("/session/complete")
async def complete_session(
    doc_id: str,
    session_id: str,
    score: int,
    current_user: dict = Depends(get_current_user),
):
    """Mark a session as complete and save the quiz score."""
    _require_pro(current_user)
    result = await pptx_collection.update_one(
        {
            "_id": ObjectId(doc_id),
            "user_id": current_user["id"],
            "sessions.session_id": session_id,
        },
        {"$set": {
            "sessions.$.done": True,
            "sessions.$.score": score,
            "sessions.$.completed_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    if result.matched_count == 0:
        raise _doc_not_found()
    return {"ok": True}
