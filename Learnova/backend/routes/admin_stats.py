from fastapi import APIRouter, Depends
from backend.middleware.auth_middleware import get_admin_user
from backend.database.db import users_collection, history_collection
from datetime import datetime, timedelta

router = APIRouter()


# ----------------------------- Summary Cards Endpoint -----------------------------
@router.get("/stats")
async def get_stats(current_user: dict = Depends(get_admin_user)):
    """Return summary metrics used by admin stats overview cards."""
    total_users = await users_collection.count_documents({})
    pro_users   = await users_collection.count_documents({"tier": "pro"})

    # Active users = distinct users who uploaded in the last 30 days
    thirty_ago = datetime.utcnow() - timedelta(days=30)
    active_ids  = await history_collection.distinct(
        "userId", {"uploadedAt": {"$gte": thirty_ago}}
    )
    active_users = len(active_ids)

    # Uploads = total history items
    total_uploads = await history_collection.count_documents({})

    # Quizzes completed = history items with done=True
    total_quizzes = await history_collection.count_documents({"done": True})

    # Average score — score field is already a percentage (0-100)
    pipeline = [
        {"$match": {"done": True, "score": {"$type": "number"}}},
        {"$group": {"_id": None, "avg": {"$avg": "$score"}}},
    ]
    avg_result = await history_collection.aggregate(pipeline).to_list(1)
    avg_score  = round(avg_result[0]["avg"] if avg_result else 0, 1)

    # New users this week
    week_ago      = datetime.utcnow() - timedelta(days=7)
    new_this_week = await users_collection.count_documents(
        {"createdAt": {"$gte": week_ago}}
    )

    return {
        "total_users"   : total_users,
        "active_users"  : active_users,
        "pro_users"     : pro_users,
        "total_uploads" : total_uploads,
        "total_quizzes" : total_quizzes,
        "avg_score"     : avg_score,
        "new_this_week" : new_this_week,
        "active_pct"    : round(active_users / total_users * 100 if total_users else 0, 1),
        "pro_pct"       : round(pro_users    / total_users * 100 if total_users else 0, 1),
    }


# ----------------------------- Chart Data Endpoints -----------------------------
@router.get("/stats/user-growth")
async def get_user_growth(current_user: dict = Depends(get_admin_user)):
    """Return daily new-user counts for the last 30 days."""
    result = []
    base = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    for i in range(29, -1, -1):
        day_start = base - timedelta(days=i)
        day_end   = day_start + timedelta(days=1)
        count = await users_collection.count_documents({
            "createdAt": {"$gte": day_start, "$lt": day_end}
        })
        result.append({"date": day_start.strftime("%d %b"), "count": count})
    return {"data": result}


@router.get("/stats/upload-activity")
async def get_upload_activity(current_user: dict = Depends(get_admin_user)):
    """Return daily upload counts for the last 30 days."""
    result = []
    base = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    for i in range(29, -1, -1):
        day_start = base - timedelta(days=i)
        day_end   = day_start + timedelta(days=1)
        count = await history_collection.count_documents({
            "uploadedAt": {"$gte": day_start, "$lt": day_end}
        })
        result.append({"date": day_start.strftime("%d %b"), "count": count})
    return {"data": result}
