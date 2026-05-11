"""
Recommendation service: business logic for recommendations.

Orchestrates between ML service and database.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Rating, Movie
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
            # Import here to avoid circular dependency
            from app.services.ml_service import MLService
            
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
    ) -> list:
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

