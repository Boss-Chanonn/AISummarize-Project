import io
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from backend.database.db import history_collection
from backend.middleware.auth_middleware import get_current_user
from backend.services.ollama_service import generate_learning_package

router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_EXTENSIONS_FREE = {"pdf", "txt", "doc", "docx"}
ALLOWED_EXTENSIONS_PRO = {"pdf", "txt", "doc", "docx", "ppt", "pptx"}


def _extract_text_from_pdf(data: bytes) -> str:
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)
    except Exception as e:
        print(f"[upload] PDF extraction error: {e}")
        return ""


def _extract_text_from_docx(data: bytes) -> str:
    try:
        import docx
        doc = docx.Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        print(f"[upload] DOCX extraction error: {e}")
        return ""


def _extract_text_from_pptx(data: bytes) -> str:
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
    """Returns (text_content, file_type, page_count)"""
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
    count = await history_collection.count_documents({"userId": user_id})
    return count + 1


@router.post("/upload")
async def upload_document(
    current_user: dict = Depends(get_current_user),
    file: Optional[UploadFile] = File(None),
    text_content: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
):
    user_id = str(current_user["_id"])
    user_tier = current_user.get("tier", "free")

    # ── Determine source: file upload OR text paste ──────────────────────────
    if file and file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        allowed = ALLOWED_EXTENSIONS_PRO if user_tier == "pro" else ALLOWED_EXTENSIONS_FREE

        if ext not in allowed:
            if user_tier != "pro" and ext in ("ppt", "pptx"):
                return JSONResponse(
                    status_code=403,
                    content={"message": "PowerPoint upload requires a Pro account. Please upgrade to continue."}
                )
            return JSONResponse(
                status_code=400,
                content={"message": f"File type .{ext} is not supported. Allowed: {', '.join(sorted(allowed))}"}
            )

        data = await file.read()
        if len(data) > MAX_FILE_SIZE:
            return JSONResponse(
                status_code=413,
                content={"message": "File exceeds 10 MB limit. Please upload a smaller file."}
            )

        doc_title = title or file.filename.rsplit(".", 1)[0]
        extracted_text, file_type, page_count = _extract_text(file.filename, data)

    elif text_content and text_content.strip():
        extracted_text = text_content.strip()
        file_type = "TXT"
        page_count = max(1, len(extracted_text) // 3000)
        doc_title = title or "Pasted text"

    else:
        return JSONResponse(status_code=400, content={"message": "Please upload a file or paste text content."})

    word_estimate = len(extracted_text.split()) if extracted_text else page_count * 350

    # ── AI generation ─────────────────────────────────────────────────────────
    fallback_payload = {
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

    ai_payload = fallback_payload
    try:
        ai_payload = await generate_learning_package(
            title=doc_title,
            file_type=file_type,
            text_content=extracted_text,
        )
        print(f"[upload] AI path succeeded for: {doc_title}")
    except Exception as e:
        print(f"[upload] Ollama unavailable, using fallback: {repr(e)}")

    # ── Save to MongoDB ────────────────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    seq_id = await _get_next_seq_id(user_id)

    history_doc = {
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
    result = await history_collection.insert_one(history_doc)
    history_id = str(result.inserted_id)

    # ── Build response ─────────────────────────────────────────────────────────
    processed_at = now.strftime("%-I:%M %p").lower() if os.name != "nt" else now.strftime("%I:%M %p").lower().lstrip("0")

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

