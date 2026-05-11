"""
User service: business logic for user operations.

This is where user-related logic lives, independent of HTTP layer.
Routes call these functions, passing dependencies.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import User
from app.core.security import get_password_hash, verify_password
from app.core.exceptions import DuplicateUserError, InvalidCredentialsError, UserNotFoundError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class UserService:
    """Service for user operations"""
    
    @staticmethod
    async def register_user(
        username: str,
        password: str,
        db: AsyncSession
    ) -> User:
        """
        Register new user.
        
        Args:
            username: User's username
            password: Plain text password (will be hashed)
            db: Database session
            
        Returns:
            Created User object
            
        Raises:
            DuplicateUserError: If username already exists
        """
        logger.info(f"Attempting to register user: {username}")
        
        # Check if user already exists
        result = await db.execute(
            select(User).where(User.username == username)
        )
        existing_user = result.scalars().first()
        
        if existing_user:
            logger.warning(f"Registration failed - duplicate username: {username}")
            raise DuplicateUserError(
                f"Username '{username}' already taken. Please choose another."
            )
        
        # Create new user
        hashed_password = get_password_hash(password)
        user = User(
            username=username,
            password_hash=hashed_password
        )
        
        # Save to database
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"User registered successfully: {username} (ID: {user.userId})")
        return user
    
    @staticmethod
    async def authenticate_user(
        username: str,
        password: str,
        db: AsyncSession
    ) -> User:
        """
        Authenticate user by username and password.
        
        Args:
            username: User's username
            password: Plain text password to verify
            db: Database session
            
        Returns:
            User object if credentials are valid
            
        Raises:
            InvalidCredentialsError: If username not found or password wrong
        """
        logger.info(f"Authentication attempt for user: {username}")
        
        # Find user
        result = await db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalars().first()
        
        # Check user exists and password matches
        if not user or not verify_password(password, user.password_hash):
            logger.warning(f"Authentication failed for user: {username}")
            raise InvalidCredentialsError("Invalid username or password")
        
        logger.info(f"Authentication successful for user: {username}")
        return user
    
    @staticmethod
    async def get_user_by_id(
        user_id: int,
        db: AsyncSession
    ) -> User:
        """
        Get user by ID.
        
        Args:
            user_id: User's ID
            db: Database session
            
        Returns:
            User object
            
        Raises:
            UserNotFoundError: If user doesn't exist
        """
        result = await db.execute(
            select(User).where(User.userId == user_id)
        )
        user = result.scalars().first()
        
        if not user:
            raise UserNotFoundError(f"User with ID {user_id} not found")
        
        return user

