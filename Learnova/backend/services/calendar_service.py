import os
import httpx
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional


# ----------------------------- Configuration -----------------------------

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/calendar/google/callback")

OUTLOOK_CLIENT_ID = os.getenv("OUTLOOK_CLIENT_ID", "")
OUTLOOK_CLIENT_SECRET = os.getenv("OUTLOOK_CLIENT_SECRET", "")
OUTLOOK_REDIRECT_URI = os.getenv("OUTLOOK_REDIRECT_URI", "http://localhost:8000/api/calendar/outlook/callback")

# ----------------------------- Google Calendar -----------------------------

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_API = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def google_oauth_url(state: str) -> str:
    """Build the Google OAuth2 authorization URL with calendar write scope."""
    params = (
        f"client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={' '.join(GOOGLE_SCOPES)}"
        f"&access_type=offline"
        f"&state={state}"
        f"&prompt=consent"
    )
    return f"{GOOGLE_AUTH_URL}?{params}"


async def google_exchange_code(code: str) -> dict | None:
    """Exchange an authorization code for Google OAuth tokens."""
    if not GOOGLE_CLIENT_ID:
        return None
    async with httpx.AsyncClient() as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        })
        if resp.status_code != 200:
            return None
        data = resp.json()
        expires_at = datetime.now(timezone.utc).timestamp() + data.get("expires_in", 3600)
        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", ""),
            "expires_at": expires_at,
        }


async def google_refresh_token(refresh_token: str) -> dict | None:
    """Refresh an expired Google access token using the refresh token."""
    if not GOOGLE_CLIENT_ID or not refresh_token:
        return None
    async with httpx.AsyncClient() as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        })
        if resp.status_code != 200:
            return None
        data = resp.json()
        expires_at = datetime.now(timezone.utc).timestamp() + data.get("expires_in", 3600)
        return {
            "access_token": data["access_token"],
            "expires_at": expires_at,
        }


async def google_create_event(access_token: str, title: str, description: str, start: str, end: str) -> dict | None:
    """Create a Google Calendar event using the user's access token."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start, "timeZone": "UTC"},
        "end": {"dateTime": end, "timeZone": "UTC"},
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(GOOGLE_CALENDAR_API, headers=headers, json=body)
        if resp.status_code not in (200, 201):
            return None
        return resp.json()


async def google_get_user_email(access_token: str) -> str:
    """Fetch the user's Google account email from the tokeninfo endpoint."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/oauth2/v1/tokeninfo",
            params={"access_token": access_token},
        )
        if resp.status_code == 200:
            return resp.json().get("email", "")
    return ""


# ----------------------------- Outlook Calendar -----------------------------

OUTLOOK_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
OUTLOOK_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
OUTLOOK_GRAPH_API = "https://graph.microsoft.com/v1.0/me/calendar/events"
OUTLOOK_SCOPES = "Calendars.ReadWrite offline_access"


def outlook_oauth_url(state: str) -> str:
    """Build the Microsoft OAuth2 authorization URL for Outlook calendar."""
    params = (
        f"client_id={OUTLOOK_CLIENT_ID}"
        f"&redirect_uri={OUTLOOK_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={OUTLOOK_SCOPES}"
        f"&state={state}"
    )
    return f"{OUTLOOK_AUTH_URL}?{params}"


async def outlook_exchange_code(code: str) -> dict | None:
    """Exchange an authorization code for Outlook (Microsoft Graph) OAuth tokens."""
    if not OUTLOOK_CLIENT_ID:
        return None
    async with httpx.AsyncClient() as client:
        resp = await client.post(OUTLOOK_TOKEN_URL, data={
            "client_id": OUTLOOK_CLIENT_ID,
            "client_secret": OUTLOOK_CLIENT_SECRET,
            "redirect_uri": OUTLOOK_REDIRECT_URI,
            "code": code,
            "grant_type": "authorization_code",
        })
        if resp.status_code != 200:
            return None
        data = resp.json()
        expires_at = datetime.now(timezone.utc).timestamp() + data.get("expires_in", 3600)
        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", ""),
            "expires_at": expires_at,
        }


async def outlook_refresh_token(refresh_token: str) -> dict | None:
    """Refresh an expired Outlook access token."""
    if not OUTLOOK_CLIENT_ID or not refresh_token:
        return None
    async with httpx.AsyncClient() as client:
        resp = await client.post(OUTLOOK_TOKEN_URL, data={
            "client_id": OUTLOOK_CLIENT_ID,
            "client_secret": OUTLOOK_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        })
        if resp.status_code != 200:
            return None
        data = resp.json()
        expires_at = datetime.now(timezone.utc).timestamp() + data.get("expires_in", 3600)
        return {
            "access_token": data["access_token"],
            "expires_at": expires_at,
        }


async def outlook_create_event(access_token: str, title: str, description: str, start: str, end: str) -> dict | None:
    """Create an Outlook calendar event using the Microsoft Graph API."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    body = {
        "subject": title,
        "body": {"contentType": "text", "content": description},
        "start": {"dateTime": start, "timeZone": "UTC"},
        "end": {"dateTime": end, "timeZone": "UTC"},
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(OUTLOOK_GRAPH_API, headers=headers, json=body)
        if resp.status_code not in (200, 201):
            return None
        return resp.json()


async def outlook_get_user_email(access_token: str) -> str:
    """Fetch the user's Outlook email from Microsoft Graph /me endpoint."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if resp.status_code == 200:
            return resp.json().get("mail", resp.json().get("userPrincipalName", ""))
    return ""


# ----------------------------- Apple Calendar (.ics) -----------------------------

def generate_ics_content(title: str, description: str, start: str, end: str, uid: str = "") -> str:
    """Generate an iCalendar (.ics) file content for Apple Calendar import."""
    uid = uid or str(uuid.uuid4())
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    start_ics = _to_ics_dt(start)
    end_ics = _to_ics_dt(end)
    return (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//Learnova//Study Calendar//EN\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "METHOD:PUBLISH\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{uid}\r\n"
        f"DTSTAMP:{now}\r\n"
        f"DTSTART:{start_ics}\r\n"
        f"DTEND:{end_ics}\r\n"
        f"SUMMARY:{_escape_ics(title)}\r\n"
        f"DESCRIPTION:{_escape_ics(description)}\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )


def _to_ics_dt(iso_dt: str) -> str:
    """Convert an ISO datetime string to iCalendar UTC format (YYYYMMDDTHHMMSSZ)."""
    try:
        dt = datetime.fromisoformat(iso_dt.replace("Z", "+00:00"))
        return dt.strftime("%Y%m%dT%H%M%SZ")
    except Exception:
        return iso_dt


def _escape_ics(text: str) -> str:
    """Escape special characters for iCalendar text fields."""
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


# ----------------------------- Provider Helpers -----------------------------

PROVIDER_NAMES = {"google": "Google Calendar", "outlook": "Outlook Calendar", "apple": "Apple Calendar"}


async def refresh_and_get_token(connection: dict) -> str | None:
    """Refresh an access token if expired, or return the current one."""
    provider = connection.get("provider", "")
    access_token = connection.get("access_token", "")
    expires_at = connection.get("expires_at", 0)
    refresh_tok = connection.get("refresh_token", "")

    now = datetime.now(timezone.utc).timestamp()
    if expires_at and expires_at > now + 60:
        return access_token

    if provider == "google" and refresh_tok:
        result = await google_refresh_token(refresh_tok)
        if result:
            return result["access_token"]
    elif provider == "outlook" and refresh_tok:
        result = await outlook_refresh_token(refresh_tok)
        if result:
            return result["access_token"]

    return access_token


async def create_provider_event(
    provider: str,
    connection: dict,
    title: str,
    description: str,
    start_time: str,
    end_time: str,
) -> dict | None:
    """Create a calendar event on the specified provider."""
    access_token = await refresh_and_get_token(connection)
    if not access_token:
        return None

    if provider == "google":
        result = await google_create_event(access_token, title, description, start_time, end_time)
        if result:
            return {"event_id": result.get("id", ""), "html_link": result.get("htmlLink", "")}
    elif provider == "outlook":
        result = await outlook_create_event(access_token, title, description, start_time, end_time)
        if result:
            return {"event_id": result.get("id", ""), "html_link": ""}

    return None
