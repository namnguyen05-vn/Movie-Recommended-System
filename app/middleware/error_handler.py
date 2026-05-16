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


def _add_cors_headers(request: Request, response: JSONResponse):
    """Add CORS headers to response for error responses"""
    origin = request.headers.get("origin", "*")
    response.headers["access-control-allow-origin"] = origin if origin != "*" else "*"
    response.headers["access-control-allow-credentials"] = "true"
    response.headers["access-control-allow-methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["access-control-allow-headers"] = "Content-Type, Authorization"


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
    
    response = JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )
    
    # Add CORS headers to ensure frontend can access error responses
    _add_cors_headers(request, response)
    return response


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
    
    response = JSONResponse(
        status_code=500,
        content=error_response.model_dump()
    )
    
    # Add CORS headers to ensure frontend can access error responses
    _add_cors_headers(request, response)
    return response

