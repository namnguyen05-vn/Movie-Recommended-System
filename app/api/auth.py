"""
Authentication API routes.

Handles user registration and login.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.dependencies import get_db_session
from app.services.user_service import UserService
from app.schemas.user_schema import UserCreate, UserResponse, Token
from app.core.security import create_access_token
from app.core.exceptions import DuplicateUserError, InvalidCredentialsError
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
async def register(
    user: UserCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Register new user.
    
    POST /api/auth/register
    {
        "username": "john_doe",
        "password": "secure_password"
    }
    
    Response: 201 Created
    {
        "userId": 1,
        "username": "john_doe"
    }
    """
    logger.info(f"Register endpoint called for: {user.username}")
    
    result = await UserService.register_user(
        user.username,
        user.password,
        db
    )
    
    return result


@router.post("/login", response_model=Token)
async def login(
    credentials: UserCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Login user.
    
    POST /api/auth/login
    {
        "username": "john_doe",
        "password": "secure_password"
    }
    
    Response: 200 OK
    {
        "access_token": "eyJhbGc...",
        "token_type": "bearer"
    }
    """
    logger.info(f"Login endpoint called for: {credentials.username}")
    
    # Authenticate
    user = await UserService.authenticate_user(
        credentials.username,
        credentials.password,
        db
    )
    
    # Create token
    access_token = create_access_token(data={"sub": str(user.userId)})
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
