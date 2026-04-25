from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from backend.database.db import users_collection, history_collection
from backend.middleware.auth_middleware import get_admin_user
from datetime import datetime, timezone, timedelta
from bson import ObjectId

router = APIRouter()


def _serialize_user(u: dict) -> dict:
    u = dict(u)
    u["_id"] = str(u["_id"])
    u.pop("password", None)
    if isinstance(u.get("createdAt"), datetime):
        u["createdAt"] = u["createdAt"].isoformat()
    return u


@router.get("/dashboard")
async def admin_dashboard(current_user: dict = Depends(get_admin_user)):
    total_users = await users_collection.count_documents({})
    total_docs = await history_collection.count_documents({})
    completed = await history_collection.count_documents({"done": True})
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    uploads_today = await history_collection.count_documents({"uploadedAt": {"$gte": today_start}})
    week_ago = now - timedelta(days=7)
    uploads_week = await history_collection.count_documents({"uploadedAt": {"$gte": week_ago}})
    return {
        "totalUsers": total_users,
        "totalDocuments": total_docs,
        "quizzesCompleted": completed,
        "uploadsToday": uploads_today,
        "uploadsThisWeek": uploads_week,
    }


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_admin_user)
):
    skip = (page - 1) * limit
    cursor = users_collection.find({}).sort("createdAt", -1).skip(skip).limit(limit)
    users = await cursor.to_list(length=limit)
    total = await users_collection.count_documents({})
    return {"users": [_serialize_user(u) for u in users], "total": total, "page": page, "limit": limit}


@router.get("/users/{user_id}")
async def get_user(user_id: str, current_user: dict = Depends(get_admin_user)):
    try:
        oid = ObjectId(user_id)
    except Exception:
        return JSONResponse(status_code=400, content={"message": "Invalid user ID"})
    user = await users_collection.find_one({"_id": oid})
    if not user:
        return JSONResponse(status_code=404, content={"message": "User not found"})
    return _serialize_user(user)


@router.put("/users/{user_id}/tier")
async def update_user_tier(
    user_id: str,
    body: dict,
    current_user: dict = Depends(get_admin_user)
):
    tier = body.get("tier")
    if tier not in ("free", "pro"):
        return JSONResponse(status_code=400, content={"message": "Tier must be 'free' or 'pro'"})
    try:
        oid = ObjectId(user_id)
    except Exception:
        return JSONResponse(status_code=400, content={"message": "Invalid user ID"})
    await users_collection.update_one({"_id": oid}, {"$set": {"tier": tier}})
    return {"message": f"User tier updated to {tier}"}


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    body: dict,
    current_user: dict = Depends(get_admin_user)
):
    role = body.get("role")
    if role not in ("user", "admin", "system_admin"):
        return JSONResponse(status_code=400, content={"message": "Invalid role"})
    try:
        oid = ObjectId(user_id)
    except Exception:
        return JSONResponse(status_code=400, content={"message": "Invalid user ID"})
    await users_collection.update_one({"_id": oid}, {"$set": {"role": role}})
    return {"message": f"User role updated to {role}"}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(get_admin_user)):
    try:
        oid = ObjectId(user_id)
    except Exception:
        return JSONResponse(status_code=400, content={"message": "Invalid user ID"})
    result = await users_collection.delete_one({"_id": oid})
    if result.deleted_count == 0:
        return JSONResponse(status_code=404, content={"message": "User not found"})
    await history_collection.delete_many({"userId": user_id})
    return {"message": "User and all their data deleted"}


@router.get("/history")
async def admin_all_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_admin_user)
):
    skip = (page - 1) * limit
    cursor = history_collection.find({}).sort("uploadedAt", -1).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    total = await history_collection.count_documents({})
    result = []
    for item in items:
        d = dict(item)
        d["_id"] = str(d["_id"])
        d.pop("quizFull", None)
        d.pop("summary", None)
        if isinstance(d.get("uploadedAt"), datetime):
            d["uploadedAt"] = d["uploadedAt"].isoformat()
        result.append(d)
    return {"items": result, "total": total, "page": page, "limit": limit}
