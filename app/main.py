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
from app.api import auth, recommend, movies

app.include_router(auth.router)
app.include_router(movies.router)
app.include_router(recommend.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "✅ Movie Recommender API v2.0",
        "version": "2.0.0-async"
    }
