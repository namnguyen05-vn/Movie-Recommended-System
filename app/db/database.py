"""
Async database engine and session configuration.

Uses SQLAlchemy 2.0+ async features with aiomysql driver.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
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
    }
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,    # Don't expire objects after commit
    autoflush=False,           # Explicit flush control
)

# Base class for ORM models
Base = declarative_base()

logger.info("📦 Async database engine configured")
