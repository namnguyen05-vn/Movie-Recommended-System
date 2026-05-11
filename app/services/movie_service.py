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
    ) -> list:
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
    ) -> list:
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

