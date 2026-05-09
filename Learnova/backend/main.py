from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from backend.middleware.security import SecurityHeadersMiddleware
from backend.database.db import client, token_blocklist_collection, system_logs_collection
from dotenv import load_dotenv
from datetime import datetime, timezone
import os

load_dotenv()

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000").split(",")

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Learnova API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Activity logging middleware
@app.middleware("http")
async def log_activity(request: Request, call_next):
    response = await call_next(request)
    # Only log API calls (not static files)
    if request.url.path.startswith("/api/"):
        try:
            await system_logs_collection.insert_one({
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "ip": request.client.host if request.client else "unknown",
                "timestamp": datetime.now(timezone.utc),
            })
        except Exception:
            pass
    return response


# Routers
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


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "Learnova"}


@app.on_event("startup")
async def startup_event():
    try:
        await client.admin.command("ping")
        print("✅ MongoDB connected")
        await token_blocklist_collection.create_index("expireAt", expireAfterSeconds=0)
        print("✅ Token blocklist TTL index ready")
        print("✅ Learnova backend started")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")


# Serve frontend — must be LAST
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

