"""
Tests for user service business logic
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.user_service import UserService
from app.core.exceptions import DuplicateUserError, InvalidCredentialsError
from app.db.models import User


@pytest.mark.asyncio
async def test_register_user_success():
    """register_user should create and return new user"""
    # Setup mock DB
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute.return_value.scalars.return_value.first.return_value = None  # No duplicate
    
    # Execute
    result = await UserService.register_user("john_doe", "password123", mock_db)
    
    # Verify
    assert result.username == "john_doe"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_register_user_raises_on_duplicate():
    """register_user should raise DuplicateUserError if user exists"""
    # Setup - mock existing user
    mock_db = AsyncMock(spec=AsyncSession)
    existing_user = MagicMock(spec=User)
    existing_user.username = "john_doe"
    mock_db.execute.return_value.scalars.return_value.first.return_value = existing_user
    
    # Execute & Verify
    with pytest.raises(DuplicateUserError):
        await UserService.register_user("john_doe", "password123", mock_db)


@pytest.mark.asyncio
async def test_authenticate_user_success():
    """authenticate_user should return user on valid credentials"""
    from app.core.security import get_password_hash
    
    hashed = get_password_hash("correct_password")
    mock_user = MagicMock(spec=User)
    mock_user.username = "john_doe"
    mock_user.password_hash = hashed
    
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute.return_value.scalars.return_value.first.return_value = mock_user
    
    # Execute
    result = await UserService.authenticate_user("john_doe", "correct_password", mock_db)
    
    # Verify
    assert result.username == "john_doe"


@pytest.mark.asyncio
async def test_authenticate_user_fails_on_wrong_password():
    """authenticate_user should raise error on wrong password"""
    from app.core.security import get_password_hash
    
    hashed = get_password_hash("correct_password")
    mock_user = MagicMock(spec=User)
    mock_user.password_hash = hashed
    
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute.return_value.scalars.return_value.first.return_value = mock_user
    
    # Execute & Verify
    with pytest.raises(InvalidCredentialsError):
        await UserService.authenticate_user("john_doe", "wrong_password", mock_db)

