"""
Authentication & Authorisation Middleware
==========================================

Provides FastAPI dependency-injection guards that are used by every protected
route in the application.  The module implements a two-tier authorisation model:

- **Authenticated user** (any account with a valid JWT)
- **Admin user** (accounts whose ``role`` is ``"admin"`` or ``"system_admin"``)
- **System admin user** (accounts whose ``role`` is ``"system_admin"`` only)

Token lifecycle
---------------
1. Issued on login (see ``backend.routes.auth``).
2. Decoded and validated on every protected-request via :func:`get_current_user`.
3. Checked against a MongoDB blocklist — tokens that have been logged out
   are rejected even if the JWT itself has not yet expired.
4. Expired or invalid tokens raise ``401 Unauthorized``.

Cross-references
----------------
- :mod:`backend.database.db` — ``users_collection`` for user lookups,
  ``token_blocklist_collection`` for logout revocation.
- :mod:`backend.routes.auth` — Token issuance during login/refresh flows.
- :mod:`backend.main` — The ``log_activity`` middleware logs the resolved
  user email from the JWT for the audit trail.
"""

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

# FastAPI dependency that extracts the ``Authorization: Bearer <token>`` header.
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
    """Decode JWT and return the user email plus optional token ID (``jti``).

    The ``jti`` (JWT ID) is an optional claim used for token-level revocation.
    When present, it is checked against the blocklist in
    :func:`_ensure_token_is_active` so that a logged-out token cannot be reused
    even before its ``exp`` claim fires.

    Parameters
    ----------
    token : str
        The raw JWT string from the ``Authorization`` header (without the
        ``"Bearer "`` prefix).

    Returns
    -------
    tuple[str, Optional[str]]
        ``(email, jti)`` — the user's email and an optional unique token ID.

    Raises
    ------
    HTTPException (401)
        If the token is malformed, expired, signed with the wrong key, or
        lacks the ``email`` claim.
    """
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
    """Reject tokens that were added to the logout blocklist.

    The blocklist collection has a TTL index on ``expireAt`` (created during
    ``startup_event`` in :mod:`backend.main`) so revoked tokens are
    automatically cleaned up once their natural JWT expiry is reached.

    Parameters
    ----------
    jti : str or None
        The JWT ID from the token payload.  If ``None`` (older tokens that
        were issued without a ``jti``), the check is skipped.

    Raises
    ------
    HTTPException (401)
        If the ``jti`` is found in the blocklist.
    """
    if not jti:
        return

    blocked = await token_blocklist_collection.find_one({"jti": jti})
    if blocked:
        raise _unauthorized("Token has been invalidated — please log in again")


def _ensure_role(current_user: dict, allowed_roles: set[str], detail: str) -> None:
    """Check the current user's role against an allowed role set.

    Parameters
    ----------
    current_user : dict
        The MongoDB user document (with an ``"id"`` key added by
        :func:`get_current_user`).
    allowed_roles : set[str]
        The set of role strings that are permitted (e.g. ``{"admin"}``).
    detail : str
        The human-readable message attached to the 403 exception.

    Raises
    ------
    HTTPException (403)
        If ``current_user["role"]`` is not in ``allowed_roles``.
    """
    if current_user.get("role") not in allowed_roles:
        raise _forbidden(detail)


# ----------------------------- Dependency Guards -----------------------------
# FastAPI dependencies used directly by route handlers to protect endpoints.
# Usage:
#   async def delete_user(user: dict = Depends(get_admin_user)): ...
#
# They form a chain: get_admin_user -> get_current_user -> HTTPBearer.


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Resolve the authenticated user document from the bearer token.

    This is the fundamental authentication guard.  Every protected endpoint
    depends on it (either directly or through :func:`get_admin_user` /
    :func:`get_system_admin_user`).

    Flow
    ----
    1. Extract the raw JWT from the ``Authorization: Bearer <token>`` header.
    2. Decode it via :func:`_decode_access_token` to get ``email`` and ``jti``.
    3. Verify the token is not revoked via :func:`_ensure_token_is_active`.
    4. Look up the full user document from ``users_collection`` by email.
    5. Add a string ``"id"`` field (converted from ``ObjectId``) for JSON
       serialisability and return the document.

    Parameters
    ----------
    credentials : HTTPAuthorizationCredentials
        Injected automatically by FastAPI's ``HTTPBearer`` dependency.

    Returns
    -------
    dict
        The full MongoDB user document with an added ``"id"`` key.

    Raises
    ------
    HTTPException (401)
        If the token is missing, invalid, expired, revoked, or the user
        document no longer exists.
    """
    token = credentials.credentials
    email, jti = _decode_access_token(token)
    await _ensure_token_is_active(jti)

    user = await users_collection.find_one({"email": email})
    if user is None:
        raise _unauthorized("User not found")

    if user.get("status") == "inactive":
        raise _forbidden("Account is disabled. Contact an administrator.")

    # Convert the MongoDB ``ObjectId`` to a string so it can be JSON-serialised.
    user["id"] = str(user["_id"])
    return user


async def get_admin_user(
    current_user: dict = Depends(get_current_user)
):
    """Allow access to admin and system_admin accounts only.

    Built on top of :func:`get_current_user` — if the token is valid but
    the user's role is neither ``"admin"`` nor ``"system_admin"``, a 403
    Forbidden response is returned.

    Parameters
    ----------
    current_user : dict
        Injected by :func:`get_current_user`.

    Returns
    -------
    dict
        The user document (same as :func:`get_current_user`).
    """
    _ensure_role(current_user, {"admin", "system_admin"}, "Admin access required")
    return current_user


async def get_system_admin_user(
    current_user: dict = Depends(get_current_user)
):
    """Allow access to system_admin accounts only.

    The most restrictive guard — only users whose ``role`` is exactly
    ``"system_admin"`` pass through.

    Parameters
    ----------
    current_user : dict
        Injected by :func:`get_current_user`.

    Returns
    -------
    dict
        The user document (same as :func:`get_current_user`).
    """
    _ensure_role(current_user, {"system_admin"}, "System admin access required")
    return current_user
