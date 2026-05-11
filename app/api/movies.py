"""
Movies API routes.

Handles movie listing, search, and details.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.dependencies import get_db_session
from app.services.movie_service import MovieService
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/movies", tags=["Movies"])


@router.get("/", response_model=list)
async def list_movies(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session)
):
    """
    List all movies with pagination.
    
    GET /api/movies?skip=0&limit=20
    """
    logger.info(f"List movies endpoint: skip={skip}, limit={limit}")
    
    movies = await MovieService.get_all_movies(
        db=db,
        limit=limit,
        offset=skip
    )
    
    return movies


@router.get("/{movie_id}")
async def get_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get movie by ID.
    
    GET /api/movies/123
    """
    logger.info(f"Get movie endpoint: movie_id={movie_id}")
    
    movie = await MovieService.get_movie_by_id(movie_id, db)
    
    return movie


@router.get("/search/title", response_model=list)
async def search_movies(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Search movies by title.
    
    GET /api/movies/search/title?q=action
    """
    logger.info(f"Search movies endpoint: q='{q}'")
    
    movies = await MovieService.search_movies(q, db, limit)
    
    return movies
