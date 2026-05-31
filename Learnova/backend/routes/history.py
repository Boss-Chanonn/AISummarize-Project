from fastapi import APIRouter, Depends
from backend.database.db import history_collection
from backend.middleware.auth_middleware import get_current_user
from backend.services.ollama_service import generate_quiz_analysis
from backend.utils.api_errors import message_error
from backend.utils.serializers import serialize_mongo_doc, serialize_mongo_list
from datetime import datetime, timezone
from bson import ObjectId

router = APIRouter()


# ----------------------------- Read Endpoints -----------------------------
@router.get("/recent")
async def get_recent_history(current_user: dict = Depends(get_current_user)):
    """Return the latest five history items for the current user."""
    user_id = str(current_user["_id"])
    cursor = history_collection.find({"userId": user_id}).sort("uploadedAt", -1).limit(5)
    items = await cursor.to_list(length=5)
    return serialize_mongo_list(items, datetime_fields={"uploadedAt", "completedAt"})


@router.get("")
async def get_all_history(current_user: dict = Depends(get_current_user)):
    """Return all history items for the current user, newest first."""
    user_id = str(current_user["_id"])
    cursor = history_collection.find({"userId": user_id}).sort("uploadedAt", -1)
    items = await cursor.to_list(length=1000)
    return serialize_mongo_list(items, datetime_fields={"uploadedAt", "completedAt"})


@router.get("/{history_id}")
async def get_history_item(
    history_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Return one history item by ID for the current user."""
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
@router.post("/{history_id}/submit-quiz")
async def submit_quiz(
    history_id: str,
    body: dict,
    current_user: dict = Depends(get_current_user)
):
    """Save quiz answers, calculate score, and update AI analysis."""
    user_id = str(current_user["_id"])
    try:
        oid = ObjectId(history_id)
    except Exception:
        return message_error(400, "Invalid history ID")

    doc = await history_collection.find_one({"_id": oid, "userId": user_id})
    if not doc:
        return message_error(404, "History item not found")

    user_answers = body.get("answers", [])  # list of chosen option indices
    quiz_questions = doc.get("quizFull", [])
    total = len(quiz_questions)
    correct_count = sum(
        1 for i, ans in enumerate(user_answers)
        if i < total and ans == quiz_questions[i].get("correct")
    )
    score_pct = round((correct_count / total) * 100) if total > 0 else 0

    # AI analysis based on quiz performance
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
        print(f"[history] Quiz analysis failed, using initial analysis: {repr(e)}")

    now = datetime.now(timezone.utc)
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


@router.post("/{history_id}/module-resources")
async def save_module_resources(
    history_id: str,
    body: dict,
    current_user: dict = Depends(get_current_user)
):
    """Persist generated learning module/resources and follow-up progress."""
    user_id = str(current_user["_id"])
    try:
        oid = ObjectId(history_id)
    except Exception:
        return message_error(400, "Invalid history ID")

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


@router.delete("/{history_id}")
async def delete_history_item(
    history_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete one history item owned by the current user."""
    user_id = str(current_user["_id"])
    try:
        oid = ObjectId(history_id)
    except Exception:
        return message_error(400, "Invalid history ID")
    result = await history_collection.delete_one({"_id": oid, "userId": user_id})
    if result.deleted_count == 0:
        return message_error(404, "History item not found")
    return {"message": "Deleted successfully"}
