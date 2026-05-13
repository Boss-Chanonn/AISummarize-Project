from fastapi import APIRouter, Depends, Query
from backend.database.db import users_collection, history_collection
from backend.middleware.auth_middleware import get_admin_user, get_system_admin_user
from backend.models.user import AdminUpdateProfile, AdminUpdateAccount
from backend.utils.api_errors import message_error
from backend.utils.serializers import serialize_mongo_doc
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from passlib.context import CryptContext

router = APIRouter()

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ----------------------------- Serializer Helpers -----------------------------
def _serialize_user(u: dict) -> dict:
    """Serialize user document for admin responses and hide password field."""
    return serialize_mongo_doc(
        u,
        datetime_fields={"createdAt"},
        drop_fields={"password"},
    )


# ----------------------------- Dashboard Endpoints -----------------------------
@router.get("/dashboard")
async def admin_dashboard(current_user: dict = Depends(get_system_admin_user)):
    """Return high-level admin dashboard statistics."""
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


# ----------------------------- User Listing Endpoints -----------------------------
@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_admin_user)
):
    """Return paginated users with file counts for admin user table."""
    skip = (page - 1) * limit
    cursor = users_collection.find({}).sort("createdAt", -1).skip(skip).limit(limit)
    users = await cursor.to_list(length=limit)
    total = await users_collection.count_documents({})

    # Add per-user document counts for the "Files" column in admin-users.html.
    user_ids = [str(u.get("_id")) for u in users if u.get("_id")]
    file_count_map = {}
    if user_ids:
        pipeline = [
            {"$match": {"userId": {"$in": user_ids}}},
            {"$group": {"_id": "$userId", "count": {"$sum": 1}}},
        ]
        async for row in history_collection.aggregate(pipeline):
            file_count_map[str(row.get("_id", ""))] = int(row.get("count", 0))

    out_users = []
    for u in users:
        su = _serialize_user(u)
        su["files"] = file_count_map.get(su["_id"], 0)
        out_users.append(su)

    return {"users": out_users, "total": total, "page": page, "limit": limit}


@router.get("/users/{user_id}")
async def get_user(user_id: str, current_user: dict = Depends(get_admin_user)):
    """Return one user profile by user ID for admin view."""
    try:
        oid = ObjectId(user_id)
    except Exception:
        return message_error(400, "Invalid user ID")
    user = await users_collection.find_one({"_id": oid})
    if not user:
        return message_error(404, "User not found")
    return _serialize_user(user)


# ----------------------------- User Account Mutations -----------------------------
@router.put("/users/{user_id}/tier")
async def update_user_tier(
    user_id: str,
    body: dict,
    current_user: dict = Depends(get_admin_user)
):
    """Update user subscription tier to free or pro."""
    tier = body.get("tier")
    if tier not in ("free", "pro"):
        return message_error(400, "Tier must be 'free' or 'pro'")
    try:
        oid = ObjectId(user_id)
    except Exception:
        return message_error(400, "Invalid user ID")
    await users_collection.update_one({"_id": oid}, {"$set": {"tier": tier}})
    return {"message": f"User tier updated to {tier}"}


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    body: dict,
    current_user: dict = Depends(get_admin_user)
):
    """Update user role to user/admin/system_admin."""
    role = body.get("role")
    if role not in ("user", "admin", "system_admin"):
        return message_error(400, "Invalid role")
    try:
        oid = ObjectId(user_id)
    except Exception:
        return message_error(400, "Invalid user ID")
    await users_collection.update_one({"_id": oid}, {"$set": {"role": role}})
    return {"message": f"User role updated to {role}"}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(get_admin_user)):
    """Block direct deletion endpoint and instruct safe archive behavior."""
    return message_error(403, "User deletion is disabled. Use archive by setting status to 'inactive'.")


# ----------------------------- Admin History Endpoints -----------------------------
@router.get("/history")
async def admin_all_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_admin_user)
):
    """Return paginated upload history across all users for admin pages."""
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
        d = serialize_mongo_doc(
            item,
            datetime_fields={"uploadedAt", "completedAt"},
            drop_fields={"quizFull"},
        )  # quizFull is too heavy for list view
        uid = d.get("userId", "")
        u_info = user_map.get(uid, {})
        d["userName"] = u_info.get("name", "Unknown")
        d["userEmail"] = u_info.get("email", "")
        result.append(d)
    return {"items": result, "total": total, "page": page, "limit": limit}


# ----------------------------- Fine-Grained Admin Endpoints -----------------------------

@router.put("/user/{user_id}/profile")
async def admin_update_profile(
    user_id: str,
    body: AdminUpdateProfile,
    current_user: dict = Depends(get_admin_user)
):
    """Update profile fields (name/email/phone/dob) for one user."""
    try:
        oid = ObjectId(user_id)
    except Exception:
        return message_error(400, "Invalid user ID")

    update_fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not update_fields:
        return message_error(400, "No fields to update")

    # If email is changing, make sure it is not taken by another user
    if "email" in update_fields:
        clash = await users_collection.find_one(
            {"email": update_fields["email"], "_id": {"$ne": oid}}
        )
        if clash:
            return message_error(409, "Email already in use")

    await users_collection.update_one({"_id": oid}, {"$set": update_fields})
    user = await users_collection.find_one({"_id": oid})
    if not user:
        return message_error(404, "User not found")
    return _serialize_user(user)


@router.put("/user/{user_id}/account")
async def admin_update_account(
    user_id: str,
    body: AdminUpdateAccount,
    current_user: dict = Depends(get_admin_user)
):
    """Update account-level fields (role/tier/status) for one user."""
    try:
        oid = ObjectId(user_id)
    except Exception:
        return message_error(400, "Invalid user ID")

    update_fields = {}
    if body.role is not None:
        if body.role not in ("user", "admin"):
            return message_error(400, "role must be 'user' or 'admin'")
        update_fields["role"] = body.role
    if body.tier is not None:
        if body.tier not in ("free", "pro"):
            return message_error(400, "tier must be 'free' or 'pro'")
        update_fields["tier"] = body.tier
    if body.status is not None:
        if body.status not in ("active", "inactive"):
            return message_error(400, "status must be 'active' or 'inactive'")
        update_fields["status"] = body.status

    if not update_fields:
        return message_error(400, "No valid fields to update")

    await users_collection.update_one({"_id": oid}, {"$set": update_fields})
    user = await users_collection.find_one({"_id": oid})
    if not user:
        return message_error(404, "User not found")
    return _serialize_user(user)


@router.post("/user/{user_id}/reset-password")
async def admin_reset_password(
    user_id: str,
    current_user: dict = Depends(get_admin_user)
):
    """Reset a user password to default value for recovery workflow."""
    try:
        oid = ObjectId(user_id)
    except Exception:
        return message_error(400, "Invalid user ID")

    user = await users_collection.find_one({"_id": oid})
    if not user:
        return message_error(404, "User not found")

    hashed = _pwd_context.hash("Learnova@2026")
    await users_collection.update_one({"_id": oid}, {"$set": {"password": hashed}})
    return {"success": True, "message": "Password reset to default"}
