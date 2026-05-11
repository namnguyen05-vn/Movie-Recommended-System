"""
Base schemas used across the API
"""

from pydantic import BaseModel
from typing import Any, Generic, TypeVar

T = TypeVar('T')


class SuccessResponse(BaseModel, Generic[T]):
    """Generic success response wrapper"""
    status: str = "success"
    data: Any


class PaginatedResponse(BaseModel):
    """Paginated list response"""
    status: str = "success"
    data: list
    total: int
    page: int
    page_size: int

