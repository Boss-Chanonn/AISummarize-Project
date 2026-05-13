from fastapi.responses import JSONResponse


def message_error(status_code: int, message: str) -> JSONResponse:
    """Return a consistent JSON error response with a message field."""
    return JSONResponse(status_code=status_code, content={"message": message})
