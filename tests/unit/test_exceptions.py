"""
Tests for custom exception classes
"""

import pytest
from app.core.exceptions import (
    AppError, DuplicateUserError, UserNotFoundError,
    InvalidCredentialsError, DatabaseError
)


def test_app_error_base_attributes():
    """All AppErrors have status_code and error_type"""
    class TestError(AppError):
        status_code = 400
        error_type = "TEST_ERROR"
    
    error = TestError("test message")
    assert error.status_code == 400
    assert error.error_type == "TEST_ERROR"
    assert error.message == "test message"


def test_duplicate_user_error():
    error = DuplicateUserError("Username already taken")
    assert error.status_code == 409
    assert error.error_type == "DUPLICATE_USER"


def test_invalid_credentials_error():
    error = InvalidCredentialsError("Wrong password")
    assert error.status_code == 401
    assert error.error_type == "INVALID_CREDENTIALS"

