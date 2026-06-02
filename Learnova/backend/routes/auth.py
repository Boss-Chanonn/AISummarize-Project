"""
routes/auth.py — Authentication & User Management
==================================================
Handles registration, login, logout, profile CRUD, and password changes.
Uses JWT (HS256) for token-based auth with bcrypt password hashing.
Token revocation is handled via a MongoDB blocklist collection (JTI tracking).
All protected endpoints depend on `get_current_user` from the auth middleware.
"""

from fastapi import APIRouter, Depends
from backend.models.user import (
    UserCreate, UserLogin, UserUpdate, PasswordChange
)
from backend.database.db import users_collection, token_blocklist_collection
from backend.middleware.auth_middleware import get_current_user, security
from backend.utils.api_errors import message_error
from fastapi.security import HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta, timezone
import os
import uuid

router = APIRouter()

# ── Password hashing (bcrypt) ──────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── JWT configuration ──────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 hours (default)


# ----------------------------- Auth Helpers -----------------------------
def hash_password(password: str) -> str:
    """Hash a plain-text password before saving to database."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Compare a plain-text password with a hashed password."""
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    """
    Create a signed JWT token with expiration and unique token ID (JTI).
    The JTI enables server-side revocation via the blocklist collection —
    see the /logout endpoint which inserts the JTI into token_blocklist_collection.
    """
    payload = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload.update({"exp": expire, "jti": str(uuid.uuid4())})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ----------------------------- Password Reset -----------------------------

# POST /forgot-password — send reset link to email
@router.post("/forgot-password")
async def forgot_password(body: dict):
    """
    POST /forgot-password — send a password reset email.
    Generates a signed JWT (expires in 1 hour), stores it on the user doc,
    and emails the user a reset link containing the token.
    Returns success even if email is unknown (prevents email enumeration).
    """
    email = body.get("email", "").strip().lower()
    if not email:
        return message_error(400, "Email is required")

    user = await users_collection.find_one({"email": email})
    if not user:
        return {"message": "If that email is registered, a reset link has been sent."}

    # Generate short-lived JWT for password reset
    reset_token = create_access_token({
        "sub": email,
        "type": "password_reset",
        "jti": str(uuid.uuid4()),
    })
    # Store token + expiry on the user document
    from datetime import timedelta
    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "reset_token": reset_token,
            "reset_token_expiry": datetime.utcnow() + timedelta(hours=1),
        }}
    )

    # Fire-and-forget reset email
    try:
        from backend.services.email_service import send_reset_password_email
        import asyncio
        asyncio.ensure_future(send_reset_password_email(email, user.get("name", "User"), reset_token))
    except Exception:
        pass

    return {"message": "If that email is registered, a reset link has been sent."}


# POST /reset-password — verify token and update password
@router.post("/reset-password")
async def reset_password(body: dict):
    """
    POST /reset-password — reset password using a valid token.
    Verifies the JWT, checks it matches the stored token on the user doc,
    and hasn't expired. Then hashes the new password and updates the user record.
    The reset_token field is cleared after successful reset (single-use).
    """
    token = body.get("token", "")
    new_password = body.get("new_password", "")
    confirm = body.get("confirm_password", "")

    if not token or not new_password or not confirm:
        return message_error(400, "Token, new password, and confirmation are required")
    if len(new_password) < 8:
        return message_error(400, "Password must be at least 8 characters")
    if new_password != confirm:
        return message_error(400, "Passwords do not match")

    # Decode JWT without verification first to get email
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return message_error(400, "Invalid or expired reset link")

    email = payload.get("sub", "")
    token_type = payload.get("type", "")
    if token_type != "password_reset" or not email:
        return message_error(400, "Invalid reset link")

    # Look up user and verify stored token matches
    user = await users_collection.find_one({"email": email})
    if not user:
        return message_error(400, "Invalid reset link")

    stored_token = user.get("reset_token", "")
    stored_expiry = user.get("reset_token_expiry")

    if stored_token != token:
        return message_error(400, "Reset link has already been used")
    if not stored_expiry or stored_expiry.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return message_error(400, "Reset link has expired — please request a new one")

    # Hash new password and update, clearing the token
    new_hashed = hash_password(new_password)
    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"password": new_hashed}, "$unset": {"reset_token": "", "reset_token_expiry": ""}}
    )

    return {"message": "Password reset successfully — please sign in"}


# ----------------------------- Public Endpoints -----------------------------

# GET /health — lightweight health check for the auth router
@router.get("/health")
async def health_check():
    """Simple endpoint to confirm auth router is alive."""
    return {"status": "ok"}


# POST /register — create a new user account (public, no auth required)
@router.post("/register", status_code=201)
async def register(user: UserCreate):
    """
    POST /register — create a new user account.
    Validates password length and DOB presence, checks for duplicate email,
    hashes the password with bcrypt, inserts into MongoDB, and fires a
    best-effort welcome email. New accounts default to role="user", tier="free".
    """
    if len(user.password) < 8:
        return message_error(400, "Password must be at least 8 characters")
    if not user.dob:
        return message_error(400, "Date of birth is required")
    existing = await users_collection.find_one({"email": user.email})
    if existing:
        return message_error(409, "Email already registered")
    hashed = hash_password(user.password)
    await users_collection.insert_one({
        "name": user.name,
        "email": user.email,
        "password": hashed,
        "dob": user.dob,
        "phone": user.phone or "",
        "role": "user",
        "tier": "free",
        "status": "active",
        "createdAt": datetime.utcnow()
    })
    # ── Fire-and-forget welcome email (silently ignore failures) ──
    try:
        from backend.services.email_service import send_welcome_email
        import asyncio
        asyncio.ensure_future(send_welcome_email(user.email, user.name))
    except Exception:
        pass
    return {"message": "Account created — please sign in"}


# POST /login — authenticate and issue a JWT token
@router.post("/login")
async def login(credentials: UserLogin):
    """
    POST /login — authenticate with email/password.
    On success, returns a signed JWT (expires in ACCESS_TOKEN_EXPIRE_MINUTES)
    plus a user profile payload. The token embeds email, name, role, and user ID.
    """
    user = await users_collection.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password"]):
        return message_error(401, "Invalid email or password")
    # ── Build JWT payload with identity claims ──
    token = create_access_token({
        "email": user["email"],
        "name": user["name"],
        "role": user.get("role", "user"),
        "id": str(user["_id"])
    })
    return {
        "token": token,
        "user": {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "role": user.get("role", "user"),
            "tier": user.get("tier", "free"),
            "dob": user.get("dob", ""),
            "phone": user.get("phone", "")
        }
    }


# ----------------------------- Protected Endpoints -----------------------------
# All endpoints below require a valid JWT via the `get_current_user` dependency.

# POST /logout — invalidate the current JWT by storing its JTI in the blocklist
@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user)
):
    """
    POST /logout — invalidate the current token.
    Decodes the JWT to extract its JTI (unique token ID), then inserts it into
    the MongoDB token_blocklist_collection. The auth middleware checks this
    collection on every protected request, effectively revoking the token.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            expire_at = datetime.fromtimestamp(exp, tz=timezone.utc)
            await token_blocklist_collection.insert_one({"jti": jti, "expireAt": expire_at})
    except Exception:
        pass  # Best-effort: if the token is already malformed, logout is a no-op
    return {"message": "Logged out successfully"}


# GET /profile — fetch the authenticated user's profile (no password returned)
@router.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    """GET /profile — return profile data for the currently authenticated user."""
    return {
        "id": str(current_user["_id"]),
        "name": current_user["name"],
        "email": current_user["email"],
        "role": current_user.get("role", "user"),
        "tier": current_user.get("tier", "free"),
        "dob": current_user.get("dob", ""),
        "phone": current_user.get("phone", "")
    }


# PUT /profile — update allowed profile fields
@router.put("/profile")
async def update_profile(
    update: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    PUT /profile — update editable profile fields.
    Only sends non-None fields to MongoDB (avoids overwriting with empty values).
    Fields that can be updated are defined by the UserUpdate model.
    """
    update_fields = {k: v for k, v in update.dict().items() if v is not None}
    if not update_fields:
        return message_error(400, "No fields to update")
    await users_collection.update_one({"_id": current_user["_id"]}, {"$set": update_fields})
    return {"message": "Profile updated"}


# PUT /password — change password (requires current password verification)
@router.put("/password")
async def change_password(
    body: PasswordChange,
    current_user: dict = Depends(get_current_user)
):
    """
    PUT /password — change password after verifying current credentials.
    Uses bcrypt to hash the new password before persisting to MongoDB.
    """
    if not verify_password(body.current_password, current_user["password"]):
        return message_error(400, "Current password is incorrect")
    new_hashed = hash_password(body.new_password)
    await users_collection.update_one({"_id": current_user["_id"]}, {"$set": {"password": new_hashed}})
    return {"message": "Password changed successfully"}

