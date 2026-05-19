import subprocess
import sys
import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy import desc

from app.db.models import Favorite
from app.db.dependencies import get_db_session
from app.core.security import get_current_admin
from app.db.models import User, Movie, Rating
from app.services.ml_service import MLService

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
    Kích hoạt chạy file training/recommender.py để huấn luyện lại AI
    Sau đó tự động gọi MLService nạp lại mô hình vào RAM.
    """
    try:
        # Xác định vị trí file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.normpath(os.path.join(current_dir, "../../training/recommender.py"))

        if not os.path.exists(script_path):
            raise HTTPException(status_code=404, detail=f"Không tìm thấy file: {script_path}")

        # Bóp cò: Khởi chạy file thuật toán
        process = subprocess.run(
            [sys.executable, "-X", "utf8", script_path]
        )

        # Kiểm tra kết quả
        if process.returncode == 0:

            # ==========================================
            # 2. CÚ CHỐT QUAN TRỌNG NHẤT: BẢO MLSERVICE TẢI LẠI RAM
            # ==========================================
            print("\n🔄 Đang ra lệnh cho MLService tải lại mô hình mới từ ổ cứng...")

            # Lấy instance duy nhất của MLService đang chạy
            ml_instance = await MLService.get_instance()

            # Gọi hàm tải lại (đã bọc Lock cực kỳ an toàn của bạn)
            await ml_instance.reload_model()

            print("✅ Cập nhật bộ nhớ RAM hoàn tất!")
            # ==========================================

            current_time = datetime.now().strftime("%d/%m/%Y %H:%M")
            return {
                "status": "success",
                "message": "AI Model đã được huấn luyện và nạp lên hệ thống thành công!",
                "last_update": current_time
            }
        else:
            raise HTTPException(status_code=500, detail="Thuật toán AI gặp sự cố. Vui lòng check Terminal!")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))