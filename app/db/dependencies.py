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


async def get_ml_service():
    """
    FastAPI dependency: provides ML service (singleton, lazy-loaded).
    
    Usage:
        @app.get("/recommend")
        async def recommend(ml: MLService = Depends(get_ml_service)):
            return await ml.get_recommendations(user_id)
    """
    from app.services.ml_service import MLService
    return await MLService.get_instance()


