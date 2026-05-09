from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from backend.database.db import users_collection, history_collection
from backend.middleware.auth_middleware import get_admin_user
from backend.models.user import AdminUpdateProfile, AdminUpdateAccount
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from passlib.context import CryptContext

router = APIRouter()

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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

    # Batch-load user names/emails
    raw_ids = [item.get("userId") for item in items if item.get("userId")]
    oid_list = []
    for uid in raw_ids:
        try:
            oid_list.append(ObjectId(uid))
        except Exception:
            pass
    user_map = {}
    if oid_list:
        async for u in users_collection.find({"_id": {"$in": oid_list}}, {"name": 1, "email": 1}):
            user_map[str(u["_id"])] = {"name": u.get("name", ""), "email": u.get("email", "")}

    result = []
    for item in items:
        d = dict(item)
        d["_id"] = str(d["_id"])
        d.pop("quizFull", None)          # too heavy for list view
        if isinstance(d.get("uploadedAt"), datetime):
            d["uploadedAt"] = d["uploadedAt"].isoformat()
        if isinstance(d.get("completedAt"), datetime):
            d["completedAt"] = d["completedAt"].isoformat()
        uid = d.get("userId", "")
        u_info = user_map.get(uid, {})
        d["userName"] = u_info.get("name", "Unknown")
        d["userEmail"] = u_info.get("email", "")
        result.append(d)
    return {"items": result, "total": total, "page": page, "limit": limit}


# ── New fine-grained admin endpoints ─────────────────────────────────────────

@router.put("/user/{user_id}/profile")
async def admin_update_profile(
    user_id: str,
    body: AdminUpdateProfile,
    current_user: dict = Depends(get_admin_user)
):
    try:
        oid = ObjectId(user_id)
    except Exception:
        return JSONResponse(status_code=400, content={"message": "Invalid user ID"})

    update_fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not update_fields:
        return JSONResponse(status_code=400, content={"message": "No fields to update"})

    # If email is changing, make sure it is not taken by another user
    if "email" in update_fields:
        clash = await users_collection.find_one(
            {"email": update_fields["email"], "_id": {"$ne": oid}}
        )
        if clash:
            return JSONResponse(status_code=409, content={"message": "Email already in use"})

    await users_collection.update_one({"_id": oid}, {"$set": update_fields})
    user = await users_collection.find_one({"_id": oid})
    if not user:
        return JSONResponse(status_code=404, content={"message": "User not found"})
    return _serialize_user(user)


@router.put("/user/{user_id}/account")
async def admin_update_account(
    user_id: str,
    body: AdminUpdateAccount,
    current_user: dict = Depends(get_admin_user)
):
    try:
        oid = ObjectId(user_id)
    except Exception:
        return JSONResponse(status_code=400, content={"message": "Invalid user ID"})

    update_fields = {}
    if body.role is not None:
        if body.role not in ("user", "admin"):
            return JSONResponse(status_code=400, content={"message": "role must be 'user' or 'admin'"})
        update_fields["role"] = body.role
    if body.tier is not None:
        if body.tier not in ("free", "pro"):
            return JSONResponse(status_code=400, content={"message": "tier must be 'free' or 'pro'"})
        update_fields["tier"] = body.tier
    if body.status is not None:
        if body.status not in ("active", "inactive"):
            return JSONResponse(status_code=400, content={"message": "status must be 'active' or 'inactive'"})
        update_fields["status"] = body.status

    if not update_fields:
        return JSONResponse(status_code=400, content={"message": "No valid fields to update"})

    await users_collection.update_one({"_id": oid}, {"$set": update_fields})
    user = await users_collection.find_one({"_id": oid})
    if not user:
        return JSONResponse(status_code=404, content={"message": "User not found"})
    return _serialize_user(user)


@router.post("/user/{user_id}/reset-password")
async def admin_reset_password(
    user_id: str,
    current_user: dict = Depends(get_admin_user)
):
    try:
        oid = ObjectId(user_id)
    except Exception:
        return JSONResponse(status_code=400, content={"message": "Invalid user ID"})

    user = await users_collection.find_one({"_id": oid})
    if not user:
        return JSONResponse(status_code=404, content={"message": "User not found"})

    hashed = _pwd_context.hash("Learnova@2026")
    await users_collection.update_one({"_id": oid}, {"$set": {"password": hashed}})
    return {"success": True, "message": "Password reset to default"}
