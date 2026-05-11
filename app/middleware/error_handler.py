"""
Global error handler middleware.

Catches AppError and other exceptions, formats them as JSON.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from app.core.exceptions import AppError, InternalServerError
from app.schemas.error_schema import ErrorResponse
from datetime import datetime
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def app_error_handler(request: Request, exc: AppError):
    """
    Handle AppError exceptions.
    
    Formats as JSON with error type for frontend to handle.
    """
    logger.warning(
        f"App error: {exc.error_type}",
        extra={
            "error_type": exc.error_type,
            "path": str(request.url.path),
            "method": request.method,
            "message": exc.message
        }
    )
    
    error_response = ErrorResponse(
        error=exc.message,
        type=exc.error_type,
        timestamp=datetime.utcnow()
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


async def generic_error_handler(request: Request, exc: Exception):
    """
    Handle unexpected exceptions.
    
    Logs error and returns generic 500.
    """
    logger.error(
        f"Unhandled exception",
        extra={
            "path": str(request.url.path),
            "method": request.method,
            "error": str(exc)
        },
        exc_info=True
    )
    
    error = InternalServerError("An unexpected error occurred")
    error_response = ErrorResponse(
        error=error.message,
        type=error.error_type,
        timestamp=datetime.utcnow()
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response.model_dump()
    )

