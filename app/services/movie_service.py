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
    def _base_query():
        """
        Helper method to get a base query that filters out invalid movies.
        Filters out movies with missing posters or default placeholder posters.
        """
        return select(Movie).where(
            Movie.poster_url.isnot(None),
            Movie.poster_url != "https://via.placeholder.com/500x750?text=No+Poster"
        )

    @staticmethod
    async def get_all_movies(
        db: AsyncSession,
        limit: int = 100,
        offset: int = 0
    ) -> list:
        """
        Get all movies with pagination (only movies with valid posters).

        Args:
            db: Database session
            limit: Maximum movies to return
            offset: Pagination offset

        Returns:
            List of Movie objects
        """
        logger.debug(f"Fetching movies: limit={limit}, offset={offset}")

        result = await db.execute(
            MovieService._base_query()
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

        # Keep select(Movie) here because fetching by exact ID should return the record
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
        Search movies by title (only movies with valid posters).

        Args:
            query: Search query string
            db: Database session
            limit: Maximum results

        Returns:
            List of matching Movie objects
        """
        logger.debug(f"Searching movies: query='{query}'")

        result = await db.execute(
            MovieService._base_query()
            .where(Movie.title.ilike(f"%{query}%"))
            .limit(limit)
        )
        movies = result.scalars().all()

        logger.debug(f"Found {len(movies)} movies matching '{query}'")
        return movies

    @staticmethod
    async def get_movies_by_genre(
        genre: str,
        db: AsyncSession,
        limit: int = 20,
        offset: int = 0
    ) -> list:
        """
        Get movies by genre (only movies with valid posters).

        Args:
            genre: Genre name to filter by
            db: Database session
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of Movie objects matching the genre
        """
        logger.debug(f"Fetching movies by genre: genre='{genre}'")

        result = await db.execute(
            MovieService._base_query()
            .where(Movie.genres.ilike(f"%{genre}%"))
            .limit(limit)
            .offset(offset)
        )
        movies = result.scalars().all()

        logger.debug(f"Found {len(movies)} movies with genre '{genre}'")
        return movies