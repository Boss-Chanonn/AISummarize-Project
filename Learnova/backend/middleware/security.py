from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # Prevent browser from caching static files — always fetch fresh copy
        content_type = response.headers.get("content-type", "")
        if (content_type.startswith("text/html")
            or content_type.startswith("application/javascript")
            or content_type.startswith("text/javascript")
            or content_type.startswith("text/css")):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        return response
