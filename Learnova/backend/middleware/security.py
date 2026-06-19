from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


def _should_disable_cache(content_type: str) -> bool:
    """Return True for frontend asset types that should always reload fresh."""
    return (
        content_type.startswith("text/html")
        or content_type.startswith("application/javascript")
        or content_type.startswith("text/javascript")
        or content_type.startswith("text/css")
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach baseline browser security headers to every outgoing response."""

    async def dispatch(self, request: Request, call_next):
        """Apply response headers after downstream handlers finish processing."""
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # Prevent browser from caching static files — always fetch fresh copy
        content_type = response.headers.get("content-type", "")
        if _should_disable_cache(content_type):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        return response
