"""
Recommendation API routes.

Handles recommendations movies.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.dependencies import get_db_session, get_ml_service
from app.core.security import get_current_user_id
from app.services.recommendation_service import RecommendationService
from app.services.ml_service import MLService
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

