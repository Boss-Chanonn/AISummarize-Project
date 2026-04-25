import json
import os
import time
from typing import Any, Dict

import httpx

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:latest")
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "180"))
OLLAMA_ENABLED = os.getenv("OLLAMA_ENABLED", "true").lower() == "true"


def _build_prompt(title: str, file_type: str, text_content: str) -> str:
    snippet = text_content[:6000].strip() if text_content else ""
    content_section = (
        f'Document excerpt:\n"""\n{snippet}\n"""'
        if snippet
        else f'Document title: "{title}" (type: {file_type})'
    )
    return f"""You are an expert academic summariser for Learnova, an AI learning platform.
Your task is to deeply analyse the document provided and return a comprehensive JSON response.

{content_section}

Return ONLY valid JSON with this exact structure (no markdown, no extra text, no code blocks):
{{
  "summary": {{
    "body": [
      "paragraph 1: Introduce the document topic, its main purpose, and the central argument or research question. Write 4-6 sentences with specific details from the document.",
      "paragraph 2: Explain the methodology, approach, or framework used. Include specific examples or evidence mentioned in the document. Write 4-6 sentences.",
      "paragraph 3: Describe the key findings, conclusions, or outcomes. Explain their significance and real-world implications. Write 4-6 sentences.",
      "paragraph 4: Discuss limitations, gaps, or areas for future research mentioned in the document. Write 3-5 sentences."
    ],
    "takeaways": [
      "Specific key point 1 directly from document",
      "Specific key point 2 directly from document",
      "Specific key point 3 directly from document",
      "Specific key point 4 directly from document",
      "Specific key point 5 directly from document"
    ]
  }},
  "quiz": [
    {{"q": "question text based on document content", "opts": ["option A", "option B", "option C", "option D"], "correct": 0, "explanation": "detailed explanation why this answer is correct"}},
    {{"q": "...", "opts": ["...", "...", "...", "..."], "correct": 1, "explanation": "..."}},
    {{"q": "...", "opts": ["...", "...", "...", "..."], "correct": 2, "explanation": "..."}},
    {{"q": "...", "opts": ["...", "...", "...", "..."], "correct": 3, "explanation": "..."}},
    {{"q": "...", "opts": ["...", "...", "...", "..."], "correct": 0, "explanation": "..."}},
    {{"q": "...", "opts": ["...", "...", "...", "..."], "correct": 1, "explanation": "..."}},
    {{"q": "...", "opts": ["...", "...", "...", "..."], "correct": 2, "explanation": "..."}},
    {{"q": "...", "opts": ["...", "...", "...", "..."], "correct": 3, "explanation": "..."}}
  ],
  "analysis": {{
    "strengths": [
      "specific strength topic 1",
      "specific strength topic 2",
      "specific strength topic 3"
    ],
    "weaknesses": [
      "specific weakness topic 1",
      "specific weakness topic 2"
    ],
    "recommendations": [
      "specific study recommendation 1",
      "specific study recommendation 2",
      "specific study recommendation 3"
    ],
    "studyNext": [
      "specific topic to study next 1",
      "specific topic to study next 2",
      "specific topic to study next 3"
    ]
  }},
  "modules": [
    {{"title": "resource title 1", "type": "youtube", "query": "specific youtube search query", "description": "why this resource helps"}},
    {{"title": "resource title 2", "type": "youtube", "query": "specific youtube search query", "description": "why this resource helps"}},
    {{"title": "resource title 3", "type": "google", "query": "specific google search query", "description": "why this resource helps"}},
    {{"title": "resource title 4", "type": "google", "query": "specific google search query", "description": "why this resource helps"}},
    {{"title": "resource title 5", "type": "youtube", "query": "specific youtube search query", "description": "why this resource helps"}}
  ]
}}

IMPORTANT REQUIREMENTS:
- Write ALL content based on the ACTUAL document text provided above
- Each summary paragraph must be 4-6 sentences long
- Each paragraph must contain SPECIFIC details, facts, or arguments from the document
- Do NOT write generic filler text
- quiz must have EXACTLY 8 questions
- Each question must have EXACTLY 4 options
- correct is 0-based index (0, 1, 2, or 3)
- modules must have EXACTLY 5 items
- No markdown, no code blocks, only raw JSON""".strip()


def _extract_json(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start:end + 1])
    raise ValueError("No JSON object found in Ollama response")


def _validate_full_payload(payload: Dict[str, Any], title: str) -> Dict[str, Any]:
    summary = payload.get("summary", {})
    body = summary.get("body", []) if isinstance(summary, dict) else []
    takeaways = summary.get("takeaways", []) if isinstance(summary, dict) else []

    body = [str(x).strip() for x in body if str(x).strip()]

    def fix_encoding(text: str) -> str:
        try:
            return text.encode("latin-1").decode("utf-8")
        except (UnicodeDecodeError, UnicodeEncodeError):
            return text

    body = [fix_encoding(x) for x in body]
    takeaways = [fix_encoding(x) for x in takeaways]
    while len(body) < 4:
        body.append(
            f"This document titled '{title}' presents "
            f"structured academic arguments supported "
            f"by evidence and analysis. The content "
            f"covers key theoretical and practical "
            f"dimensions relevant to the field."
        )
    body = body[:4]

    takeaways = [str(x).strip() for x in takeaways if str(x).strip()]
    while len(takeaways) < 5:
        takeaways.append(
            "Review the key concepts and connect "
            "them to the quiz questions."
        )
    takeaways = takeaways[:5]

    quiz_raw = payload.get("quiz", [])
    quiz = []
    if isinstance(quiz_raw, list):
        for item in quiz_raw:
            if not isinstance(item, dict):
                continue
            q = str(item.get("q", "")).strip()
            opts = item.get("opts", [])
            correct = item.get("correct", 0)
            explanation = str(item.get("explanation", "")).strip()
            if not q or not isinstance(opts, list) or len(opts) < 2:
                continue
            opts = [str(o).strip() for o in opts]
            while len(opts) < 4:
                opts.append("None of the above")
            opts = opts[:4]
            try:
                correct = int(correct) % 4
            except Exception:
                correct = 0
            quiz.append({"q": q, "opts": opts, "correct": correct, "explanation": explanation})

    FALLBACK_QUESTIONS = [
        {"q": "What is the primary focus of this document?", "opts": ["Empirical measurement", "Theoretical critique", "Systematic synthesis", "Policy evaluation"], "correct": 2, "explanation": "The document takes a synthesis approach."},
        {"q": "Which methodology is primarily employed?", "opts": ["Randomised trial", "Ethnographic fieldwork", "Literature review", "Longitudinal survey"], "correct": 2, "explanation": "A literature review and analytical framework are central."},
        {"q": "What type of evidence is most heavily used?", "opts": ["Anecdotal reports", "Peer-reviewed studies", "Government statistics", "Industry benchmarks"], "correct": 1, "explanation": "Peer-reviewed studies form the backbone of evidence."},
        {"q": "Who is the target audience?", "opts": ["General public", "Academic researchers", "Policy makers only", "Undergrad students"], "correct": 1, "explanation": "Technical language indicates researchers and practitioners."},
        {"q": "What gap is identified in existing work?", "opts": ["Lack of data", "Under-representation", "Insufficient longitudinal research", "Overemphasis on theory"], "correct": 2, "explanation": "Longitudinal evidence is underdeveloped in this field."},
        {"q": "What does the document recommend?", "opts": ["Abandon frameworks", "Cross-disciplinary collaboration", "Quantitative only", "Single institution studies"], "correct": 1, "explanation": "Cross-disciplinary collaboration is most promising."},
        {"q": "Which factor most influences outcomes?", "opts": ["Funding levels", "Institutional support", "Individual motivation", "Technology availability"], "correct": 1, "explanation": "Institutional support is the dominant conditioning factor."},
        {"q": "What is the overall contribution?", "opts": ["Definitive theory proof", "Synthesised framework", "Replication study", "Full critique"], "correct": 1, "explanation": "A synthesised framework organises complex findings."},
    ]
    while len(quiz) < 8:
        quiz.append(FALLBACK_QUESTIONS[len(quiz) % 8])
    quiz = quiz[:8]

    analysis = payload.get("analysis", {})
    if not isinstance(analysis, dict):
        analysis = {}

    strengths = [str(x).strip() for x in analysis.get("strengths", []) if str(x).strip()][:3]
    if not strengths:
        strengths = ["Core understanding", "Concept linkage", "Evidence awareness"]
    weaknesses = [str(x).strip() for x in analysis.get("weaknesses", []) if str(x).strip()][:2]
    if not weaknesses:
        weaknesses = ["Application depth", "Long-term retention"]
    recommendations = [str(x).strip() for x in analysis.get("recommendations", []) if str(x).strip()][:3]
    if not recommendations:
        recommendations = ["Review core concepts regularly", "Practice applied questions", "Revisit evidence summaries"]
    study_next = [str(x).strip() for x in analysis.get("studyNext", []) if str(x).strip()][:3]
    if not study_next:
        study_next = ["Related academic literature", "Applied case studies", "Cross-disciplinary research"]

    modules_raw = payload.get("modules", [])
    modules = []
    if isinstance(modules_raw, list):
        for m in modules_raw:
            if not isinstance(m, dict):
                continue
            t = str(m.get("title", "")).strip()
            mtype = str(m.get("type", "google")).strip().lower()
            query = str(m.get("query", t)).strip()
            desc = str(m.get("description", "")).strip()
            if not t or not query:
                continue
            encoded = query.replace(" ", "+")
            url = (
                f"https://www.youtube.com/results?search_query={encoded}"
                if mtype == "youtube"
                else f"https://www.google.com/search?q={encoded}"
            )
            modules.append({"title": t, "type": mtype, "url": url, "description": desc})

    while len(modules) < 5:
        topic = study_next[len(modules) % len(study_next)]
        encoded = topic.replace(" ", "+")
        mtype = "youtube" if len(modules) % 2 == 0 else "google"
        url = (
            f"https://www.youtube.com/results?search_query={encoded}"
            if mtype == "youtube"
            else f"https://www.google.com/search?q={encoded}"
        )
        modules.append({"title": topic, "type": mtype, "url": url, "description": f"Explore more about {topic}"})
    modules = modules[:5]

    return {
        "summary": {"body": body, "takeaways": takeaways},
        "quiz": quiz,
        "analysis": {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "recommendations": recommendations,
            "studyNext": study_next,
        },
        "modules": modules,
    }


async def generate_learning_package(
    title: str,
    file_type: str,
    text_content: str = "",
) -> Dict[str, Any]:
    if not OLLAMA_ENABLED:
        raise RuntimeError("Ollama is disabled by configuration")

    prompt = _build_prompt(title=title, file_type=file_type, text_content=text_content)
    print(f"[ollama] Generating for: {title} ({file_type}) model={OLLAMA_MODEL}")
    t0 = time.time()

    async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT_SECONDS) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL.rstrip('/')}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "format": "json", "options": {"temperature": 0.3}},
        )
        response.raise_for_status()
        data = response.json()

    elapsed = time.time() - t0
    raw_output = data.get("response", "")
    print(f"[ollama] Done in {elapsed:.1f}s — raw length={len(raw_output)} chars")

    parsed = _extract_json(raw_output)
    return _validate_full_payload(parsed, title)


async def generate_quiz_analysis(
    title: str,
    quiz_questions: list,
    user_answers: list,
) -> Dict[str, Any]:
    """Generate personalized strengths/weaknesses/recommendations after quiz submission."""
    if not OLLAMA_ENABLED:
        raise RuntimeError("Ollama is disabled")

    wrong_topics = []
    correct_topics = []
    for i, (q, ans) in enumerate(zip(quiz_questions, user_answers)):
        question_text = q.get("q", f"Question {i+1}")
        if ans == q.get("correct"):
            correct_topics.append(question_text)
        else:
            wrong_topics.append(question_text)

    wrong_str = "\n".join(f"- {t}" for t in wrong_topics) if wrong_topics else "- None (all correct!)"
    correct_str = "\n".join(f"- {t}" for t in correct_topics) if correct_topics else "- None"

    prompt = f"""You are an educational coach. A student just completed a quiz about "{title}".

Questions answered CORRECTLY:
{correct_str}

Questions answered INCORRECTLY:
{wrong_str}

Return ONLY valid JSON:
{{
  "strengths": ["area of strength 1 based on correct answers", "area 2", "area 3"],
  "weaknesses": ["area needing improvement based on wrong answers", "area 2"],
  "recommendations": ["specific study recommendation 1", "recommendation 2", "recommendation 3"]
}}

Be specific to the actual questions listed above. No markdown, only JSON.""".strip()

    print(f"[ollama] Generating quiz analysis for: {title}")
    t0 = time.time()

    async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT_SECONDS) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL.rstrip('/')}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "format": "json", "options": {"temperature": 0.3}},
        )
        response.raise_for_status()
        data = response.json()

    elapsed = time.time() - t0
    raw_output = data.get("response", "")
    print(f"[ollama] Quiz analysis done in {elapsed:.1f}s")

    try:
        parsed = _extract_json(raw_output)
    except Exception:
        parsed = {}

    strengths = [str(x).strip() for x in parsed.get("strengths", []) if str(x).strip()][:3]
    if not strengths:
        strengths = ["Core understanding", "Concept recall", "Analytical thinking"]
    weaknesses = [str(x).strip() for x in parsed.get("weaknesses", []) if str(x).strip()][:2]
    if not weaknesses:
        weaknesses = ["Application depth", "Detail retention"]
    recommendations = [str(x).strip() for x in parsed.get("recommendations", []) if str(x).strip()][:3]
    if not recommendations:
        recommendations = ["Review the summary again", "Re-read the sections you missed", "Practice with similar materials"]

    return {"strengths": strengths, "weaknesses": weaknesses, "recommendations": recommendations}

