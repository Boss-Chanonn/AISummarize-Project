from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from backend.database.db import db, system_logs_collection, users_collection, history_collection
from backend.middleware.auth_middleware import get_system_admin_user
from datetime import datetime, timezone
from bson import ObjectId

router = APIRouter()


@router.get("/health")
async def system_health(current_user: dict = Depends(get_system_admin_user)):
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


@router.get("/stats")
async def system_stats(current_user: dict = Depends(get_system_admin_user)):
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


@router.get("/logs")
async def get_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=1000),
    current_user: dict = Depends(get_system_admin_user)
):
    skip = (page - 1) * limit
    cursor = system_logs_collection.find({}).sort("timestamp", -1).skip(skip).limit(limit)
    logs = await cursor.to_list(length=limit)
    total = await system_logs_collection.count_documents({})
    result = []
    for log in logs:
        d = dict(log)
        d["_id"] = str(d["_id"])
        if isinstance(d.get("timestamp"), datetime):
            d["timestamp"] = d["timestamp"].isoformat()
        result.append(d)
    return {"logs": result, "total": total, "page": page, "limit": limit}


@router.get("/db/{collection_name}")
async def view_collection(
    collection_name: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_system_admin_user)
):
    allowed = {"users", "history", "system_logs", "token_blocklist"}
    if collection_name not in allowed:
        return {"error": f"Collection '{collection_name}' not accessible. Allowed: {sorted(allowed)}"}
    col = db[collection_name]
    skip = (page - 1) * limit
    cursor = col.find({}).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    total = await col.count_documents({})
    result = []
    for item in items:
        d = dict(item)
        d["_id"] = str(d["_id"])
        d.pop("password", None)
        for k, v in d.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        result.append(d)
    return {"collection": collection_name, "items": result, "total": total, "page": page, "limit": limit}


@router.delete("/db/{collection_name}/documents")
async def delete_documents(
    collection_name: str,
    body: dict,
    current_user: dict = Depends(get_system_admin_user)
):
    allowed = {"users", "history", "system_logs", "token_blocklist"}
    if collection_name not in allowed:
        return JSONResponse(status_code=400, content={"message": "Collection not accessible"})

    ids = body.get("ids")
    if not ids or not isinstance(ids, list):
        return JSONResponse(status_code=400, content={"message": "ids must be a non-empty list"})
    if len(ids) > 100:
        return JSONResponse(status_code=400, content={"message": "Cannot delete more than 100 documents at once"})

    oids = []
    for id_str in ids:
        try:
            oids.append(ObjectId(str(id_str)))
        except Exception:
            pass
    if not oids:
        return JSONResponse(status_code=400, content={"message": "No valid IDs provided"})

    # Safety: never delete system_admin accounts
    if collection_name == "users":
        blocked = await users_collection.count_documents({"_id": {"$in": oids}, "role": "system_admin"})
        if blocked > 0:
            return JSONResponse(status_code=403, content={"message": "Cannot delete system_admin accounts"})

    col = db[collection_name]
    result = await col.delete_many({"_id": {"$in": oids}})
    return {"deleted": result.deleted_count}
