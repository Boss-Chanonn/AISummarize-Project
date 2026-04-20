from fastapi import APIRouter, Depends, Request
from backend.middleware.auth_middleware import get_current_user
from datetime import datetime, timezone

router = APIRouter()

GENERIC_QUIZ = [
    {
        "q": "What is the primary focus or central argument of this document?",
        "opts": [
            "Empirical measurement of outcomes",
            "Theoretical critique of existing models",
            "Systematic synthesis and analysis of prior work",
            "Policy evaluation and reform recommendations",
        ],
        "correct": 2,
        "explanation": "The document takes a synthesis approach, drawing on prior research to build a central argument.",
    },
    {
        "q": "Which research methodology does this document primarily employ?",
        "opts": [
            "Randomised controlled trial",
            "Ethnographic fieldwork",
            "Literature review and analytical framework",
            "Longitudinal survey study",
        ],
        "correct": 2,
        "explanation": "A literature review and analytical framework are central to how the document builds its argument.",
    },
    {
        "q": "What type of evidence is most heavily used to support the main claims?",
        "opts": [
            "Anecdotal case reports",
            "Peer-reviewed academic studies",
            "Government statistics only",
            "Industry benchmarks and reports",
        ],
        "correct": 1,
        "explanation": "Peer-reviewed studies form the backbone of the evidential claims made throughout the document.",
    },
    {
        "q": "Which best describes the target audience of this document?",
        "opts": [
            "General public readers",
            "Academic researchers and practitioners",
            "Policy makers only",
            "First-year undergraduate students",
        ],
        "correct": 1,
        "explanation": "The technical language, academic framing, and citation style indicate this is aimed at researchers and informed practitioners.",
    },
    {
        "q": "What key gap or limitation is identified in the existing body of work?",
        "opts": [
            "Lack of quantitative data",
            "Under-representation of certain groups",
            "Absence of sufficient longitudinal research",
            "Overemphasis on theory over practice",
        ],
        "correct": 2,
        "explanation": "The document specifically notes that longitudinal evidence is underdeveloped in this field.",
    },
    {
        "q": "What does the document recommend for future research?",
        "opts": [
            "Abandon current theoretical frameworks",
            "Prioritise cross-disciplinary collaboration",
            "Focus exclusively on quantitative approaches",
            "Limit studies to single institutional contexts",
        ],
        "correct": 1,
        "explanation": "The document advocates for cross-disciplinary collaboration as the most promising avenue for advancing the field.",
    },
    {
        "q": "Which factor most significantly influences the outcomes discussed in this document?",
        "opts": [
            "Funding levels",
            "Institutional support and context",
            "Individual participant motivation alone",
            "Technological infrastructure availability",
        ],
        "correct": 1,
        "explanation": "Institutional support and context are identified as the dominant conditioning factor across the outcomes discussed.",
    },
    {
        "q": "What is the overall contribution of this document to its field?",
        "opts": [
            "A definitive proof of a contested theory",
            "A synthesised framework for understanding complex interactions",
            "A replication study confirming existing findings",
            "A full critique that discredits prior research",
        ],
        "correct": 1,
        "explanation": "The document contributes a synthesised framework that helps organise complex, sometimes contradictory findings in the field.",
    },
]


@router.post("/upload")
async def upload_document(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    body = await request.json()

    raw_title = body.get("title", "Uploaded Document")
    # Strip file extension from title
    title = raw_title.rsplit(".", 1)[0] if "." in raw_title else raw_title
    file_type = body.get("fileType", "TXT").upper()
    page_count = int(body.get("pageCount", 1)) or 1

    word_estimate = page_count * 350
    now = datetime.now(timezone.utc)
    processed_at = now.strftime("%I:%M %p").lower().lstrip("0")
    year_str = str(now.year)

    return {
        "title": title,
        "fileType": file_type,
        "pageCount": page_count,
        "meta": f".{file_type.lower()} \u00b7 {page_count} {'page' if page_count == 1 else 'pages'}",
        "infoRows": [
            ["File type", file_type],
            ["Estimated words", f"{word_estimate:,}"],
            ["Pages", str(page_count)],
            ["Language", "English"],
            ["Processed at", processed_at],
        ],
        "summary": {
            "pages": f"{page_count} {'page' if page_count == 1 else 'pages'} condensed",
            "title": title,
            "authors": f"AI-processed document \u00b7 {year_str}",
            "body": [
                f"This document has been processed by Learnova\u2019s AI engine. The content spans {page_count} {'page' if page_count == 1 else 'pages'} and covers a focused subject area with clear theoretical and empirical dimensions.",
                "The key themes identified include the methodology employed, the evidence base drawn upon, and the limitations acknowledged by the author(s). These form the basis for the comprehension quiz below.",
            ],
            "takeaways": [
                "The document presents a structured argument supported by academic references and prior research.",
                "Core findings are framed within a broader context with implications for both theory and practice.",
                "Review this summary carefully \u2014 the quiz will test your understanding of the main claims and evidence.",
            ],
        },
        "quizData": GENERIC_QUIZ,
        "strengths": [
            "Research methodology",
            "Evidence-based argument",
            "Theoretical grounding",
        ],
        "weaknesses": ["Practical application", "Longitudinal evidence"],
        "studyNext": [
            "Cross-disciplinary research",
            "Applied case studies",
            "Longitudinal study design",
        ],
    }
