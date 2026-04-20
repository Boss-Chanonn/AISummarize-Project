from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from backend.database.db import history_collection
from backend.middleware.auth_middleware import get_current_user
from datetime import datetime
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


@router.get("/results")
async def get_results(
    id: int = Query(0),
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])

    if id:
        item = await history_collection.find_one({"userId": user_id, "seqId": id})
    else:
        item = await history_collection.find_one(
            {"userId": user_id}, sort=[("uploadedAt", -1)]
        )

    if not item:
        return JSONResponse(
            status_code=404,
            content={"message": "Result not found. Complete a quiz first."},
        )

    return serialize_history(item)


@router.get("/modules")
async def get_modules(
    historyId: int = Query(0),
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])

    if historyId:
        item = await history_collection.find_one(
            {"userId": user_id, "seqId": historyId}
        )
    else:
        item = await history_collection.find_one(
            {"userId": user_id}, sort=[("uploadedAt", -1)]
        )

    if not item:
        return JSONResponse(
            status_code=404,
            content={"message": "No module data found. Complete a quiz first."},
        )

    weaknesses = item.get("weaknesses", [])
    study_next = item.get("studyNext", [])
    topics = (weaknesses + study_next)[:4]
    while len(topics) < 4:
        topics.append("study skills")

    types = ["video", "article", "video", "podcast"]
    sources = [
        "MIT OpenCourseWare \u00b7 YouTube",
        "Nature \u2014 npj Science of Learning",
        "EdSurge \u00b7 Vimeo",
        "The EdTech Podcast \u00b7 Spotify",
    ]
    durations = ["18 min", "12 min read", "24 min", "38 min"]
    tags = ["Watched", "Peer-reviewed", "Expert speaker", "Transcript available"]
    badges = [
        {"class": "badge-dim", "label": "Done"},
        {"class": "badge-gold", "label": "Recommended"},
        {"class": "badge-green", "label": "New"},
        {"class": "badge-gold", "label": "Recommended"},
    ]
    statuses = ["done", "none", "none", "none"]

    def title_fn(i: int, topic: str) -> str:
        fns = [
            lambda t: f"Understanding {t} in depth",
            lambda t: f"The evidence on {t} in education",
            lambda t: f"{t[0].upper()}{t[1:]} in practice: A guide",
            lambda t: f"Rethinking {t} \u2014 experts discuss",
        ]
        return fns[i](topic)

    main_topic = (weaknesses[0] if weaknesses else (study_next[0] if study_next else "key concepts")).lower()
    total_minutes = 92

    resources = []
    for i, topic in enumerate(topics):
        resources.append({
            "id": i,
            "type": types[i],
            "title": title_fn(i, topic),
            "source": sources[i],
            "duration": durations[i],
            "tag": tags[i],
            "badge": badges[i],
            "status": statuses[i],
        })

    return {
        "historyId": item.get("seqId", 0),
        "docTitle": item.get("title", ""),
        "moduleTitle": main_topic,
        "description": f"Based on your quiz results, you missed questions about {main_topic}. These resources will help close that gap \u2014 estimated {total_minutes} min total.",
        "totalMinutes": total_minutes,
        "resourceCount": len(topics),
        "progress": {
            "done": 1,
            "scheduled": 1,
            "remaining": len(topics) - 1,
            "pct": math.floor(1 / len(topics) * 100),
        },
        "focusAreas": [
            {
                "title": "Rebuild the weak spot",
                "body": f"Understand why {main_topic} matters and what the research says.",
            },
            {
                "title": "Learn through mixed formats",
                "body": "Short article, practical video, and podcast pacing to keep the module engaging.",
            },
            {
                "title": "Leave with clearer recall",
                "body": "Use the scheduled resources to reinforce the same concept from multiple angles.",
            },
        ],
        "resources": resources,
    }
