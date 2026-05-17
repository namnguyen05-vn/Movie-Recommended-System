from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from app.schemas.rating_schema import RatingCreate
from app.db.dependencies import get_db_session
from app.core.security import get_current_user_id
from app.db.models import Rating

router = APIRouter(prefix="/api/rate", tags=["Rating"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def rate_movie(
        rating_data: RatingCreate,
        user_id: int = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db_session)
):
    """Lưu hoặc cập nhật điểm đánh giá của người dùng"""
    stmt = select(Rating).where(Rating.userId == user_id, Rating.movieId == rating_data.movieId)
    result = await db.execute(stmt)
    existing_rating = result.scalars().first()
    current_time_val = int(datetime.now().strftime("%Y%m%d%H%M%S"))
    if existing_rating:
        existing_rating.rating = rating_data.rating
        existing_rating.timestamp = current_time_val
    else:
        new_rating = Rating(
            userId=user_id,
            movieId=rating_data.movieId,
            rating=rating_data.rating,
            timestamp=current_time_val
        )
        db.add(new_rating)

    await db.commit()
    return {"status": "success", "message": "Rating saved successfully"}


@router.get("/{movie_id}")
async def get_user_rating(
        movie_id: int,
        user_id: int = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db_session)
):
    """Lấy số sao đánh giá cũ khi load lại trang"""
    stmt = select(Rating).where(Rating.userId == user_id, Rating.movieId == movie_id)
    result = await db.execute(stmt)
    user_rating = result.scalars().first()

    if user_rating:
        return {"rated": True, "rating": user_rating.rating}
    return {"rated": False, "rating": 0}
