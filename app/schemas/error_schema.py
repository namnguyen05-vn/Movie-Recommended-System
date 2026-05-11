"""
Error response schemas for consistent API error format
"""

from pydantic import BaseModel
from datetime import datetime


class ErrorResponse(BaseModel):
    """
    Standard error response format
    
    Example:
    {
        "error": "Username already taken",
        "type": "DUPLICATE_USER",
        "timestamp": "2026-05-11T10:30:00Z"
    }
    """
    error: str
    type: str
    timestamp: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Username already taken",
                "type": "DUPLICATE_USER",
                "timestamp": "2026-05-11T10:30:00Z"
            }
        }

