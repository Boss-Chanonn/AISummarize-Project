from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from backend.models.user import (
    UserCreate, UserLogin, UserResponse,
    TokenResponse, UserUpdate, PasswordChange
)
from backend.database.db import users_collection
from backend.middleware.auth_middleware import get_current_user
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from bson import ObjectId
import os

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("JWT_EXPIRE_MINUTES", "60")
)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict) -> str:
    payload = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload.update({"exp": expire})
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

