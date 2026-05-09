from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from backend.database.db import history_collection
from backend.middleware.auth_middleware import get_current_user
from datetime import datetime
from bson import ObjectId

router = APIRouter()


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["_id"] = str(doc["_id"])
    if isinstance(doc.get("uploadedAt"), datetime):
        doc["uploadedAt"] = doc["uploadedAt"].isoformat()
    if isinstance(doc.get("completedAt"), datetime):
        doc["completedAt"] = doc["completedAt"].isoformat()
    return doc


@router.get("/results")
async def get_results(
    id: str = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """Get quiz results for a history item by MongoDB _id."""
    user_id = str(current_user["_id"])

    if id:
        try:
            oid = ObjectId(id)
        except Exception:
            return JSONResponse(status_code=400, content={"message": "Invalid ID"})
        item = await history_collection.find_one({"_id": oid, "userId": user_id})
    else:
        item = await history_collection.find_one(
            {"userId": user_id, "done": True}, sort=[("completedAt", -1)]
        )

    if not item:
        return JSONResponse(status_code=404, content={"message": "Result not found. Complete a quiz first."})

    doc = _serialize(item)
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
        "summary": doc.get("summary", {}),
        "modules": doc.get("modules", []),
        "uploadedAt": doc.get("uploadedAt"),
        "completedAt": doc.get("completedAt"),
    }


@router.get("/modules")
async def get_modules(
    historyId: str = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """Get learning modules for a history item by MongoDB _id."""
    user_id = str(current_user["_id"])

    if historyId:
        try:
            oid = ObjectId(historyId)
        except Exception:
            return JSONResponse(status_code=400, content={"message": "Invalid ID"})
        item = await history_collection.find_one({"_id": oid, "userId": user_id})
    else:
        item = await history_collection.find_one(
            {"userId": user_id}, sort=[("uploadedAt", -1)]
        )

    if not item:
        return JSONResponse(status_code=404, content={"message": "No modules found."})

    return {
        "_id": str(item["_id"]),
        "title": item.get("title"),
        "modules": item.get("modules", []),
        "studyNext": item.get("analysis", {}).get("studyNext", []),
    }

