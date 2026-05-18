from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from backend.database.db import users_collection, token_blocklist_collection
from dotenv import load_dotenv
from typing import Optional
import os

load_dotenv()


# ----------------------------- JWT Configuration -----------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
ALGORITHM = "HS256"

security = HTTPBearer()


# ----------------------------- Auth Helpers -----------------------------
def _unauthorized(detail: str) -> HTTPException:
    """Build a shared 401 error to keep auth guard responses consistent."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
    )


def _forbidden(detail: str) -> HTTPException:
    """Build a shared 403 error for role-based access checks."""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
    )


def _decode_access_token(token: str) -> tuple[str, Optional[str]]:
    """Decode JWT and return the user email plus optional token ID."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise _unauthorized("Invalid or expired token") from exc

    email: Optional[str] = payload.get("email")
    jti: Optional[str] = payload.get("jti")
    if email is None:
        raise _unauthorized("Invalid token")

    return email, jti


async def _ensure_token_is_active(jti: Optional[str]) -> None:
    """Reject tokens that were added to the logout blocklist."""
    if not jti:
        return

    blocked = await token_blocklist_collection.find_one({"jti": jti})
    if blocked:
        raise _unauthorized("Token has been invalidated — please log in again")


def _ensure_role(current_user: dict, allowed_roles: set[str], detail: str) -> None:
    """Check the current user's role against an allowed role set."""
    if current_user.get("role") not in allowed_roles:
        raise _forbidden(detail)


# ----------------------------- Dependency Guards -----------------------------
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Resolve the authenticated user document from the bearer token."""
    token = credentials.credentials
    email, jti = _decode_access_token(token)
    await _ensure_token_is_active(jti)

    user = await users_collection.find_one({"email": email})
    if user is None:
        raise _unauthorized("User not found")

    if user.get("status") == "inactive":
        raise _forbidden("Account is disabled. Contact an administrator.")

    user["id"] = str(user["_id"])
    return user


async def get_admin_user(
    current_user: dict = Depends(get_current_user)
):
    """Allow access to admin and system_admin accounts only."""
    _ensure_role(current_user, {"admin", "system_admin"}, "Admin access required")
    return current_user


async def get_system_admin_user(
    current_user: dict = Depends(get_current_user)
):
    """Allow access to system_admin accounts only."""
    _ensure_role(current_user, {"system_admin"}, "System admin access required")
    return current_user
