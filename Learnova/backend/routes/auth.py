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

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 hours


# ----------------------------- Auth Helpers -----------------------------
def hash_password(password: str) -> str:
    """Hash a plain-text password before saving to database."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Compare a plain-text password with a hashed password."""
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    """Create a signed JWT token with expiration and unique token ID."""
    payload = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload.update({"exp": expire, "jti": str(uuid.uuid4())})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ----------------------------- Public Endpoints -----------------------------
@router.get("/health")
async def health_check():
    """Simple endpoint to confirm auth router is alive."""
    return {"status": "ok"}


@router.post("/register", status_code=201)
async def register(user: UserCreate):
    """Create a new user account after validating basic required fields."""
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
    try:
        from backend.services.email_service import send_welcome_email
        import asyncio
        asyncio.ensure_future(send_welcome_email(user.email, user.name))
    except Exception:
        pass  # welcome email is best-effort
    return {"message": "Account created — please sign in"}


@router.post("/login")
async def login(credentials: UserLogin):
    """Authenticate user credentials and return JWT plus profile payload."""
    user = await users_collection.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password"]):
        return message_error(401, "Invalid email or password")
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
@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user)
):
    """Invalidate current token by saving its JTI into blocklist."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            expire_at = datetime.fromtimestamp(exp, tz=timezone.utc)
            await token_blocklist_collection.insert_one({"jti": jti, "expireAt": expire_at})
    except Exception:
        pass
    return {"message": "Logged out successfully"}


@router.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Return profile data for the currently authenticated user."""
    return {
        "id": str(current_user["_id"]),
        "name": current_user["name"],
        "email": current_user["email"],
        "role": current_user.get("role", "user"),
        "tier": current_user.get("tier", "free"),
        "dob": current_user.get("dob", ""),
        "phone": current_user.get("phone", "")
    }


@router.put("/profile")
async def update_profile(
    update: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update editable profile fields for the current user."""
    update_fields = {k: v for k, v in update.dict().items() if v is not None}
    if not update_fields:
        return message_error(400, "No fields to update")
    await users_collection.update_one({"_id": current_user["_id"]}, {"$set": update_fields})
    return {"message": "Profile updated"}


@router.put("/password")
async def change_password(
    body: PasswordChange,
    current_user: dict = Depends(get_current_user)
):
    """Change password after verifying the current password first."""
    if not verify_password(body.current_password, current_user["password"]):
        return message_error(400, "Current password is incorrect")
    new_hashed = hash_password(body.new_password)
    await users_collection.update_one({"_id": current_user["_id"]}, {"$set": {"password": new_hashed}})
    return {"message": "Password changed successfully"}

