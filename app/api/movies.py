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
from app.core.security import get_current_user_id
import time
from sqlalchemy import select
from app.db.models import Rating

logger = get_logger(__name__)

router = APIRouter(prefix="/api/movies", tags=["Movies"])


@router.get("/search/title", response_model=list[MovieResponse])
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


@router.get("/", response_model=list[MovieResponse])
async def list_movies(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    genre: str = Query(None),
    db: AsyncSession = Depends(get_db_session)
):
    """
    List all movies with optional search and genre filtering.
    
    GET /api/movies?skip=0&limit=20
    GET /api/movies?skip=0&limit=20&search=action
    GET /api/movies?skip=0&limit=20&genre=Action
    """
    logger.info(f"List movies endpoint: skip={skip}, limit={limit}, search={search}, genre={genre}")
    
    # If search is provided, use search instead
    if search:
        movies = await MovieService.search_movies(search, db, limit)
        return movies
    
    # If genre is provided, filter by genre
    if genre:
        movies = await MovieService.get_movies_by_genre(genre, db, limit, skip)
        return movies
    
    # Otherwise get all movies
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
    """
    logger.info(f"Get movie endpoint: movie_id={movie_id}")
    
    movie = await MovieService.get_movie_by_id(movie_id, db)
    
    return movie
