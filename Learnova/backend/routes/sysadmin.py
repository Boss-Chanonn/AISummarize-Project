from fastapi import APIRouter, Depends, Query
from backend.database.db import db, system_logs_collection, users_collection, history_collection
from backend.middleware.auth_middleware import get_system_admin_user
from backend.utils.api_errors import message_error
from backend.utils.serializers import serialize_mongo_doc, serialize_mongo_list
from datetime import datetime, timezone
from bson import ObjectId

router = APIRouter()


# ----------------------------- System Health -----------------------------
@router.get("/health")
async def system_health(current_user: dict = Depends(get_system_admin_user)):
    """Check health of external dependencies used by the platform."""
    import os
    import httpx
    # Check MongoDB
    db_ok = False
    try:
        from backend.database.db import client
        await client.admin.command("ping")
        db_ok = True
    except Exception:
        pass
    # Check Ollama
    ollama_ok = False
    ollama_base = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{ollama_base}/api/tags")
            ollama_ok = r.status_code == 200
    except Exception:
        pass
    return {
        "mongodb": "ok" if db_ok else "error",
        "ollama": "ok" if ollama_ok else "unavailable",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ----------------------------- System Summary -----------------------------
@router.get("/stats")
async def system_stats(current_user: dict = Depends(get_system_admin_user)):
    """Return high-level system totals for admin overview cards."""
    total_users = await users_collection.count_documents({})
    total_docs = await history_collection.count_documents({})
    total_completed = await history_collection.count_documents({"done": True})
    total_logs = await system_logs_collection.count_documents({})
    return {
        "totalUsers": total_users,
        "totalDocuments": total_docs,
        "totalCompleted": total_completed,
        "totalLogs": total_logs,
    }


# ----------------------------- Logs and Data View -----------------------------
@router.get("/logs")
async def get_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=1000),
    current_user: dict = Depends(get_system_admin_user)
):
    """Return paginated system logs in newest-first order."""
    skip = (page - 1) * limit
    cursor = system_logs_collection.find({}).sort("timestamp", -1).skip(skip).limit(limit)
    logs = await cursor.to_list(length=limit)
    total = await system_logs_collection.count_documents({})
    result = serialize_mongo_list(logs, datetime_fields={"timestamp"})
    return {"logs": result, "total": total, "page": page, "limit": limit}


@router.get("/db/{collection_name}")
async def view_collection(
    collection_name: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_system_admin_user)
):
    """View documents from an allowed collection with pagination."""
    allowed = {"users", "history", "system_logs", "token_blocklist"}
    if collection_name not in allowed:
        # Keep legacy "error" key for compatibility with existing admin tooling.
        return {"error": f"Collection '{collection_name}' not accessible. Allowed: {sorted(allowed)}"}
    col = db[collection_name]
    skip = (page - 1) * limit
    cursor = col.find({}).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    total = await col.count_documents({})
    result = [
        serialize_mongo_doc(item, drop_fields={"password"})
        for item in items
    ]
    return {"collection": collection_name, "items": result, "total": total, "page": page, "limit": limit}


# ----------------------------- User Status Management -----------------------------
@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    body: dict,
    current_user: dict = Depends(get_system_admin_user)
):
    """Toggle a user account between active and inactive status."""
    new_status = body.get("status")
    if new_status not in ("active", "inactive"):
        return message_error(400, "status must be 'active' or 'inactive'")
    try:
        oid = ObjectId(user_id)
    except Exception:
        return message_error(400, "Invalid user ID")

    # Prevent deactivating own account
    if str(current_user.get("_id", "")) == user_id:
        return message_error(403, "Cannot change your own account status")

    user = await users_collection.find_one({"_id": oid})
    if not user:
        return message_error(404, "User not found")

    await users_collection.update_one({"_id": oid}, {"$set": {"status": new_status}})
    return {"message": f"User status updated to {new_status}", "status": new_status}


# ----------------------------- Destructive Actions -----------------------------
@router.delete("/db/{collection_name}/documents")
async def delete_documents(
    collection_name: str,
    body: dict,
    current_user: dict = Depends(get_system_admin_user)
):
    """Delete selected documents from one allowed collection with safety checks."""
    allowed = {"users", "history", "system_logs", "token_blocklist"}
    if collection_name not in allowed:
        return message_error(400, "Collection not accessible")

    ids = body.get("ids")
    if not ids or not isinstance(ids, list):
        return message_error(400, "ids must be a non-empty list")
    if len(ids) > 100:
        return message_error(400, "Cannot delete more than 100 documents at once")

    oids = []
    for id_str in ids:
        try:
            oids.append(ObjectId(str(id_str)))
        except Exception:
            pass
    if not oids:
        return message_error(400, "No valid IDs provided")

    # Safety: never delete system_admin accounts
    if collection_name == "users":
        blocked = await users_collection.count_documents({"_id": {"$in": oids}, "role": "system_admin"})
        if blocked > 0:
            return message_error(403, "Cannot delete system_admin accounts")

    col = db[collection_name]
    result = await col.delete_many({"_id": {"$in": oids}})
    return {"deleted": result.deleted_count}
