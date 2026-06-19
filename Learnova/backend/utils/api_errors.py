from fastapi.responses import JSONResponse


def message_error(status_code: int, message: str, code: str | None = None) -> JSONResponse:
    """Return a consistent JSON error response with a message field."""
    content = {"message": message}
    if code:
        content["code"] = code
    return JSONResponse(status_code=status_code, content=content)
