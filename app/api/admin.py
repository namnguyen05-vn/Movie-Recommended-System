from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy import desc

from app.db.models import Favorite
from app.db.dependencies import get_db_session
from app.core.security import get_current_admin
from app.db.models import User, Movie, Rating

# Tạo Router mới với tiền tố /api/admin
router = APIRouter(prefix="/api/admin", tags=["Admin Dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
        admin_user=Depends(get_current_admin),  # LÍNH GÁC BẢO VỆ Ở ĐÂY
        db: AsyncSession = Depends(get_db_session)
):
    """Lấy các chỉ số tổng quan cho trang Quản trị"""

    # Dùng func.count của SQLAlchemy để đếm số lượng dòng trong MySQL siêu tốc
    movies_count = await db.scalar(select(func.count(Movie.movieId)))
    users_count = await db.scalar(select(func.count(User.userId)))
    ratings_count = await db.scalar(select(func.count(Rating.movieId)))

    return {
        "total_movies": movies_count or 0,
        "total_users": users_count or 0,
        "total_ratings": ratings_count or 0,
        "ai_last_update": "Chưa có dữ liệu"
    }


# 1. API: LẤY TOP PHIM ĐƯỢC YÊU THÍCH NHẤT
@router.get("/top-favorites")
async def get_top_favorites(
        admin_user=Depends(get_current_admin),
        db: AsyncSession = Depends(get_db_session)
):
    # Đếm số lượng thả tim theo movieId, sắp xếp giảm dần, lấy top 5
    stmt = (
        select(Movie.title, func.count(Favorite.movieId).label('fav_count'))
        .join(Favorite, Movie.movieId == Favorite.movieId)
        .group_by(Movie.movieId)
        .order_by(desc('fav_count'))
        .limit(5)
    )
    result = await db.execute(stmt)
    top_favs = result.all()

    return [{"title": row.title, "count": row.fav_count} for row in top_favs]


# 2. API: LẤY TOP PHIM ĐÁNH GIÁ CAO NHẤT
@router.get("/top-rated")
async def get_top_rated(
        admin_user=Depends(get_current_admin),
        db: AsyncSession = Depends(get_db_session)
):
    # Tính điểm trung bình theo movieId, sắp xếp giảm dần, lấy top 5
    stmt = (
        select(Movie.title, func.avg(Rating.rating).label('avg_rating'))
        .join(Rating, Movie.movieId == Rating.movieId)
        .group_by(Movie.movieId)
        .order_by(desc('avg_rating'))
        .limit(5)
    )
    result = await db.execute(stmt)
    top_rated = result.all()

    return [{"title": row.title, "rating": round(row.avg_rating, 1)} for row in top_rated]


# 3. API: KÍCH HOẠT CHẠY LẠI MODEL AI
@router.post("/retrain-ai")
async def trigger_ai_retrain(
        admin_user=Depends(get_current_admin),
):
    """
    Hàm này mô phỏng việc gọi script Machine Learning để train lại ma trận gợi ý.
    Trong thực tế, bạn sẽ import model AI vào đây và gọi hàm .fit()
    """
    import asyncio
    from datetime import datetime

    # Giả lập thời gian AI đang tính toán (đọc file, train ma trận...) mất 3 giây
    await asyncio.sleep(3)

    current_time = datetime.now().strftime("%d/%m/%Y %H:%M")

    return {
        "status": "success",
        "message": "AI Model đã được huấn luyện lại thành công với dữ liệu mới nhất!",
        "last_update": current_time
    }