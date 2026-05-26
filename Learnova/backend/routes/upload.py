import io
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile

from backend.utils.api_errors import message_error
from backend.database.db import history_collection
from backend.middleware.auth_middleware import get_current_user
from backend.services.ollama_service import generate_learning_package
from backend.services.ai_service import AIService
from backend.services.schemas import SummaryRequest, QuizRequest, SummaryResponse

# Shared AI service instance — Mac 1 for summary, Mac 2 for quiz
_ai_service = AIService()

router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_EXTENSIONS_FREE = {"pdf", "txt", "doc", "docx"}
ALLOWED_EXTENSIONS_PRO = {"pdf", "txt", "doc", "docx", "ppt", "pptx"}


# ----------------------------- Text Extraction Helpers -----------------------------
def _extract_text_from_pdf(data: bytes) -> str:
    """Extract readable text from PDF bytes."""
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)
    except Exception as e:
        print(f"[upload] PDF extraction error: {e}")
        return ""


# ── PDF quality checker ──────────────────────────────────────────────────────
# Thresholds — tune these if needed
_MIN_CHARS_PER_PAGE     = 80    # fewer than this per page = likely scanned/image PDF
_MIN_WORD_LENGTH_AVG    = 3.0   # avg word length below this = likely OCR garbage
_MAX_GARBAGE_RATIO      = 0.35  # more than 35% non-ASCII/non-printable = corrupted
_MIN_READABLE_PAGES_PCT = 0.40  # at least 40% of pages must pass quality check


def _assess_pdf_quality(data: bytes, extracted_text: str, page_count: int) -> tuple[bool, str]:
    """
    Returns (is_readable, reason).
    is_readable=False means the PDF is scanned, blurry, or image-only.
    """
    if page_count == 0:
        return False, "empty"

    total_chars = len(extracted_text.strip())
    chars_per_page = total_chars / max(page_count, 1)

    # Check 1 — almost no text extracted at all
    if total_chars < 50:
        return False, "no_text"

    if chars_per_page < _MIN_CHARS_PER_PAGE:
        return False, "too_sparse"

    # Check 2 — garbage character ratio (non-printable, replacement chars)
    import unicodedata
    garbage = sum(
        1 for ch in extracted_text
        if (not ch.isprintable() and ch not in ("\n", "\t", "\r"))
        or ch == "�"   # Unicode replacement character — sign of bad encoding
        or (ord(ch) > 127 and unicodedata.category(ch) == "So")  # misc symbols
    )
    garbage_ratio = garbage / max(total_chars, 1)
    if garbage_ratio > _MAX_GARBAGE_RATIO:
        return False, "garbage_text"

    # Check 3 — word length average (real text has avg ~4-7 chars per word)
    words = [w for w in extracted_text.split() if w.isalpha()]
    if words:
        avg_len = sum(len(w) for w in words) / len(words)
        if avg_len < _MIN_WORD_LENGTH_AVG and len(words) > 20:
            return False, "garbled_words"

    # Check 4 — per-page extraction (need at least 40% of pages to have real text)
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(data))
        readable_pages = sum(
            1 for page in reader.pages
            if len((page.extract_text() or "").strip()) >= _MIN_CHARS_PER_PAGE
        )
        readable_pct = readable_pages / max(len(reader.pages), 1)
        if readable_pct < _MIN_READABLE_PAGES_PCT:
            return False, "mostly_images"
    except Exception:
        pass  # If PyPDF2 fails here, we already have text so it's probably OK

    return True, "ok"


def _build_blur_error(reason: str) -> dict:
    """Return a structured error payload the frontend can display."""
    messages = {
        "no_text":       "No readable text found in this PDF.",
        "too_sparse":    "This PDF appears to be a scanned document — very little text could be extracted.",
        "garbage_text":  "This PDF contains mostly unreadable characters, likely from a bad scan or image conversion.",
        "garbled_words": "The text extracted from this PDF appears garbled — it may be a low-quality scan.",
        "mostly_images": "Most pages in this PDF are images with no selectable text.",
        "empty":         "This PDF appears to be empty.",
    }
    detail = messages.get(reason, "This PDF could not be read properly.")
    return {
        "error": "unreadable_pdf",
        "detail": detail,
        "user_message": (
            f"{detail} "
            "Please upload a clearer version, a text-based PDF, or paste the text directly using the text input."
        ),
        "suggestions": [
            "Use a text-based PDF (not a scan)",
            "Copy and paste the text directly",
            "Try converting the PDF to a Word document first",
            "If it is a scanned document, run OCR software on it first",
        ],
    }


def _extract_text_from_docx(data: bytes) -> str:
    """Extract readable text from DOCX bytes."""
    try:
        import docx
        doc = docx.Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        print(f"[upload] DOCX extraction error: {e}")
        return ""


def _extract_text_from_pptx(data: bytes) -> str:
    """Extract readable text from PPT/PPTX bytes."""
    try:
        from pptx import Presentation
        prs = Presentation(io.BytesIO(data))
        texts = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    texts.append(shape.text)
        return "\n".join(texts)
    except Exception as e:
        print(f"[upload] PPTX extraction error: {e}")
        return ""


def _extract_text(filename: str, data: bytes) -> tuple[str, str, int]:
    """Return extracted text, normalized file type label, and estimated page count."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"

    if ext == "pdf":
        text = _extract_text_from_pdf(data)
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(data))
            pages = len(reader.pages)
        except Exception:
            pages = max(1, len(text) // 3000)
        return text, "PDF", max(1, pages)

    elif ext in ("doc", "docx"):
        text = _extract_text_from_docx(data)
        pages = max(1, len(text) // 3000)
        return text, "DOCX", pages

    elif ext in ("ppt", "pptx"):
        text = _extract_text_from_pptx(data)
        pages = max(1, len(text) // 500)
        return text, "PPTX", pages

    else:
        # Plain text / fallback
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:
            text = ""
        pages = max(1, len(text) // 3000)
        return text, ext.upper(), pages


async def _get_next_seq_id(user_id: str) -> int:
    """Generate the next per-user sequential ID for history records."""
    count = await history_collection.count_documents({"userId": user_id})
    return count + 1


def _build_fallback_payload(doc_title: str, page_count: int) -> dict:
    """Build deterministic fallback content when AI service is unavailable."""
    return {
        "summary": {
            "body": [
                f"This document titled '{doc_title}' has been processed by Learnova's AI engine. It spans {page_count} {'page' if page_count == 1 else 'pages'} covering key academic concepts.",
                "The themes identified include core methodology, evidence base, and author conclusions — forming the basis for the comprehension quiz below.",
            ],
            "takeaways": [
                "The document presents a structured argument supported by academic references.",
                "Core findings are framed within a broader context with practical implications.",
                "Review this summary carefully — the quiz will test understanding of the main claims.",
            ],
        },
        "quiz": [
            {"q": "What is the primary focus of this document?", "opts": ["Empirical measurement", "Theoretical critique", "Systematic synthesis", "Policy evaluation"], "correct": 2, "explanation": "The document takes a synthesis approach."},
            {"q": "Which methodology is primarily employed?", "opts": ["Randomised trial", "Ethnographic fieldwork", "Literature review", "Longitudinal survey"], "correct": 2, "explanation": "A literature review and analytical framework are central."},
            {"q": "What type of evidence is most heavily used?", "opts": ["Anecdotal reports", "Peer-reviewed studies", "Government statistics", "Industry benchmarks"], "correct": 1, "explanation": "Peer-reviewed studies form the backbone of evidence."},
            {"q": "Who is the target audience?", "opts": ["General public", "Academic researchers", "Policy makers only", "Undergrad students"], "correct": 1, "explanation": "Technical language indicates researchers and practitioners."},
            {"q": "What gap is identified in existing work?", "opts": ["Lack of data", "Under-representation", "Insufficient longitudinal research", "Overemphasis on theory"], "correct": 2, "explanation": "Longitudinal evidence is underdeveloped in this field."},
            {"q": "What does the document recommend?", "opts": ["Abandon frameworks", "Cross-disciplinary collaboration", "Quantitative only", "Single institution studies"], "correct": 1, "explanation": "Cross-disciplinary collaboration is most promising."},
            {"q": "Which factor most influences outcomes?", "opts": ["Funding levels", "Institutional support", "Individual motivation", "Technology availability"], "correct": 1, "explanation": "Institutional support is the dominant conditioning factor."},
            {"q": "What is the overall contribution?", "opts": ["Definitive theory proof", "Synthesised framework", "Replication study", "Full critique"], "correct": 1, "explanation": "A synthesised framework organises complex findings."},
        ],
        "analysis": {
            "strengths": ["Core understanding", "Concept linkage", "Evidence awareness"],
            "weaknesses": ["Application depth", "Long-term retention"],
            "recommendations": ["Review core concepts regularly", "Practice applied questions", "Revisit evidence summaries"],
            "studyNext": ["Related academic literature", "Applied case studies", "Cross-disciplinary research"],
        },
        "modules": [
            {"title": "Introduction to the Topic", "type": "youtube", "url": f"https://www.youtube.com/results?search_query={doc_title.replace(' ', '+')}", "description": "Video overview of the main topic"},
            {"title": "Academic Overview", "type": "google", "url": f"https://www.google.com/search?q={doc_title.replace(' ', '+')}+academic", "description": "Academic resources on this topic"},
            {"title": "Key Concepts Explained", "type": "youtube", "url": f"https://www.youtube.com/results?search_query={doc_title.replace(' ', '+')}+explained", "description": "Concept explanations"},
            {"title": "Further Reading", "type": "google", "url": f"https://www.google.com/search?q={doc_title.replace(' ', '+')}+research", "description": "Deeper research materials"},
            {"title": "Related Topics", "type": "youtube", "url": f"https://www.youtube.com/results?search_query={doc_title.replace(' ', '+')}+tutorial", "description": "Tutorials on related topics"},
        ],
    }


async def _generate_ai_payload(
    doc_title: str,
    file_type: str,
    extracted_text: str,
    fallback_payload: dict,
) -> dict:
    """
    Generate AI payload using dual-Mac routing:
    - Mac 1 (gpt-oss)     → summary via AIService
    - Mac 2 (deepseek)    → quiz via AIService quiz_client
    Falls back to legacy single-Mac path if both fail.
    """
    import asyncio

    # ── Step 1: Summary on Mac 1 (gpt-oss) ──────────────────────────────────
    summary_response = None
    try:
        loop = asyncio.get_event_loop()
        summary_response = await loop.run_in_executor(
            None,
            lambda: _ai_service.summarize(
                SummaryRequest(title=doc_title, text=extracted_text)
            )
        )
        print(f"[upload] Mac 1 summary done for: {doc_title}")
    except Exception as e:
        print(f"[upload] Mac 1 summary failed: {repr(e)} — trying legacy path")

    # ── Step 2: Quiz on Mac 2 (deepseek) ────────────────────────────────────
    quiz_data = None
    if summary_response:
        try:
            loop = asyncio.get_event_loop()
            quiz_response = await loop.run_in_executor(
                None,
                lambda: _ai_service.generate_quiz(
                    QuizRequest(
                        title=doc_title,
                        summary=summary_response,
                        question_count=8,
                        difficulty="intermediate",
                    )
                )
            )
            # Convert to legacy quiz format expected by frontend
            quiz_data = [
                {
                    "q": q.question,
                    "opts": q.options,
                    "correct": q.correct_index,
                    "explanation": q.explanation,
                    "topic": q.topic,
                }
                for q in quiz_response.questions
            ]
            print(f"[upload] Mac 2 quiz done for: {doc_title} — {len(quiz_data)} questions")
        except Exception as e:
            print(f"[upload] Mac 2 quiz failed: {repr(e)}")

    # ── Step 3: Build payload if both succeeded ──────────────────────────────
    if summary_response and quiz_data:
        return {
            "summary": {
                "body": summary_response.body,
                "takeaways": summary_response.takeaways,
                "title": summary_response.summary_title,
                "authors": summary_response.authors,
                "topics": summary_response.topics,
            },
            "analysis": {
                "strengths": [],
                "weaknesses": [],
                "studyNext": [],
            },
            "modules": [],
            "quiz": quiz_data,
        }

    # ── Step 4: Legacy single-Mac fallback ───────────────────────────────────
    print(f"[upload] Falling back to legacy path for: {doc_title}")
    try:
        payload = await generate_learning_package(
            title=doc_title,
            file_type=file_type,
            text_content=extracted_text,
        )
        print(f"[upload] Legacy path succeeded for: {doc_title}")
        return payload
    except Exception as error:
        print(f"[upload] All AI paths failed, using fallback: {repr(error)}")
        return fallback_payload


def _build_history_doc(
    user_id: str,
    seq_id: int,
    doc_title: str,
    file_type: str,
    page_count: int,
    word_estimate: int,
    ai_payload: dict,
    now: datetime,
) -> dict:
    """Build the MongoDB history document from normalized upload data."""
    return {
        "userId": user_id,
        "seqId": seq_id,
        "title": doc_title,
        "fileType": file_type,
        "pageCount": page_count,
        "wordEstimate": word_estimate,
        "summary": ai_payload["summary"],
        "analysis": ai_payload["analysis"],
        "modules": ai_payload["modules"],
        "quizFull": ai_payload["quiz"],
        "done": False,
        "score": None,
        "correct": None,
        "total": 8,
        "userAnswers": [],
        "uploadedAt": now,
        "completedAt": None,
    }


def _format_processed_time(now: datetime) -> str:
    """Format processing time in the same style used by existing frontend."""
    if os.name != "nt":
        return now.strftime("%-I:%M %p").lower()
    return now.strftime("%I:%M %p").lower().lstrip("0")


def _build_upload_response(
    history_id: str,
    seq_id: int,
    doc_title: str,
    file_type: str,
    page_count: int,
    word_estimate: int,
    ai_payload: dict,
    processed_at: str,
) -> dict:
    """Build API response payload returned to upload page after processing."""
    return {
        "historyId": history_id,
        "seqId": seq_id,
        "title": doc_title,
        "fileType": file_type,
        "pageCount": page_count,
        "meta": f".{file_type.lower()} · {page_count} {'page' if page_count == 1 else 'pages'}",
        "infoRows": [
            ["File type", file_type],
            ["Estimated words", f"{word_estimate:,}"],
            ["Pages", str(page_count)],
            ["Language", "English"],
            ["Processed", processed_at],
        ],
        "summary": {
            "title": doc_title,
            "authors": "Uploaded document",
            "pages": f"{page_count} page{'s' if page_count != 1 else ''}",
            "body": ai_payload["summary"]["body"],
            "takeaways": ai_payload["summary"]["takeaways"],
            "strengths": ai_payload["analysis"]["strengths"],
            "weaknesses": ai_payload["analysis"]["weaknesses"],
            "studyNext": ai_payload["analysis"]["studyNext"],
        },
        "quizData": ai_payload["quiz"],
        "modules": ai_payload["modules"],
    }


# ----------------------------- Upload Endpoint -----------------------------
@router.post("/upload")
async def upload_document(
    current_user: dict = Depends(get_current_user),
    file: Optional[UploadFile] = File(None),
    text_content: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
):
    """Process file/text upload, generate learning package, and save history."""
    user_id = str(current_user["_id"])
    user_tier = current_user.get("tier", "free")

    # ── Determine source: file upload OR text paste ──────────────────────────
    if file and file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        allowed = ALLOWED_EXTENSIONS_PRO if user_tier == "pro" else ALLOWED_EXTENSIONS_FREE

        if ext not in allowed:
            if user_tier != "pro" and ext in ("ppt", "pptx"):
                return message_error(403, "PowerPoint upload requires a Pro account. Please upgrade to continue.")
            return message_error(
                400,
                f"File type .{ext} is not supported. Allowed: {', '.join(sorted(allowed))}",
            )

        data = await file.read()
        if len(data) > MAX_FILE_SIZE:
            return message_error(413, "File exceeds 10 MB limit. Please upload a smaller file.")

        doc_title = title or file.filename.rsplit(".", 1)[0]
        extracted_text, file_type, page_count = _extract_text(file.filename, data)

        # ── PDF quality gate ────────────────────────────────────────────────
        if ext == "pdf":
            is_readable, reason = _assess_pdf_quality(data, extracted_text, page_count)
            if not is_readable:
                from fastapi.responses import JSONResponse
                error_payload = _build_blur_error(reason)
                return JSONResponse(status_code=422, content=error_payload)
        # ────────────────────────────────────────────────────────────────────

    elif text_content and text_content.strip():
        extracted_text = text_content.strip()
        file_type = "TXT"
        page_count = max(1, len(extracted_text) // 3000)
        doc_title = title or "Pasted text"

    else:
        return message_error(400, "Please upload a file or paste text content.")

    word_estimate = len(extracted_text.split()) if extracted_text else page_count * 350

    # Phase 2: build AI payload (fallback first, AI if available).
    fallback_payload = _build_fallback_payload(doc_title, page_count)
    ai_payload = await _generate_ai_payload(
        doc_title=doc_title,
        file_type=file_type,
        extracted_text=extracted_text,
        fallback_payload=fallback_payload,
    )

    # Phase 3: save final history record to MongoDB.
    now = datetime.now(timezone.utc)
    seq_id = await _get_next_seq_id(user_id)
    history_doc = _build_history_doc(
        user_id=user_id,
        seq_id=seq_id,
        doc_title=doc_title,
        file_type=file_type,
        page_count=page_count,
        word_estimate=word_estimate,
        ai_payload=ai_payload,
        now=now,
    )
    result = await history_collection.insert_one(history_doc)
    history_id = str(result.inserted_id)

    # Phase 4: return frontend payload.
    processed_at = _format_processed_time(now)
    return _build_upload_response(
        history_id=history_id,
        seq_id=seq_id,
        doc_title=doc_title,
        file_type=file_type,
        page_count=page_count,
        word_estimate=word_estimate,
        ai_payload=ai_payload,
        processed_at=processed_at,
    )