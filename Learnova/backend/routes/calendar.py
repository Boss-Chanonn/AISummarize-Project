from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import RedirectResponse, Response as FastAPIResponse
from backend.database.db import users_collection
from backend.middleware.auth_middleware import get_current_user
from backend.utils.api_errors import message_error
from backend.services.calendar_service import (
    google_oauth_url, google_exchange_code, google_get_user_email,
    outlook_oauth_url, outlook_exchange_code, outlook_get_user_email,
    generate_ics_content, create_provider_event, PROVIDER_NAMES,
)
from datetime import datetime, timezone
from bson import ObjectId
import uuid

router = APIRouter()

# In-memory store for pending OAuth states (state -> user_id string)
_pending_oauth: dict[str, str] = {}


# ----------------------------- Calendar Status -----------------------------

@router.get("/status")
async def get_calendar_status(current_user: dict = Depends(get_current_user)):
    """Return which calendar providers the current user has connected."""
    connections = current_user.get("calendar_connections", [])
    providers = {}
    for conn in connections:
        p = conn.get("provider", "")
        providers[p] = {"connected": True, "email": conn.get("email", "")}
    return {
        "google": providers.get("google", {}).get("connected", False),
        "google_email": providers.get("google", {}).get("email", ""),
        "outlook": providers.get("outlook", {}).get("connected", False),
        "outlook_email": providers.get("outlook", {}).get("email", ""),
        "apple": providers.get("apple", {}).get("connected", False),
        "apple_email": providers.get("apple", {}).get("email", ""),
    }


# ----------------------------- Google OAuth -----------------------------

@router.get("/google/auth")
async def google_auth(current_user: dict = Depends(get_current_user)):
    """Return Google OAuth URL for the current user to authorize."""
    state = str(uuid.uuid4())
    _pending_oauth[state] = str(current_user["_id"])
    url = google_oauth_url(state)
    return {"auth_url": url, "state": state}


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str = Query(""),
    state: str = Query(""),
):
    """Handle Google OAuth callback: exchange code, store tokens, redirect to frontend."""
    if not code:
        return RedirectResponse(url="/module.html?calendar=error&reason=no_code")

    user_id = _pending_oauth.pop(state, None)
    if not user_id:
        return RedirectResponse(url="/module.html?calendar=error&reason=invalid_state")

    tokens = await google_exchange_code(code)
    if not tokens:
        return RedirectResponse(url="/module.html?calendar=error&reason=google_failed")

    email = await google_get_user_email(tokens["access_token"])

    connection = {
        "provider": "google",
        "email": email,
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token", ""),
        "expires_at": tokens.get("expires_at", 0),
        "connected_at": datetime.now(timezone.utc).isoformat(),
    }

    await _upsert_connection_by_id(user_id, connection)
    return RedirectResponse(url=f"/module.html?calendar=connected&provider=google&email={email}")


# ----------------------------- Outlook OAuth -----------------------------

@router.get("/outlook/auth")
async def outlook_auth(current_user: dict = Depends(get_current_user)):
    """Return Outlook OAuth URL for the current user to authorize."""
    state = str(uuid.uuid4())
    _pending_oauth[state] = str(current_user["_id"])
    url = outlook_oauth_url(state)
    return {"auth_url": url, "state": state}


@router.get("/outlook/callback")
async def outlook_callback(
    code: str = Query(""),
    state: str = Query(""),
):
    """Handle Outlook OAuth callback: exchange code, store tokens, redirect to frontend."""
    if not code:
        return RedirectResponse(url="/module.html?calendar=error&reason=no_code")

    user_id = _pending_oauth.pop(state, None)
    if not user_id:
        return RedirectResponse(url="/module.html?calendar=error&reason=invalid_state")

    tokens = await outlook_exchange_code(code)
    if not tokens:
        return RedirectResponse(url="/module.html?calendar=error&reason=outlook_failed")

    email = await outlook_get_user_email(tokens["access_token"])

    connection = {
        "provider": "outlook",
        "email": email,
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token", ""),
        "expires_at": tokens.get("expires_at", 0),
        "connected_at": datetime.now(timezone.utc).isoformat(),
    }

    await _upsert_connection_by_id(user_id, connection)
    return RedirectResponse(url=f"/module.html?calendar=connected&provider=outlook&email={email}")


# ----------------------------- Apple Calendar (.ics) -----------------------------

@router.get("/apple/ical")
async def apple_ical(
    title: str = Query("Study Session"),
    description: str = Query(""),
    start: str = Query(""),
    end: str = Query(""),
    current_user: dict = Depends(get_current_user),
):
    """Generate an .ics file for Apple Calendar import."""
    ics_content = generate_ics_content(title, description, start, end)
    return FastAPIResponse(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=learnova-study-event.ics"},
    )


@router.post("/apple/connect")
async def apple_connect(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Store Apple Calendar CalDAV connection info for the user."""
    body = await request.json()
    email = body.get("email", "")
    connection = {
        "provider": "apple",
        "email": email,
        "caldav_url": body.get("caldav_url", ""),
        "access_token": "",
        "refresh_token": "",
        "expires_at": 0,
        "connected_at": datetime.now(timezone.utc).isoformat(),
    }
    await _upsert_connection(current_user, connection)
    return {"message": f"Apple Calendar configured for {email}"}


# ----------------------------- Event Creation -----------------------------

@router.post("/events")
async def create_calendar_event(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Create a calendar event on the user's connected provider."""
    body = await request.json()
    provider = body.get("provider", "").lower()
    title = body.get("title", "Study Session")
    description = body.get("description", "Learnova study session")
    start_time = body.get("start_time", "")
    end_time = body.get("end_time", "")

    if not provider:
        return message_error(400, "Calendar provider is required")
    if provider not in ("google", "outlook", "apple"):
        return message_error(400, f"Unsupported provider: {provider}")
    if not start_time or not end_time:
        return message_error(400, "start_time and end_time are required")

    if provider == "apple":
        params = f"title={title}&description={description}&start={start_time}&end={end_time}"
        return {
            "ics_url": f"/api/calendar/apple/ical?{params}",
            "message": "Download the .ics file to import into Apple Calendar",
        }

    connections = current_user.get("calendar_connections", [])
    connection = next((c for c in connections if c.get("provider") == provider), None)
    if not connection:
        return message_error(400, f"{PROVIDER_NAMES.get(provider, provider)} not connected. Connect it first.")

    result = await create_provider_event(provider, connection, title, description, start_time, end_time)
    if not result:
        return message_error(502, f"Failed to create event on {PROVIDER_NAMES.get(provider, provider)}")

    return {"message": "Event created", "event": result}


# ----------------------------- Disconnect -----------------------------

@router.post("/disconnect")
async def disconnect_calendar(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Remove a connected calendar provider from the user's account."""
    body = await request.json()
    provider = body.get("provider", "").lower()

    if not provider:
        return message_error(400, "Provider is required")

    connections = current_user.get("calendar_connections", [])
    filtered = [c for c in connections if c.get("provider") != provider]

    if len(filtered) == len(connections):
        return message_error(404, f"{PROVIDER_NAMES.get(provider, provider)} is not connected")

    await users_collection.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"calendar_connections": filtered}},
    )
    return {"message": f"{PROVIDER_NAMES.get(provider, provider)} disconnected"}


# ----------------------------- Helpers -----------------------------

async def _upsert_connection(user: dict, new_connection: dict) -> None:
    """Add or replace a calendar connection for the given user document."""
    provider = new_connection["provider"]
    connections = user.get("calendar_connections", [])
    filtered = [c for c in connections if c.get("provider") != provider]
    filtered.append(new_connection)
    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"calendar_connections": filtered}},
    )


async def _upsert_connection_by_id(user_id: str, new_connection: dict) -> None:
    """Add or replace a calendar connection by user ID (used in OAuth callback)."""
    provider = new_connection["provider"]
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        return
    connections = user.get("calendar_connections", [])
    filtered = [c for c in connections if c.get("provider") != provider]
    filtered.append(new_connection)
    await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"calendar_connections": filtered}},
    )
