from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from backend.middleware.security import SecurityHeadersMiddleware
from backend.database.db import client, token_blocklist_collection, system_logs_collection
from dotenv import load_dotenv
from datetime import datetime, timezone
from jose import jwt as _jwt
import json
import os

load_dotenv()


# ----------------------------- App Configuration -----------------------------
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000").split(",")

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Learnova API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ----------------------------- Registered Middleware -----------------------------
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------- Activity Logging -----------------------------
_LOG_SECRET = os.getenv("SECRET_KEY", "changeme")


def _extract_user_email_from_header(auth_header: str) -> str | None:
    """Read the user email from a bearer token when one is present."""
    if not auth_header.startswith("Bearer "):
        return None

    try:
        payload = _jwt.decode(auth_header[7:], _LOG_SECRET, algorithms=["HS256"])
        return payload.get("email")
    except Exception:
        return None


async def _extract_login_email_from_request(request: Request) -> str | None:
    """Read login email from JSON body and restore the body for the route handler."""
    if request.method != "POST" or request.url.path != "/api/auth/login":
        return None

    try:
        body = await request.body()

        async def receive() -> dict:
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = receive
        payload = json.loads(body.decode("utf-8")) if body else {}
        email = payload.get("email")
        if isinstance(email, str) and email.strip():
            return email.strip()
    except Exception:
        return None

    return None


async def _resolve_log_user_email(request: Request) -> str | None:
    """Choose the best available user identity for one activity log entry."""
    header_email = _extract_user_email_from_header(
        request.headers.get("Authorization", "")
    )
    if header_email:
        return header_email

    return await _extract_login_email_from_request(request)


async def _write_system_log(request: Request, status_code: int, user_email: str | None) -> None:
    """Store one API activity log entry without interrupting the request flow."""
    await system_logs_collection.insert_one({
        "method": request.method,
        "path": request.url.path,
        "status": status_code,
        "ip": request.client.host if request.client else "unknown",
        "user_email": user_email,
        "timestamp": datetime.now(timezone.utc),
    })

@app.middleware("http")
async def log_activity(request: Request, call_next):
    """Log API requests for system-admin audit views after each response."""
    user_email = await _resolve_log_user_email(request)
    response = await call_next(request)
    # Only log API calls (not static files)
    if request.url.path.startswith("/api/"):
        try:
            await _write_system_log(request, response.status_code, user_email)
        except Exception:
            pass
    return response


# ----------------------------- Router Registration -----------------------------
from backend.routes.auth import router as auth_router
from backend.routes.user import router as user_router
from backend.routes.upload import router as upload_router
from backend.routes.history import router as history_router
from backend.routes.content import router as content_router
from backend.routes.admin import router as admin_router
from backend.routes.admin_stats import router as admin_stats_router
from backend.routes.sysadmin import router as sysadmin_router
from backend.routes.billing import router as billing_router

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(user_router, prefix="/api/user", tags=["user"])
app.include_router(upload_router, prefix="/api", tags=["upload"])
app.include_router(history_router, prefix="/api/history", tags=["history"])
app.include_router(content_router, prefix="/api", tags=["content"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
app.include_router(admin_stats_router, prefix="/api/admin", tags=["admin-stats"])
app.include_router(sysadmin_router, prefix="/api/sysadmin", tags=["sysadmin"])
app.include_router(billing_router, prefix="/api/billing", tags=["billing"])


# ----------------------------- Health and Startup -----------------------------
@app.get("/api/health")
async def health():
    """Return a lightweight health payload for smoke tests and monitoring."""
    return {"status": "ok", "app": "Learnova"}


@app.on_event("startup")
async def startup_event():
    """Verify critical backend services and prepare DB indexes on app startup."""
    try:
        await client.admin.command("ping")
        print("✅ MongoDB connected")
        await token_blocklist_collection.create_index("expireAt", expireAfterSeconds=0)
        print("✅ Token blocklist TTL index ready")
        print("✅ Learnova backend started")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")


# ----------------------------- Frontend Hosting -----------------------------
# Serve frontend last so API routes are matched before static file fallback.
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

