from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.middleware.security import SecurityHeadersMiddleware
from backend.database.db import client
from dotenv import load_dotenv
import os

load_dotenv()

allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8000"
).split(",")

app = FastAPI(title="Learnova API")

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
from backend.routes.auth import router as auth_router
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])

# Health check
@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "Learnova"}

# Startup
@app.on_event("startup")
async def startup_event():
    try:
        await client.admin.command("ping")
        print("✅ MongoDB connected")
        print("✅ Learnova backend started")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")

# Serve frontend — must be LAST
app.mount(
    "/",
    StaticFiles(directory="frontend", html=True),
    name="frontend"
)

