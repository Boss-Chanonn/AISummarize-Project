from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from backend.database.db import history_collection
from backend.middleware.auth_middleware import get_current_user
from backend.services.ollama_service import generate_quiz_analysis
from datetime import datetime, timezone
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


@router.get("/recent")
async def get_recent_history(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    cursor = history_collection.find({"userId": user_id}).sort("uploadedAt", -1).limit(5)
    items = await cursor.to_list(length=5)
    return [_serialize(item) for item in items]


@router.get("")
async def get_all_history(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    cursor = history_collection.find({"userId": user_id}).sort("uploadedAt", -1)
    items = await cursor.to_list(length=1000)
    return [_serialize(item) for item in items]


@router.get("/{history_id}")
async def get_history_item(
    history_id: str,
    current_user: dict = Depends(get_current_user)
):
    user_id = str(current_user["_id"])
    try:
        oid = ObjectId(history_id)
    except Exception:
        return JSONResponse(status_code=400, content={"message": "Invalid history ID"})
    doc = await history_collection.find_one({"_id": oid, "userId": user_id})
    if not doc:
        return JSONResponse(status_code=404, content={"message": "History item not found"})
    return _serialize(doc)


@router.post("/{history_id}/submit-quiz")
async def submit_quiz(
    history_id: str,
    body: dict,
    current_user: dict = Depends(get_current_user)
):
    """Called when user submits quiz answers. Saves score and triggers AI analysis."""
    user_id = str(current_user["_id"])
    try:
        oid = ObjectId(history_id)
    except Exception:
        return JSONResponse(status_code=400, content={"message": "Invalid history ID"})

    doc = await history_collection.find_one({"_id": oid, "userId": user_id})
    if not doc:
        return JSONResponse(status_code=404, content={"message": "History item not found"})

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
    return _serialize(updated)


@router.delete("/{history_id}")
async def delete_history_item(
    history_id: str,
    current_user: dict = Depends(get_current_user)
):
    user_id = str(current_user["_id"])
    try:
        oid = ObjectId(history_id)
    except Exception:
        return JSONResponse(status_code=400, content={"message": "Invalid history ID"})
    result = await history_collection.delete_one({"_id": oid, "userId": user_id})
    if result.deleted_count == 0:
        return JSONResponse(status_code=404, content={"message": "History item not found"})
    return {"message": "Deleted successfully"}

