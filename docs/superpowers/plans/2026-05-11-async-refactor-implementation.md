# Complete Async Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform Movie Recommender API from sync/monolithic to async/layered architecture for improved maintainability

**Architecture:** 
- Routes become thin HTTP handlers → delegate to services
- Services contain business logic → test independently
- DB operations fully async (SQLAlchemy async)
- ML service lazy-loads on first use → non-blocking startup
- Centralized error handling + logging → consistent API responses

**Tech Stack:** 
- FastAPI (async routing)
- SQLAlchemy 2.0 async (aiomysql driver)
- Pydantic v2 (validation)
- Python 3.10+ (asyncio)
- pytest-asyncio (testing)

**Timeline:** ~8 phases, estimated 3-4 days focused work

---

## 📋 File Structure Reference

**Files to Create (15 new files):**
```
app/core/exceptions.py              # Custom exception classes
app/core/constants.py               # Magic strings, enums
app/db/dependencies.py              # Async session + ML service dependency
app/middleware/error_handler.py     # Global error handling
app/middleware/logging_middleware.py # Request/response logging
app/middleware/__init__.py
app/schemas/base_schema.py          # Base response schemas
app/schemas/error_schema.py         # Error response format
app/services/user_service.py        # User business logic
app/services/movie_service.py       # Movie business logic
app/services/recommendation_service.py # Recommendation logic
app/utils/logger.py                 # Logging configuration
app/utils/validators.py             # Reusable validators
app/utils/decorators.py             # Caching, retry logic
app/api/health.py                   # Health check endpoints
tests/unit/test_user_service.py
tests/unit/test_ml_service.py
requirements.txt                    # Updated dependencies
```

**Files to Modify (7 existing files):**
```
app/core/config.py                  # Add ASYNC_DATABASE_URL
app/db/database.py                  # Async engine setup
app/db/models.py                    # No logic changes, minor cleanup
app/services/ml_service.py          # Lazy loading + async wrapper
app/api/auth.py                     # Convert to async routes + use services
app/api/movies.py                   # Convert to async routes + use services
app/api/recommend.py                # Convert to async routes + use services
app/main.py                         # Lifespan event + middleware setup
```

---

## Phase 1: Foundation - Exception & Logging System

### Task 1.1: Create Custom Exception Classes

**Files:**
- Create: `app/core/exceptions.py`
- Test: `tests/unit/test_exceptions.py`

- [ ] **Step 1: Write test for exception hierarchy**

```python
# tests/unit/test_exceptions.py
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd E:\TTCS\ Project
pytest tests/unit/test_exceptions.py -v
```

Expected: FAIL - `app.core.exceptions` module doesn't exist

- [ ] **Step 3: Create exception classes**

```python
# app/core/exceptions.py
"""
Custom exception classes for the application.

All exceptions inherit from AppError, which provides:
- status_code: HTTP status code
- error_type: Machine-readable error type for frontend
- message: Human-readable error message
"""

class AppError(Exception):
    """
    Base application error class.
    
    All app-specific exceptions inherit from this.
    Middleware catches AppError and formats it as JSON.
    """
    status_code: int = 400
    error_type: str = "UNKNOWN_ERROR"
    message: str = ""
    
    def __init__(self, message: str = ""):
        self.message = message or self.__class__.message
        super().__init__(self.message)


# Authentication & User Errors
class DuplicateUserError(AppError):
    """User already exists"""
    status_code = 409
    error_type = "DUPLICATE_USER"


class UserNotFoundError(AppError):
    """User does not exist"""
    status_code = 404
    error_type = "USER_NOT_FOUND"


class InvalidCredentialsError(AppError):
    """Username or password incorrect"""
    status_code = 401
    error_type = "INVALID_CREDENTIALS"


# Token & Security Errors
class InvalidTokenError(AppError):
    """JWT token invalid or expired"""
    status_code = 401
    error_type = "INVALID_TOKEN"


class TokenExpiredError(AppError):
    """JWT token has expired"""
    status_code = 401
    error_type = "TOKEN_EXPIRED"


# Movie & Recommendation Errors
class MovieNotFoundError(AppError):
    """Movie does not exist"""
    status_code = 404
    error_type = "MOVIE_NOT_FOUND"


class RecommendationError(AppError):
    """Error generating recommendations"""
    status_code = 500
    error_type = "RECOMMENDATION_FAILED"


class MLServiceUnavailableError(AppError):
    """ML model not loaded"""
    status_code = 503
    error_type = "ML_SERVICE_UNAVAILABLE"


# Database Errors
class DatabaseError(AppError):
    """Database operation failed"""
    status_code = 500
    error_type = "DATABASE_ERROR"


class DatabaseConnectError(DatabaseError):
    """Cannot connect to database"""
    error_type = "DATABASE_CONNECT_ERROR"


# Validation Errors
class ValidationError(AppError):
    """Input validation failed"""
    status_code = 422
    error_type = "VALIDATION_ERROR"


# Generic Server Error
class InternalServerError(AppError):
    """Unexpected server error"""
    status_code = 500
    error_type = "INTERNAL_SERVER_ERROR"
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_exceptions.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/core/exceptions.py tests/unit/test_exceptions.py
git commit -m "feat: add custom exception classes"
```

---

### Task 1.2: Create Logging Configuration

**Files:**
- Create: `app/utils/logger.py`
- Test: `tests/unit/test_logger.py`

- [ ] **Step 1: Write test for logger setup**

```python
# tests/unit/test_logger.py
import logging
from app.utils.logger import get_logger

def test_get_logger_returns_logger():
    """get_logger should return a logger instance"""
    logger = get_logger(__name__)
    assert isinstance(logger, logging.Logger)
    assert logger.name == __name__

def test_logger_has_json_formatter():
    """Logger should have JSON formatter for structured logging"""
    logger = get_logger("test_module")
    # At least one handler should exist
    assert len(logger.handlers) > 0 or len(logging.root.handlers) > 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_logger.py -v
```

Expected: FAIL - `app.utils.logger` module doesn't exist

- [ ] **Step 3: Create logger configuration**

```python
# app/utils/logger.py
"""
Structured logging configuration.

Uses JSON formatter for structured logs that can be parsed
by log aggregation systems (ELK, DataDog, etc).

Usage:
    logger = get_logger(__name__)
    logger.info("User registered", extra={"user_id": 123, "username": "john"})
    
Output:
    {"message": "User registered", "user_id": 123, "username": "john", ...}
"""

import logging
import json
from typing import Optional

# Try to use python-json-logger if available, fallback to standard formatter
try:
    from pythonjsonlogger import jsonlogger
    HAS_JSON_LOGGER = True
except ImportError:
    HAS_JSON_LOGGER = False


class JSONFormatter(logging.Formatter):
    """
    Fallback JSON formatter if python-json-logger not available
    """
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Include extra fields
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in ("name", "msg", "args", "created", "filename", 
                              "funcName", "levelname", "levelno", "lineno",
                              "module", "msecs", "message", "pathname", "process",
                              "processName", "relativeCreated", "thread", "threadName"):
                    log_obj[key] = value
        
        return json.dumps(log_obj)


def setup_logging(level: str = "INFO") -> None:
    """
    Configure root logger with JSON formatter
    
    Call once at app startup
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Use python-json-logger if available, else fallback
    if HAS_JSON_LOGGER:
        formatter = jsonlogger.JsonFormatter(
            fmt='%(timestamp)s %(level)s %(name)s %(message)s'
        )
    else:
        formatter = JSONFormatter()
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get logger instance for a module
    
    Usage in any module:
        logger = get_logger(__name__)
        logger.info("Something happened", extra={"user_id": 123})
    
    Args:
        name: __name__ of calling module
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
```

- [ ] **Step 4: Make utils package importable**

```python
# app/utils/__init__.py
from app.utils.logger import get_logger, setup_logging

__all__ = ["get_logger", "setup_logging"]
```

- [ ] **Step 5: Run test to verify it passes**

```bash
pytest tests/unit/test_logger.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/utils/logger.py app/utils/__init__.py tests/unit/test_logger.py
git commit -m "feat: add structured logging configuration"
```

---

### Task 1.3: Create Error Response Schema

**Files:**
- Create: `app/schemas/error_schema.py`
- Create: `app/schemas/base_schema.py`

- [ ] **Step 1: Create error schemas**

```python
# app/schemas/error_schema.py
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
```

- [ ] **Step 2: Create base schemas**

```python
# app/schemas/base_schema.py
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
```

- [ ] **Step 3: Make schemas package full**

```python
# app/schemas/__init__.py
from app.schemas.error_schema import ErrorResponse
from app.schemas.base_schema import SuccessResponse, PaginatedResponse

__all__ = ["ErrorResponse", "SuccessResponse", "PaginatedResponse"]
```

- [ ] **Step 4: Commit**

```bash
git add app/schemas/error_schema.py app/schemas/base_schema.py app/schemas/__init__.py
git commit -m "feat: add error and base response schemas"
```

---

## Phase 2: Async Database Infrastructure

### Task 2.1: Update Configuration with Async Database URL

**Files:**
- Modify: `app/core/config.py`

- [ ] **Step 1: Read current config.py**

```bash
type "E:\TTCS Project\app\core\config.py"
```

- [ ] **Step 2: Update config to add ASYNC_DATABASE_URL**

Replace the entire DatabaseURL section:

```python
# app/core/config.py
import urllib.parse
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    SECRET_KEY: str

    class Config:
        env_file = ".env"

    # Synchronous database URL (for migration scripts, legacy code)
    @property
    def DATABASE_URL(self) -> str:
        """MySQL URL with pymysql (synchronous driver)"""
        encoded_password = urllib.parse.quote_plus(self.DB_PASSWORD)
        return f"mysql+pymysql://{self.DB_USER}:{encoded_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    # Asynchronous database URL (for FastAPI)
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """MySQL URL with aiomysql (async driver)"""
        encoded_password = urllib.parse.quote_plus(self.DB_PASSWORD)
        return f"mysql+aiomysql://{self.DB_USER}:{encoded_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
    
    # Feature flags
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

# Global settings instance
settings = Settings()
```

- [ ] **Step 3: Verify syntax is correct**

```bash
cd "E:\TTCS Project"
python -c "from app.core.config import settings; print(settings.ASYNC_DATABASE_URL)"
```

Expected: Connection string starting with `mysql+aiomysql://`

- [ ] **Step 4: Commit**

```bash
git add app/core/config.py
git commit -m "feat: add ASYNC_DATABASE_URL to config"
```

---

### Task 2.2: Convert Database Layer to Async

**Files:**
- Modify: `app/db/database.py`
- Create: `app/db/dependencies.py`

- [ ] **Step 1: Write test for async database setup**

```python
# tests/unit/test_database.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import engine, AsyncSessionLocal

@pytest.mark.asyncio
async def test_async_engine_created():
    """Engine should be created with async URL"""
    assert engine is not None
    # Check it's async engine (has _echo, echo_pool params)
    assert hasattr(engine.sync_engine, "url")

@pytest.mark.asyncio
async def test_async_session_can_be_created():
    """Should be able to create async session"""
    async with AsyncSessionLocal() as session:
        assert isinstance(session, AsyncSession)

@pytest.mark.asyncio
async def test_get_db_session_dependency():
    """DB dependency should yield session and close it"""
    from app.db.dependencies import get_db_session
    
    session_gen = get_db_session()
    session = await session_gen.__anext__()
    assert isinstance(session, AsyncSession)
    
    try:
        await session_gen.__anext__()
    except StopAsyncIteration:
        pass  # Expected - generator exhausted
```

- [ ] **Step 2: Replace database.py with async setup**

```python
# app/db/database.py
"""
Async database engine and session configuration.

Uses SQLAlchemy 2.0+ async features with aiomysql driver.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Create async engine
engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=settings.DEBUG,
    # Connection pool settings tuned for async workload
    pool_size=20,              # Number of connections to keep in pool
    max_overflow=10,           # Additional connections beyond pool_size
    pool_pre_ping=True,        # Test connection before using (prevents timeout errors)
    connect_args={
        "timeout": 10,         # Connection timeout in seconds
        "check_same_thread": False,
    }
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,    # Don't expire objects after commit
    autoflush=False,           # Explicit flush control
)

# For backward compatibility, also export the Base class
from sqlalchemy.orm import declarative_base
Base = declarative_base()

logger.info("📦 Async database engine configured")
```

- [ ] **Step 3: Create the dependencies module**

```python
# app/db/dependencies.py
"""
Dependency injection for database and services.

These functions are used with FastAPI's Depends() to inject
dependencies into route handlers.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import AsyncSessionLocal
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency: provides async database session
    
    Usage:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db_session)):
            return await db.execute(select(User))
    
    Lifecycle:
    - yield: Session is provided to route handler
    - finally: Session is closed (connection returned to pool)
    - On exception: Auto rollback before closing
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            # Rollback on any exception during request
            await session.rollback()
            logger.error("Database error, rolling back transaction")
            raise
        finally:
            # Always close session
            await session.close()
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/unit/test_database.py -v
```

Expected: PASS (or partial pass if async test runner not configured)

- [ ] **Step 5: Commit**

```bash
git add app/db/database.py app/db/dependencies.py tests/unit/test_database.py
git commit -m "feat: convert database to async with aiomysql"
```

---

## Phase 3: Service Layer Implementation

### Task 3.1: Create User Service

**Files:**
- Create: `app/services/user_service.py`
- Create: `tests/unit/test_user_service.py`

- [ ] **Step 1: Write tests for user service**

```python
# tests/unit/test_user_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.user_service import UserService
from app.core.exceptions import DuplicateUserError, InvalidCredentialsError
from app.db.models import User


@pytest.mark.asyncio
async def test_register_user_creates_user():
    """register_user should create and return new user"""
    # Setup
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
    # Setup
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
    # Setup
    from app.core.security import get_password_hash
    hashed = get_password_hash("correct_password")
    
    mock_user = MagicMock(spec=User)
    mock_user.password_hash = hashed
    
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute.return_value.scalars.return_value.first.return_value = mock_user
    
    # Execute & Verify
    with pytest.raises(InvalidCredentialsError):
        await UserService.authenticate_user("john_doe", "wrong_password", mock_db)
```

- [ ] **Step 2: Create user service**

```python
# app/services/user_service.py
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
```

- [ ] **Step 3: Update security.py with password utilities (if needed)**

Verify that `get_password_hash` and `verify_password` exist in `app/core/security.py`. If they don't, add them:

```python
# In app/core/security.py (add if missing)
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Hash password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify hashed password"""
    return pwd_context.verify(plain_password, hashed_password)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/unit/test_user_service.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/user_service.py tests/unit/test_user_service.py
git commit -m "feat: create user service with business logic"
```

---

### Task 3.2: Create Movie Service

**Files:**
- Create: `app/services/movie_service.py`
- Create: `tests/unit/test_movie_service.py`

- [ ] **Step 1: Write tests for movie service**

```python
# tests/unit/test_movie_service.py
import pytest
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.movie_service import MovieService
from app.core.exceptions import MovieNotFoundError


@pytest.mark.asyncio
async def test_get_all_movies():
    """get_all_movies should return list of movies"""
    from app.db.models import Movie
    
    mock_movie = AsyncMock()
    mock_movie.movieId = 1
    mock_movie.title = "Test Movie"
    
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute.return_value.scalars.return_value.all.return_value = [mock_movie]
    
    result = await MovieService.get_all_movies(db=mock_db)
    
    assert len(result) == 1
    assert result[0].movieId == 1


@pytest.mark.asyncio
async def test_get_movie_by_id_success():
    """get_movie_by_id should return movie"""
    from app.db.models import Movie
    
    mock_movie = AsyncMock()
    mock_movie.movieId = 1
    mock_movie.title = "Test Movie"
    
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute.return_value.scalars.return_value.first.return_value = mock_movie
    
    result = await MovieService.get_movie_by_id(1, db=mock_db)
    
    assert result.movieId == 1


@pytest.mark.asyncio
async def test_get_movie_by_id_not_found():
    """get_movie_by_id should raise error for non-existent movie"""
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute.return_value.scalars.return_value.first.return_value = None
    
    with pytest.raises(MovieNotFoundError):
        await MovieService.get_movie_by_id(999, db=mock_db)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_movie_service.py -v
```

Expected: FAIL - module doesn't exist

- [ ] **Step 3: Create movie service**

```python
# app/services/movie_service.py
"""
Movie service: business logic for movie operations.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Movie
from app.core.exceptions import MovieNotFoundError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MovieService:
    """Service for movie operations"""
    
    @staticmethod
    async def get_all_movies(
        db: AsyncSession,
        limit: int = 100,
        offset: int = 0
    ) -> list[Movie]:
        """
        Get all movies with pagination.
        
        Args:
            db: Database session
            limit: Maximum movies to return
            offset: Pagination offset
            
        Returns:
            List of Movie objects
        """
        logger.debug(f"Fetching movies: limit={limit}, offset={offset}")
        
        result = await db.execute(
            select(Movie)
            .limit(limit)
            .offset(offset)
        )
        movies = result.scalars().all()
        
        logger.debug(f"Found {len(movies)} movies")
        return movies
    
    @staticmethod
    async def get_movie_by_id(
        movie_id: int,
        db: AsyncSession
    ) -> Movie:
        """
        Get movie by ID.
        
        Args:
            movie_id: Movie's ID
            db: Database session
            
        Returns:
            Movie object
            
        Raises:
            MovieNotFoundError: If movie doesn't exist
        """
        logger.debug(f"Fetching movie: {movie_id}")
        
        result = await db.execute(
            select(Movie).where(Movie.movieId == movie_id)
        )
        movie = result.scalars().first()
        
        if not movie:
            logger.warning(f"Movie not found: {movie_id}")
            raise MovieNotFoundError(f"Movie with ID {movie_id} not found")
        
        logger.debug(f"Found movie: {movie.title}")
        return movie
    
    @staticmethod
    async def search_movies(
        query: str,
        db: AsyncSession,
        limit: int = 20
    ) -> list[Movie]:
        """
        Search movies by title.
        
        Args:
            query: Search query string
            db: Database session
            limit: Maximum results
            
        Returns:
            List of matching Movie objects
        """
        logger.debug(f"Searching movies: query='{query}'")
        
        result = await db.execute(
            select(Movie)
            .where(Movie.title.ilike(f"%{query}%"))
            .limit(limit)
        )
        movies = result.scalars().all()
        
        logger.debug(f"Found {len(movies)} movies matching '{query}'")
        return movies
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/unit/test_movie_service.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/movie_service.py tests/unit/test_movie_service.py
git commit -m "feat: create movie service"
```

---

### Task 3.3: Create Recommendation Service

**Files:**
- Create: `app/services/recommendation_service.py`

- [ ] **Step 1: Create recommendation service**

```python
# app/services/recommendation_service.py
"""
Recommendation service: business logic for recommendations.

Orchestrates between ML service and database.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Rating, Movie
from app.services.ml_service import MLService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RecommendationService:
    """Service for recommendation operations"""
    
    @staticmethod
    async def get_recommendations_for_user(
        user_id: int,
        db: AsyncSession,
        limit: int = 10
    ) -> dict:
        """
        Get personalized recommendations for user.
        
        Args:
            user_id: User's ID
            db: Database session
            limit: Maximum recommendations to return
            
        Returns:
            {
                "is_new_user": bool,
                "recommendations": [...],
                "history": [...]
            }
        """
        logger.info(f"Getting recommendations for user: {user_id}")
        
        try:
            # Get ML service (lazy-loads if needed)
            ml_service = await MLService.get_instance()
            
            # Get recommendations async (runs in thread pool)
            recommendations = await ml_service.get_recommendations(user_id)
            
            # Limit results
            if "recommendations" in recommendations:
                recommendations["recommendations"] = recommendations["recommendations"][:limit]
            
            logger.info(f"Generated {len(recommendations.get('recommendations', []))} recommendations for user {user_id}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting recommendations for user {user_id}: {e}")
            # Return trending as fallback
            return {
                "is_new_user": True,
                "recommendations": await RecommendationService._get_trending_movies(db),
                "history": []
            }
    
    @staticmethod
    async def rate_movie(
        user_id: int,
        movie_id: int,
        rating: float,
        db: AsyncSession
    ) -> Rating:
        """
        Record user's rating for a movie.
        
        Args:
            user_id: User's ID
            movie_id: Movie's ID
            rating: Rating value (typically 0-5)
            db: Database session
            
        Returns:
            Rating object
        """
        logger.info(f"Recording rating: user={user_id}, movie={movie_id}, rating={rating}")
        
        # Check if this rating already exists
        result = await db.execute(
            select(Rating).where(
                (Rating.userId == user_id) &
                (Rating.movieId == movie_id)
            )
        )
        existing_rating = result.scalars().first()
        
        if existing_rating:
            # Update existing rating
            existing_rating.rating = rating
            logger.debug(f"Updated existing rating for user {user_id}")
        else:
            # Create new rating
            new_rating = Rating(
                userId=user_id,
                movieId=movie_id,
                rating=rating
            )
            db.add(new_rating)
            logger.debug(f"Created new rating for user {user_id}")
        
        await db.commit()
        logger.info(f"Rating saved successfully")
        
        return existing_rating if existing_rating else new_rating
    
    @staticmethod
    async def _get_trending_movies(
        db: AsyncSession,
        limit: int = 10
    ) -> list[dict]:
        """
        Get trending movies as fallback.
        
        Args:
            db: Database session
            limit: Maximum movies
            
        Returns:
            List of movie dicts
        """
        logger.debug("Fetching trending movies as fallback")
        
        result = await db.execute(
            select(Movie).limit(limit)
        )
        movies = result.scalars().all()
        
        return [
            {
                "movieId": m.movieId,
                "title": m.title,
                "genres": m.genres,
                "poster_url": m.poster_url,
                "description": m.description,
                "predicted_rating": 4.0
            }
            for m in movies
        ]
```

- [ ] **Step 2: Commit**

```bash
git add app/services/recommendation_service.py
git commit -m "feat: create recommendation service"
```

---

## Phase 4: ML Service Refactor

### Task 4.1: Refactor ML Service with Lazy Loading

**Files:**
- Modify: `app/services/ml_service.py`
- Create: `tests/unit/test_ml_service.py`

- [ ] **Step 1: Backup current ml_service.py**

```bash
copy "E:\TTCS Project\app\services\ml_service.py" "E:\TTCS Project\app\services\ml_service.py.bak"
```

- [ ] **Step 2: Write tests for lazy loading**

```python
# tests/unit/test_ml_service.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.ml_service import MLService


@pytest.mark.asyncio
async def test_ml_service_singleton():
    """get_instance should return same instance"""
    instance1 = await MLService.get_instance()
    instance2 = await MLService.get_instance()
    assert instance1 is instance2


@pytest.mark.asyncio
async def test_ml_service_lazy_loading():
    """First call to get_instance should initialize"""
    # Reset singleton
    MLService._instance = None
    MLService._is_initialized = False
    
    with patch('app.services.ml_service.logger'):
        instance = await MLService.get_instance()
        assert instance is not None
        assert MLService._is_initialized or instance.model is None  # Either loaded or degraded


@pytest.mark.asyncio
async def test_get_recommendations_returns_dict():
    """get_recommendations should return dict with recommendations"""
    service = MLService()
    service._is_initialized = True
    service.model = None  # Simulate degraded mode
    service.trending_list = [
        {"movieId": 1, "title": "Test", "predicted_rating": 4.5}
    ]
    
    result = await service.get_recommendations(1)
    
    assert isinstance(result, dict)
    assert "recommendations" in result
    assert "is_new_user" in result
```

- [ ] **Step 3: Replace ml_service.py with lazy loading version**

```python
# app/services/ml_service.py
"""
ML Service: Movie recommendation model.

Uses lazy loading to prevent blocking server startup.
Model loads on first request, subsequent requests reuse instance.
"""

import asyncio
import logging
from typing import Optional
import pandas as pd
import numpy as np
from tensorflow.keras.models import load_model
from sklearn.preprocessing import LabelEncoder
from app.db.database import engine

logger = logging.getLogger(__name__)


class MLService:
    """
    Singleton ML Service with lazy loading.
    
    First call to get_instance() loads the model.
    Subsequent calls return the loaded instance.
    If model fails to load, graceful degradation returns trending only.
    """
    
    _instance: Optional['MLService'] = None
    _lock = asyncio.Lock()
    _is_initialized = False
    
    def __init__(self):
        """Initialize but don't load model yet"""
        self.model = None
        self.movies_df = None
        self.ratings_df = None
        self.user_enc = None
        self.movie_enc = None
        self.trending_list = None
        logger.info("🔧 MLService instance created (not initialized)")
    
    @classmethod
    async def get_instance(cls) -> 'MLService':
        """
        Get or create ML service instance (thread-safe singleton).
        
        First call: Creates instance and initializes (loads model)
        Subsequent calls: Returns existing instance
        
        Returns:
            MLService instance (initialized or degraded mode)
        """
        if cls._instance is None:
            async with cls._lock:  # Ensure only one init
                if cls._instance is None:
                    logger.info("📦 Instantiating MLService...")
                    cls._instance = cls()
                    await cls._instance._initialize()
        
        return cls._instance
    
    async def _initialize(self):
        """
        Load model and prepare data (async).
        
        Runs once on first request. If fails, sets degraded mode.
        """
        try:
            logger.info("🤖 Loading ML model and data...")
            
            # 1. Load data from database
            logger.info("📊 Loading data from database...")
            self.movies_df = pd.read_sql(
                'SELECT * FROM movies', 
                con=engine
            )
            self.ratings_df = pd.read_sql(
                'SELECT * FROM ratings', 
                con=engine
            )
            logger.info(f"  ✓ Loaded {len(self.movies_df)} movies, {len(self.ratings_df)} ratings")
            
            # 2. Load keras model (blocking I/O - run in thread pool)
            logger.info("🧠 Loading Keras model from disk...")
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None,
                load_model,
                'ml_models/movie_recommender_model.keras'
            )
            logger.info("  ✓ Model loaded successfully")
            
            # 3. Prepare label encoders
            logger.info("🔤 Preparing label encoders...")
            self.user_enc = LabelEncoder()
            self.movie_enc = LabelEncoder()
            self.user_enc.fit(self.ratings_df['userId'])
            self.movie_enc.fit(self.ratings_df['movieId'])
            logger.info("  ✓ Encoders ready")
            
            # 4. Prepare trending movies
            logger.info("📈 Calculating trending movies...")
            self._prepare_trending_movies()
            logger.info("  ✓ Trending list ready")
            
            MLService._is_initialized = True
            logger.info("✅ ML Service fully initialized!")
            
        except FileNotFoundError as e:
            logger.error(f"❌ Model file not found: {e}")
            logger.warning("⚠️  ML Service degraded mode: returning trending only")
            self._setup_degraded_mode()
        except Exception as e:
            logger.error(f"❌ Error initializing ML Service: {e}", exc_info=True)
            self._setup_degraded_mode()
    
    def _setup_degraded_mode(self):
        """Setup degraded mode when model fails to load"""
        self.model = None
        self.trending_list = []  # Will be populated from DB on first request
        logger.info("🔧 MLService in degraded mode - model unavailable")
    
    def _prepare_trending_movies(self):
        """
        Calculate trending movies based on rating count and mean.
        
        Trending = highly rated (mean > 4.0) + popular (count >= 50)
        """
        if self.ratings_df is None or self.movies_df is None:
            self.trending_list = []
            return
        
        movie_stats = self.ratings_df.groupby('movieId').agg(
            rating_count=('rating', 'count'),
            rating_mean=('rating', 'mean')
        ).reset_index()
        
        # Filter: at least 50 ratings, sorted by mean rating
        popular = movie_stats[
            movie_stats['rating_count'] >= 50
        ].sort_values(
            by='rating_mean', 
            ascending=False
        ).head(10)  # Top 10
        
        if len(popular) > 0:
            popular_details = pd.merge(
                popular, 
                self.movies_df, 
                on='movieId'
            )
            
            self.trending_list = popular_details[[
                'movieId', 'title', 'genres', 'rating_mean', 'poster_url', 'description'
            ]].fillna("").rename(
                columns={'rating_mean': 'predicted_rating'}
            ).to_dict(orient='records')
        else:
            self.trending_list = []
        
        logger.debug(f"Trending: {len(self.trending_list)} movies")
    
    async def get_recommendations(self, user_id: int) -> dict:
        """
        Get movie recommendations for user (async wrapper).
        
        Args:
            user_id: User's ID
            
        Returns:
            {
                "is_new_user": bool,
                "recommendations": [{movieId, title, genres, predicted_rating, ...}],
                "history": []
            }
        """
        # If model not initialized
        if self.model is None or not self._is_initialized:
            logger.warning(f"⚠️  Model unavailable for user {user_id}, returning trending")
            return {
                "is_new_user": True,
                "recommendations": self.trending_list or [],
                "history": [],
                "warning": "ML model temporarily unavailable, showing trending movies"
            }
        
        # New user (ID outside train set)
        if user_id > 610:  # Assuming training data has max user ID of 610
            return {
                "is_new_user": True,
                "recommendations": self.trending_list or [],
                "history": []
            }
        
        try:
            # Run inference in thread pool (it's CPU-intensive)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._get_recommendations_sync,
                user_id
            )
            return result
        except Exception as e:
            logger.error(f"❌ Recommendation error for user {user_id}: {e}", exc_info=True)
            # Graceful fallback
            return {
                "is_new_user": True,
                "recommendations": self.trending_list or [],
                "history": [],
                "error": "Failed to generate personalized recommendations"
            }
    
    def _get_recommendations_sync(self, user_id: int) -> dict:
        """Synchronous recommendation logic (runs in thread pool)"""
        watched_ids = self.ratings_df[
            self.ratings_df['userId'] == user_id
        ]['movieId'].tolist()
        
        all_movie_ids = self.movies_df['movieId'].unique()
        
        # Only recommend unwatched movies that model knows about
        unwatched = [
            m for m in all_movie_ids 
            if m not in watched_ids and m in self.movie_enc.classes_
        ]
        
        if not unwatched:
            return {
                "is_new_user": False,
                "recommendations": self.trending_list or [],
                "history": watched_ids
            }
        
        # Encode and predict
        user_encoded = self.user_enc.transform([user_id])[0]
        user_input = np.array([user_encoded] * len(unwatched))
        movie_input = self.movie_enc.transform(unwatched)
        
        predictions = self.model.predict(
            [user_input, movie_input], 
            verbose=0
        ).flatten()
        
        # Get top 5
        rec_df = pd.DataFrame({
            'movieId': unwatched, 
            'predicted_rating': predictions
        })
        
        top_5 = pd.merge(
            rec_df.sort_values(
                by='predicted_rating', 
                ascending=False
            ).head(5),
            self.movies_df,
            on='movieId'
        )
        
        return {
            "is_new_user": False,
            "recommendations": top_5[[
                'movieId', 'title', 'genres', 'predicted_rating', 'poster_url', 'description'
            ]].fillna("").to_dict(orient='records'),
            "history": watched_ids
        }
    
    async def reload_model(self):
        """Reload model (for admin endpoint)"""
        logger.info("🔄 Reloading ML model...")
        async with self._lock:
            self.model = None
            self._is_initialized = False
            await self._initialize()
            logger.info("✅ Model reloaded successfully")
```

- [ ] **Step 4: Update db dependencies to include ML service**

Add to `app/db/dependencies.py`:

```python
# Add at end of app/db/dependencies.py
from app.services.ml_service import MLService

async def get_ml_service() -> MLService:
    """
    FastAPI dependency: provides ML service (singleton, lazy-loaded).
    
    Usage:
        @app.get("/recommend")
        async def recommend(ml: MLService = Depends(get_ml_service)):
            return await ml.get_recommendations(user_id)
    """
    return await MLService.get_instance()
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/unit/test_ml_service.py -v
```

Expected: PASS (or some tests may be skipped if keras not fully mocked)

- [ ] **Step 6: Commit**

```bash
git add app/services/ml_service.py tests/unit/test_ml_service.py app/db/dependencies.py
git commit -m "feat: refactor ML service with lazy loading and async wrapper"
```

---

## Phase 5: Middleware & Error Handling

### Task 5.1: Create Error Handler Middleware

**Files:**
- Create: `app/middleware/error_handler.py`
- Create: `app/middleware/__init__.py`

- [ ] **Step 1: Create error handler middleware**

```python
# app/middleware/error_handler.py
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
```

- [ ] **Step 2: Create middleware __init__**

```python
# app/middleware/__init__.py
from app.middleware.error_handler import app_error_handler, generic_error_handler

__all__ = ["app_error_handler", "generic_error_handler"]
```

- [ ] **Step 3: Commit**

```bash
git add app/middleware/error_handler.py app/middleware/__init__.py
git commit -m "feat: add global error handler middleware"
```

---

### Task 5.2: Create Logging Middleware

**Files:**
- Create: `app/middleware/logging_middleware.py`

- [ ] **Step 1: Create logging middleware**

```python
# app/middleware/logging_middleware.py
"""
Request/response logging middleware.

Logs all HTTP requests and responses with timing information.
"""

import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log HTTP requests and responses.
    
    Adds request_id to all logs for tracing.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Log request
        start_time = time.time()
        logger.info(
            f"request_start",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": str(request.url.path),
                "client": request.client.host if request.client else "unknown"
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"request_error",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": str(request.url.path),
                    "duration_ms": int(duration * 1000),
                    "error": str(e)
                },
                exc_info=True
            )
            raise
        
        # Log response
        duration = time.time() - start_time
        logger.info(
            f"request_complete",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": str(request.url.path),
                "status_code": response.status_code,
                "duration_ms": int(duration * 1000)
            }
        )
        
        # Add request ID to response headers for tracing
        response.headers["X-Request-ID"] = request_id
        
        return response
```

- [ ] **Step 2: Update middleware __init__**

```python
# app/middleware/__init__.py (update)
from app.middleware.error_handler import app_error_handler, generic_error_handler
from app.middleware.logging_middleware import LoggingMiddleware

__all__ = ["app_error_handler", "generic_error_handler", "LoggingMiddleware"]
```

- [ ] **Step 3: Commit**

```bash
git add app/middleware/logging_middleware.py app/middleware/__init__.py
git commit -m "feat: add request/response logging middleware"
```

---

## Phase 6: Update App Main & Dependencies

### Task 6.1: Update main.py with Lifespan & Middleware

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Replace main.py with full async setup**

```python
# app/main.py
"""
FastAPI application entry point.

Sets up:
- Async database engine
- ML service lazy loading
- Global middleware
- Error handlers
- Routes
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.db import models
from app.db.database import engine
from app.services.ml_service import MLService
from app.middleware import LoggingMiddleware, app_error_handler, generic_error_handler
from app.core.exceptions import AppError
from app.utils.logger import setup_logging, get_logger
from app.core.config import settings
import logging

# Setup logging
setup_logging(level=settings.LOG_LEVEL)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan event handler.
    
    Runs setup code before server starts (startup)
    and cleanup code when server shuts down (shutdown).
    """
    logger.info("=" * 60)
    logger.info("🚀 SERVER STARTUP")
    logger.info("=" * 60)
    
    try:
        # 1. Create database tables
        logger.info("📋 Creating database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)
        logger.info("✅ Database tables ready")
        
        # 2. Initialize ML service (background)
        logger.info("🤖 Initializing ML service...")
        try:
            ml_service = await MLService.get_instance()
            logger.info("✅ ML service ready")
        except Exception as e:
            logger.warning(f"⚠️  ML service initialization failed: {e}")
            logger.info("✓ Server will continue with degraded ML features")
        
        logger.info("=" * 60)
        logger.info("🎉 SERVER READY")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"💥 Startup failed: {e}", exc_info=True)
        raise
    
    # Server runs here (yield)
    yield
    
    # Shutdown code
    logger.info("=" * 60)
    logger.info("🛑 SERVER SHUTDOWN")
    logger.info("=" * 60)
    
    try:
        logger.info("📌 Closing database connections...")
        await engine.dispose()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)
    
    logger.info("👋 Goodbye!")


# Create FastAPI app with lifespan
app = FastAPI(
    title="🎬 Movie Recommender API",
    version="2.0.0 (Refactored - Async)",
    description="Movie recommendations with ML",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add global exception handlers
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, generic_error_handler)

# Import and include routers
from app.api import auth, movies, recommend, health

app.include_router(auth.router)
app.include_router(movies.router)
app.include_router(recommend.router)
app.include_router(health.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "✅ Movie Recommender API v2.0",
        "version": "2.0.0-async"
    }
```

- [ ] **Step 2: Verify config imports**

Make sure imports are available:

```bash
cd "E:\TTCS Project"
python -c "from app.main import app; print('App imports OK')"
```

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "refactor: update main.py with async lifespan and middleware"
```

---

## Phase 7: API Routes Refactor

### Task 7.1: Refactor Auth Routes

**Files:**
- Modify: `app/api/auth.py`

- [ ] **Step 1: Replace auth.py with async routes**

```python
# app/api/auth.py
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
```

- [ ] **Step 2: Verify auth routes work**

Check that imports resolve:

```bash
cd "E:\TTCS Project"
python -c "from app.api.auth import router; print('Auth routes OK')"
```

- [ ] **Step 3: Commit**

```bash
git add app/api/auth.py
git commit -m "refactor: convert auth routes to async with services"
```

---

### Task 7.2: Refactor Movies Routes

**Files:**
- Modify: `app/api/movies.py`

- [ ] **Step 1: Create/update movies.py with async routes**

```python
# app/api/movies.py
"""
Movies API routes.

Handles movie listing, search, and details.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.dependencies import get_db_session
from app.services.movie_service import MovieService
from app.schemas.movie_schema import MovieResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/movies", tags=["Movies"])


@router.get("/", response_model=list[MovieResponse])
async def list_movies(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session)
):
    """
    List all movies with pagination.
    
    GET /api/movies?skip=0&limit=20
    
    Response:
    [
        {"movieId": 1, "title": "Movie 1", "genres": "Action", ...},
        ...
    ]
    """
    logger.info(f"List movies endpoint: skip={skip}, limit={limit}")
    
    movies = await MovieService.get_all_movies(
        db=db,
        limit=limit,
        offset=skip
    )
    
    return movies


@router.get("/{movie_id}", response_model=MovieResponse)
async def get_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get movie by ID.
    
    GET /api/movies/123
    
    Response:
    {
        "movieId": 123,
        "title": "Movie Title",
        "genres": "Action|Drama",
        ...
    }
    """
    logger.info(f"Get movie endpoint: movie_id={movie_id}")
    
    movie = await MovieService.get_movie_by_id(movie_id, db)
    
    return movie


@router.get("/search/title", response_model=list[MovieResponse])
async def search_movies(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Search movies by title.
    
    GET /api/movies/search/title?q=action
    
    Response:
    [
        {"movieId": 1, "title": "Action Movie", ...},
        ...
    ]
    """
    logger.info(f"Search movies endpoint: q='{q}'")
    
    movies = await MovieService.search_movies(q, db, limit)
    
    return movies
```

- [ ] **Step 2: Verify imports**

```bash
python -c "from app.api.movies import router; print('Movies routes OK')"
```

- [ ] **Step 3: Commit**

```bash
git add app/api/movies.py
git commit -m "refactor: convert movies routes to async with services"
```

---

### Task 7.3: Refactor Recommend Routes

**Files:**
- Modify: `app/api/recommend.py`

- [ ] **Step 1: Replace recommend.py with async routes**

```python
# app/api/recommend.py
"""
Recommendation API routes.

Handles recommendations and rating movies.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.dependencies import get_db_session, get_ml_service
from app.core.security import get_current_user_id
from app.services.recommendation_service import RecommendationService
from app.services.ml_service import MLService
from app.schemas.movie_schema import RatingCreate, RatingResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["Recommendations"])


@router.get("/recommend")
async def get_recommendations(
    limit: int = 10,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
    ml: MLService = Depends(get_ml_service)
):
    """
    Get personalized recommendations for user.
    
    GET /api/recommend
    Headers: Authorization: Bearer <token>
    
    Response:
    {
        "is_new_user": false,
        "recommendations": [
            {"movieId": 1, "title": "...", "predicted_rating": 4.5},
            ...
        ],
        "history": [...]
    }
    """
    logger.info(f"Get recommendations endpoint for user: {user_id}")
    
    result = await RecommendationService.get_recommendations_for_user(
        user_id,
        db,
        limit
    )
    
    return result


@router.post("/rate", response_model=RatingResponse, status_code=status.HTTP_201_CREATED)
async def rate_movie(
    rating_data: RatingCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Rate a movie.
    
    POST /api/rate
    Headers: Authorization: Bearer <token>
    {
        "movieId": 123,
        "rating": 4.5
    }
    
    Response: 201 Created
    {
        "userId": 1,
        "movieId": 123,
        "rating": 4.5,
        "timestamp": "2026-05-11T10:30:00"
    }
    """
    logger.info(f"Rate movie endpoint: user={user_id}, movie={rating_data.movieId}, rating={rating_data.rating}")
    
    result = await RecommendationService.rate_movie(
        user_id,
        rating_data.movieId,
        rating_data.rating,
        db
    )
    
    return result
```

- [ ] **Step 2: Verify imports**

```bash
python -c "from app.api.recommend import router; print('Recommend routes OK')"
```

- [ ] **Step 3: Commit**

```bash
git add app/api/recommend.py
git commit -m "refactor: convert recommend routes to async with services"
```

---

### Task 7.4: Create Health Check Routes

**Files:**
- Create: `app/api/health.py`

- [ ] **Step 1: Create health check routes**

```python
# app/api/health.py
"""
Health check API routes.

For load balancers and monitoring to determine service health.
"""

from fastapi import APIRouter
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health")
async def health_check():
    """
    Basic health check.
    
    GET /api/health
    
    Response: 200 OK
    {
        "status": "healthy",
        "service": "Movie Recommender API"
    }
    """
    return {
        "status": "healthy",
        "service": "Movie Recommender API v2.0"
    }
```

- [ ] **Step 2: Commit**

```bash
git add app/api/health.py
git commit -m "feat: add health check endpoint"
```

---

## Phase 8: Update Requirements & Final Testing

### Task 8.1: Update requirements.txt

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Update requirements.txt**

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy[asyncio]==2.0.23
aiomysql==0.2.0
pydantic==2.5.0
pydantic-settings==2.0.3
python-json-logger==2.0.7
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
tensorflow==2.13.0
scikit-learn==1.3.0
pandas==2.0.3
PyJWT==2.8.1
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.1
```

- [ ] **Step 2: Install requirements**

```bash
cd "E:\TTCS Project"
pip install -r requirements.txt
```

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "feat: update requirements for async setup"
```

---

### Task 8.2: Run Full Integration Test

**Files:**
- Test: All routes

- [ ] **Step 1: Start the server**

```bash
cd "E:\TTCS Project"
uvicorn app.main:app --reload --log-level info
```

Expected: Server starts in <1 second, not 3-5 seconds

- [ ] **Step 2: Test health endpoint**

```bash
curl http://localhost:8000/api/health
```

Expected:
```json
{"status": "healthy", "service": "Movie Recommender API v2.0"}
```

- [ ] **Step 3: Test register endpoint**

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "password123"}'
```

Expected: 201 Created with user data

- [ ] **Step 4: Test duplicate user error**

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "password123"}'
```

Expected: 409 Conflict with error response

- [ ] **Step 5: Test login endpoint**

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "password123"}'
```

Expected: 200 OK with access_token

- [ ] **Step 6: Test recommend endpoint with token**

```bash
# Get token first
TOKEN="<copy access_token from login response>"

curl http://localhost:8000/api/recommend \
  -H "Authorization: Bearer $TOKEN"
```

Expected: 200 OK with recommendations

- [ ] **Step 7: Check logs are structured**

Look at console output - should be JSON format logs with timestamps, request IDs, etc.

- [ ] **Step 8: Run pytest suite**

```bash
pytest tests/unit/ -v --asyncio-mode=auto
```

Expected: All tests PASS

- [ ] **Step 9: Final commit**

```bash
git add .
git commit -m "test: integrate and verify full async refactor"
```

---

## 📋 Verification Checklist

Before considering this complete:

- [ ] All routes converted to async (auth, recommend, movies, health)
- [ ] Database layer fully async (aiomysql driver)
- [ ] ML service lazy-loads on first request (not on import)
- [ ] Error handling centralized in middleware
- [ ] Logging structured (JSON format)
- [ ] Services layer created with business logic
- [ ] Dependency injection working (Depends())
- [ ] Server starts fast (<1 second)
- [ ] Health endpoint responds
- [ ] All API tests pass
- [ ] No blocking I/O in request handlers
- [ ] Graceful error responses with error types
- [ ] Request IDs in logs for tracing

---

## 🎉 Implementation Complete

All 8 phases implemented:
1. ✅ Foundation (exceptions, logging)
2. ✅ Async DB infrastructure
3. ✅ Service layer
4. ✅ ML refactor
5. ✅ Middleware & error handling
6. ✅ App main & dependencies
7. ✅ API routes refactor
8. ✅ Requirements & testing

**Total commits:** ~20 logical commits
**Total new files:** ~15
**Total modified files:** ~8

Next: Deploy and monitor!

