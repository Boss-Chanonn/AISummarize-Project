from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from backend.models.user import (
    UserCreate, UserLogin, UserResponse,
    TokenResponse, UserUpdate, PasswordChange
)
from backend.database.db import users_collection, token_blocklist_collection
from backend.middleware.auth_middleware import get_current_user, security
from fastapi.security import HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta, timezone
from bson import ObjectId
import os
import uuid

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 hours

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict) -> str:
    payload = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload.update({"exp": expire, "jti": str(uuid.uuid4())})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

@router.get("/health")
async def health_check():
    return {"status": "ok"}

@router.post("/register", status_code=201)
async def register(user: UserCreate):
    if len(user.password) < 8:
        return JSONResponse(status_code=400, content={"message": "Password must be at least 8 characters"})
    if not user.dob:
        return JSONResponse(status_code=400, content={"message": "Date of birth is required"})
    existing = await users_collection.find_one({"email": user.email})
    if existing:
        return JSONResponse(status_code=409, content={"message": "Email already registered"})
    hashed = hash_password(user.password)
    await users_collection.insert_one({
        "name": user.name,
        "email": user.email,
        "password": hashed,
        "dob": user.dob,
        "phone": user.phone or "",
        "role": "user",
        "tier": "free",
        "createdAt": datetime.utcnow()
    })
    return {"message": "Account created — please sign in"}

@router.post("/login")
async def login(credentials: UserLogin):
    user = await users_collection.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password"]):
        return JSONResponse(status_code=401, content={"message": "Invalid email or password"})
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

@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user)
):
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
    update_fields = {k: v for k, v in update.dict().items() if v is not None}
    if not update_fields:
        return JSONResponse(status_code=400, content={"message": "No fields to update"})
    await users_collection.update_one({"_id": current_user["_id"]}, {"$set": update_fields})
    return {"message": "Profile updated"}

@router.put("/password")
async def change_password(
    body: PasswordChange,
    current_user: dict = Depends(get_current_user)
):
    if not verify_password(body.current_password, current_user["password"]):
        return JSONResponse(status_code=400, content={"message": "Current password is incorrect"})
    new_hashed = hash_password(body.new_password)
    await users_collection.update_one({"_id": current_user["_id"]}, {"$set": {"password": new_hashed}})
    return {"message": "Password changed successfully"}

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict) -> str:
    payload = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload.update({
        "exp": expire,
        "jti": str(uuid.uuid4())  # unique token ID for blocklist
    })
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

@router.get("/health")
async def health_check():
    return {"status": "ok"}

@router.post("/register", status_code=201)
async def register(user: UserCreate):
    if len(user.password) < 8:
        return JSONResponse(
            status_code=400,
            content={"message": "Password must be at least 8 characters"}
        )

    existing = await users_collection.find_one({"email": user.email})
    if existing:
        return JSONResponse(
            status_code=409,
            content={"message": "Email already registered"}
        )

    hashed = hash_password(user.password)

    result = await users_collection.insert_one({
        "name": user.name,
        "email": user.email,
        "password": hashed,
        "role": "user",
        "tier": "free",
        "createdAt": datetime.utcnow()
    })

    return {"message": "Account created — please sign in"}

@router.post("/login")
async def login(credentials: UserLogin):
    user = await users_collection.find_one(
        {"email": credentials.email}
    )

    if not user or not verify_password(
        credentials.password, user["password"]
    ):
        return JSONResponse(
            status_code=401,
            content={"message": "Invalid email or password"}
        )

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
            "tier": user.get("tier", "free")
        }
    }

@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user)
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            expire_at = datetime.fromtimestamp(exp, tz=timezone.utc)
            await token_blocklist_collection.insert_one({
                "jti": jti,
                "expireAt": expire_at
            })
    except Exception:
        pass  # token already invalid — logout succeeds anyway
    return {"message": "Logged out successfully"}

@router.get("/profile")
async def get_profile(
    current_user: dict = Depends(get_current_user)
):
    return {
        "id": str(current_user["_id"]),
        "name": current_user["name"],
        "email": current_user["email"],
        "role": current_user.get("role", "user"),
        "tier": current_user.get("tier", "free")
    }

