from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from backend.database.db import history_collection
from backend.middleware.auth_middleware import get_current_user
from datetime import datetime, timezone
from bson import ObjectId
import math

router = APIRouter()


def serialize_history(doc: dict) -> dict:
    """Convert a MongoDB history document to a JSON-safe dict."""
    doc["id"] = doc.pop("seqId", 0)
    doc.pop("_id", None)
    doc.pop("userId", None)
    if isinstance(doc.get("uploadedAt"), datetime):
        doc["uploadedAt"] = doc["uploadedAt"].isoformat()
    return doc


@router.get("/recent")
async def get_recent_history(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    cursor = history_collection.find(
        {"userId": user_id}
    ).sort("uploadedAt", -1).limit(5)
    items = await cursor.to_list(length=5)
    return [serialize_history(item) for item in items]


@router.get("")
async def get_all_history(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    cursor = history_collection.find(
        {"userId": user_id}
    ).sort("uploadedAt", -1)
    items = await cursor.to_list(length=1000)
    return [serialize_history(item) for item in items]


@router.post("/save", status_code=201)
async def save_history(
    body: dict,
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])

    # Get next sequential ID for this user
    last = await history_collection.find_one(
        {"userId": user_id}, sort=[("seqId", -1)]
    )
    next_id = (last["seqId"] + 1) if last and "seqId" in last else 1

    new_item = {
        "userId": user_id,
        "seqId": next_id,
        "title": body.get("title", "Untitled"),
        "meta": body.get("meta", ""),
        "fileType": body.get("fileType", "TXT"),
        "pageCount": body.get("pageCount", 1),
        "score": body.get("score", 0),
        "correct": body.get("correct", 0),
        "total": body.get("total", 8),
        "done": True,
        "uploadedAt": datetime.now(timezone.utc),
        "summary": body.get("summary", {}),
        "strengths": body.get("strengths", []),
        "weaknesses": body.get("weaknesses", []),
        "studyNext": body.get("studyNext", []),
        "questions": body.get("questions", []),
        "quizFull": body.get("quizFull", []),
    }

    await history_collection.insert_one(new_item)
    return serialize_history(new_item)
