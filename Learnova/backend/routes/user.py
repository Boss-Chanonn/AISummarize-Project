from fastapi import APIRouter, Depends
from backend.database.db import history_collection
from backend.middleware.auth_middleware import get_current_user
from datetime import datetime, timedelta, timezone

router = APIRouter()


@router.get("/profile")
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # All history for this user
    cursor = history_collection.find({"userId": user_id})
    history = await cursor.to_list(length=1000)

    total_docs = len(history)
    completed = [h for h in history if h.get("done")]
    quiz_count = len(completed)
    avg_score = (
        round(sum(h.get("score", 0) for h in completed) / quiz_count)
        if quiz_count > 0
        else 0
    )

    # Sub-labels
    new_this_week = sum(
        1 for h in history
        if h.get("uploadedAt") and h["uploadedAt"] >= week_ago
    )
    quizzes_this_month = sum(
        1 for h in completed
        if h.get("uploadedAt") and h["uploadedAt"] >= month_ago
    )

    stat_subs = [
        f"+{new_this_week} this week" if new_this_week > 0 else "No new uploads this week",
        f"Based on {quiz_count} quiz{'zes' if quiz_count > 1 else ''}" if quiz_count > 0 else "No quizzes yet",
        f"{quizzes_this_month} this month" if quizzes_this_month > 0 else "None this month",
    ]

    return {
        "name": current_user["name"],
        "email": current_user["email"],
        "documentsStudied": total_docs,
        "averageScore": avg_score,
        "quizzesCompleted": quiz_count,
        "statSubs": stat_subs,
    }
