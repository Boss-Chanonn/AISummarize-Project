"""
routes/history.py — Document History CRUD
==========================================
Provides read, write, and delete endpoints for the per-user document history
stored in the MongoDB `history` collection. History items are created during
upload (routes/upload.py) and updated when quizzes are submitted.

Cross-reference: routes/upload.py (creates history), routes/content.py (reads results),
                 routes/ai.py → ollama_service.generate_quiz_analysis (AI quiz feedback).
"""

from fastapi import APIRouter, Depends
from backend.database.db import history_collection
from backend.middleware.auth_middleware import get_current_user
from backend.services.ollama_service import generate_quiz_analysis
from backend.utils.api_errors import message_error
from backend.utils.sanitization import sanitize_answer_indices
from backend.utils.serializers import serialize_mongo_doc, serialize_mongo_list
from datetime import datetime, timezone
from bson import ObjectId

router = APIRouter()


# ----------------------------- Read Endpoints -----------------------------

# GET /recent — fetch the latest 5 history items
@router.get("/recent")
async def get_recent_history(current_user: dict = Depends(get_current_user)):
    """GET /recent — return the latest five history items for the current user (newest first)."""
    user_id = str(current_user["_id"])
    cursor = history_collection.find({"userId": user_id}).sort("uploadedAt", -1).limit(5)
    items = await cursor.to_list(length=5)
    return serialize_mongo_list(items, datetime_fields={"uploadedAt", "completedAt"})


# GET / — fetch all history items
@router.get("")
async def get_all_history(current_user: dict = Depends(get_current_user)):
    """GET / — return all history items for the current user, newest first (up to 1000)."""
    user_id = str(current_user["_id"])
    cursor = history_collection.find({"userId": user_id}).sort("uploadedAt", -1)
    items = await cursor.to_list(length=1000)
    return serialize_mongo_list(items, datetime_fields={"uploadedAt", "completedAt"})


# GET /{history_id} — fetch a single history item by ID
@router.get("/{history_id}")
async def get_history_item(
    history_id: str,
    current_user: dict = Depends(get_current_user)
):
    """GET /{history_id} — return one history item by ID, scoped to the current user."""
    user_id = str(current_user["_id"])
    try:
        oid = ObjectId(history_id)
    except Exception:
        return message_error(400, "Invalid history ID")
    doc = await history_collection.find_one({"_id": oid, "userId": user_id})
    if not doc:
        return message_error(404, "History item not found")
    return serialize_mongo_doc(doc, datetime_fields={"uploadedAt", "completedAt"})


# ----------------------------- Write Endpoints -----------------------------

# POST /{history_id}/submit-quiz — save user's quiz answers and calculate score
@router.post("/{history_id}/submit-quiz")
async def submit_quiz(
    history_id: str,
    body: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    POST /{history_id}/submit-quiz — save quiz answers, calculate score,
    and trigger AI-powered performance analysis.

    Request body expects: { "answers": [0, 1, 2, ...] }   (list of chosen option indices)
    The handler compares each answer to the stored correct index,
    computes a percentage score, and calls generate_quiz_analysis for
    strengths/weaknesses/recommendations.

    Cross-reference: ollama_service.generate_quiz_analysis produces the AI feedback.
    """
    user_id = str(current_user["_id"])
    try:
        oid = ObjectId(history_id)
    except Exception:
        return message_error(400, "Invalid history ID")

    doc = await history_collection.find_one({"_id": oid, "userId": user_id})
    if not doc:
        return message_error(404, "History item not found")

    user_answers = sanitize_answer_indices(body.get("answers", []))
    quiz_questions = doc.get("quizFull", [])
    total = len(quiz_questions)
    correct_count = sum(
        1 for i, ans in enumerate(user_answers)
        if i < total and ans == quiz_questions[i].get("correct")
    )
    score_pct = round((correct_count / total) * 100) if total > 0 else 0

    # ── AI analysis based on quiz performance (best-effort) ──
    ai_analysis = doc.get("analysis", {})
    try:
        ai_result = await generate_quiz_analysis(
            title=doc.get("title", "document"),
            quiz_questions=quiz_questions,
            user_answers=user_answers,
        )
        ai_analysis = {
            "strengths": ai_result["strengths"],
            "weaknesses": ai_result["weaknesses"],
            "recommendations": ai_result["recommendations"],
            "studyNext": doc.get("analysis", {}).get("studyNext", []),
        }
        print(f"[history] Quiz analysis generated for: {doc.get('title')}")
    except Exception as e:
        # If AI analysis fails, keep whatever analysis was already stored
        print(f"[history] Quiz analysis failed, using initial analysis: {repr(e)}")

    now = datetime.now(timezone.utc)
    # ── Persist quiz results and mark as done ──
    await history_collection.update_one(
        {"_id": oid},
        {"$set": {
            "done": True,
            "score": score_pct,
            "correct": correct_count,
            "total": total,
            "userAnswers": user_answers,
            "analysis": ai_analysis,
            "completedAt": now,
        }}
    )

    updated = await history_collection.find_one({"_id": oid})
    return serialize_mongo_doc(updated, datetime_fields={"uploadedAt", "completedAt"})


# POST /{history_id}/module-resources — persist generated learning modules
@router.post("/{history_id}/module-resources")
async def save_module_resources(
    history_id: str,
    body: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    POST /{history_id}/module-resources — persist generated learning modules,
    resources, follow-up quizzes, and progress tracking data.

    Only writes fields from a whitelist (learningModule, moduleResources,
    followUpQuiz, progress) to prevent arbitrary data injection.
    """
    user_id = str(current_user["_id"])
    try:
        oid = ObjectId(history_id)
    except Exception:
        return message_error(400, "Invalid history ID")

    # Whitelist of allowed fields — prevents writing arbitrary data
    allowed_fields = {
        "learningModule",
        "moduleResources",
        "followUpQuiz",
        "progress",
    }
    update_fields = {key: body[key] for key in allowed_fields if key in body}
    if not update_fields:
        return message_error(400, "No module data provided")

    result = await history_collection.update_one(
        {"_id": oid, "userId": user_id},
        {"$set": update_fields}
    )
    if result.matched_count == 0:
        return message_error(404, "History item not found")

    updated = await history_collection.find_one({"_id": oid})
    return serialize_mongo_doc(updated, datetime_fields={"uploadedAt", "completedAt"})


# DELETE /{history_id} — remove a history item
@router.delete("/{history_id}")
async def delete_history_item(
    history_id: str,
    current_user: dict = Depends(get_current_user)
):
    """DELETE /{history_id} — delete one history item owned by the current user."""
    user_id = str(current_user["_id"])
    try:
        oid = ObjectId(history_id)
    except Exception:
        return message_error(400, "Invalid history ID")
    result = await history_collection.delete_one({"_id": oid, "userId": user_id})
    if result.deleted_count == 0:
        return message_error(404, "History item not found")
    return {"message": "Deleted successfully"}
