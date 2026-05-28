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
    return {
        "_id": doc["_id"],
        "title": doc.get("title"),
        "fileType": doc.get("fileType"),
        "score": doc.get("score"),
        "correct": doc.get("correct"),
        "total": doc.get("total"),
        "userAnswers": doc.get("userAnswers", []),
        "quizFull": doc.get("quizFull", []),
        "analysis": doc.get("analysis", {}),
        "strengths": doc.get("analysis", {}).get("strengths", []),
        "weaknesses": doc.get("analysis", {}).get("weaknesses", []),
        "studyNext": doc.get("analysis", {}).get("studyNext", []),
        "summary": doc.get("summary", {}),
        "modules": doc.get("modules", []),
        "learningModule": doc.get("learningModule"),
        "moduleResources": doc.get("moduleResources"),
        "followUpQuiz": doc.get("followUpQuiz"),
        "progress": doc.get("progress"),
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
