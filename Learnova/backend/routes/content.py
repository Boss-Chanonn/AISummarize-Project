from fastapi import APIRouter, Depends, Query
from backend.database.db import history_collection
from backend.middleware.auth_middleware import get_current_user
from backend.utils.api_errors import message_error
from backend.utils.serializers import serialize_mongo_doc
from bson import ObjectId

router = APIRouter()


# ----------------------------- Results Endpoints -----------------------------
@router.get("/results")
async def get_results(
    id: str = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """Get quiz results for one history item or the latest completed quiz."""
    user_id = str(current_user["_id"])

    if id:
        try:
            oid = ObjectId(id)
        except Exception:
            return message_error(400, "Invalid ID")
        item = await history_collection.find_one({"_id": oid, "userId": user_id})
    else:
        item = await history_collection.find_one(
            {"userId": user_id, "done": True}, sort=[("completedAt", -1)]
        )

    if not item:
        return message_error(404, "Result not found. Complete a quiz first.")

    doc = serialize_mongo_doc(item, datetime_fields={"uploadedAt", "completedAt"})
    quiz_full = doc.get("quizFull", [])
    user_answers = doc.get("userAnswers", [])
    reviewed_questions = []
    analysis_reviewed_questions = []
    weak_topics = []

    for index, question in enumerate(quiz_full):
        chosen = user_answers[index] if index < len(user_answers) else -1
        options = question.get("opts", [])
        correct_index = question.get("correct", 0)
        is_correct = chosen == correct_index
        topic = question.get("topic") or "General comprehension"
        if not is_correct and topic not in weak_topics:
            weak_topics.append(topic)
        reviewed_questions.append({
            "q": question.get("q", ""),
            "topic": topic,
            "correct": is_correct,
            "your": options[chosen] if isinstance(chosen, int) and 0 <= chosen < len(options) else "Skipped",
            "answer": None if is_correct else (options[correct_index] if 0 <= correct_index < len(options) else ""),
            "explanation": question.get("explanation", ""),
        })
        analysis_reviewed_questions.append({
            "question": question.get("q") or "Review this quiz question from the document.",
            "topic": topic,
            "user_answer": options[chosen] if isinstance(chosen, int) and 0 <= chosen < len(options) else "Skipped",
            "correct_answer": options[correct_index] if 0 <= correct_index < len(options) else "Review the correct option.",
            "is_correct": is_correct,
            "explanation": question.get("explanation") or "Review the document summary to understand why this answer is correct.",
        })

    analysis = doc.get("analysis", {}) or {}
    topic_tags = doc.get("summary", {}).get("topics", [])
    weaknesses = analysis.get("weaknesses") or weak_topics or topic_tags[:2]
    study_next = analysis.get("studyNext") or analysis.get("recommendations") or []
    if len(study_next) < 2:
        study_next = [
            *study_next,
            "Review the missed quiz explanations.",
            "Retest the weak topics after studying the module.",
        ][:2]

    return {
        "_id": doc["_id"],
        "title": doc.get("title"),
        "fileType": doc.get("fileType"),
        "score": doc.get("score"),
        "correct": doc.get("correct"),
        "total": doc.get("total"),
        "userAnswers": doc.get("userAnswers", []),
        "quizFull": quiz_full,
        "questions": reviewed_questions,
        "analysis": {
            **analysis,
            "weak_topics": analysis.get("weak_topics") or weak_topics or weaknesses,
            "study_recommendations": study_next,
            "reviewed_questions": analysis.get("reviewed_questions") or analysis_reviewed_questions,
            "score_percent": doc.get("score") or 0,
            "correct_count": doc.get("correct") or 0,
            "total_questions": doc.get("total") or len(quiz_full),
        },
        "summary": doc.get("summary", {}),
        "topicTags": topic_tags,
        "strengths": analysis.get("strengths", []),
        "weaknesses": weaknesses,
        "studyNext": study_next,
        "learningModule": doc.get("learningModule"),
        "moduleResources": doc.get("moduleResources"),
        "followUpQuiz": doc.get("followUpQuiz"),
        "progress": doc.get("progress"),
        "modules": doc.get("modules", []),
        "uploadedAt": doc.get("uploadedAt"),
        "completedAt": doc.get("completedAt"),
    }


# ----------------------------- Modules Endpoints -----------------------------
@router.get("/modules")
async def get_modules(
    historyId: str = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """Get learning modules for one history item or the latest upload."""
    user_id = str(current_user["_id"])

    if historyId:
        try:
            oid = ObjectId(historyId)
        except Exception:
            return message_error(400, "Invalid ID")
        item = await history_collection.find_one({"_id": oid, "userId": user_id})
    else:
        item = await history_collection.find_one(
            {"userId": user_id}, sort=[("uploadedAt", -1)]
        )

    if not item:
        return message_error(404, "No modules found.")

    doc = serialize_mongo_doc(item)
    return {
        "_id": doc["_id"],
        "title": doc.get("title"),
        "modules": doc.get("modules", []),
        "studyNext": doc.get("analysis", {}).get("studyNext", []),
    }
