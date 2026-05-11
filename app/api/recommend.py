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
from app.schemas.movie_schema import RatingCreate
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


@router.post("/rate", status_code=status.HTTP_201_CREATED)
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
