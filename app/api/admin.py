import subprocess
import sys
import os
from typing import Optional
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy import desc
from sqlalchemy.util.concurrency import asyncio
from fastapi import status
from app.core.security import get_password_hash
from app.db.models import Favorite
from app.db.dependencies import get_db_session
from app.core.security import get_current_admin
from app.db.models import User, Movie, Rating
from app.services.ml_service import MLService
from app.schemas.user_schema import UserCreate, UserUpdate
from app.schemas.movie_schema import MovieCreate, MovieUpdate


# Tạo Router mới với tiền tố /api/admin
router = APIRouter(prefix="/api/admin", tags=["Admin Dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
        admin_user=Depends(get_current_admin),  # LÍNH GÁC BẢO VỆ Ở ĐÂY
        db: AsyncSession = Depends(get_db_session)
):
    """Lấy các chỉ số tổng quan cho trang Quản trị"""

    # 1. Dùng func.count của SQLAlchemy để đếm số lượng dòng trong MySQL siêu tốc
    movies_count = await db.scalar(select(func.count(Movie.movieId)))
    users_count = await db.scalar(select(func.count(User.userId)))
    ratings_count = await db.scalar(select(func.count(Rating.movieId)))

    # 2. Đọc thời gian huấn luyện AI mới nhất từ file .keras trên ổ cứng
    ai_last_update = "Chưa có dữ liệu"
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.normpath(os.path.join(current_dir, "../../training/movie_recommender_model.keras"))

        if os.path.exists(model_path):
            # Lấy thời gian file được sửa đổi lần cuối (modified time)
            timestamp = os.path.getmtime(model_path)
            ai_last_update = datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M")
    except Exception as e:
        print(f"Không thể đọc thời gian file AI: {e}")

    return {
        "total_movies": movies_count or 0,
        "total_users": users_count or 0,
        "total_ratings": ratings_count or 0,
        "ai_last_update": ai_last_update
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
            print("\n⏱️ Chờ 2 giây để Hệ điều hành giải phóng hoàn toàn file lock...")
            await asyncio.sleep(2)
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


@router.get("/users")
async def get_all_users(
        page: int = 1,
        limit: int = 5,
        search: Optional[str] = None,
        admin_user=Depends(get_current_admin),
        db: AsyncSession = Depends(get_db_session)
):
    """Lấy danh sách người dùng có phân trang và tìm kiếm (Giới hạn browse 10 trang)"""
    stmt = select(User)

    # 1. Xử lý logic Tìm kiếm (Nếu có từ khóa truyền lên)
    if search:
        search_query = search.strip()
        if search_query.isdigit():
            # Nếu nhập số, tìm chính xác theo ID hoặc tìm gần đúng theo tên
            stmt = stmt.where(or_(User.userId == int(search_query), User.username.ilike(f"%{search_query}%")))
        else:
            # Nếu nhập chữ, tìm gần đúng theo tên
            stmt = stmt.where(User.username.ilike(f"%{search_query}%"))

    # 2. Tính tổng số lượng bản ghi để phân trang
    count_stmt = select(func.count()).select_from(stmt)
    total_count = await db.scalar(count_stmt) or 0

    # CHỐT CHẶN: Nếu KHÔNG tìm kiếm và tổng số user vượt quá 50 (10 trang * 5)
    # Thì ta ép hệ thống chỉ coi như có 50 user để phân trang tối đa là 10.
    if not search and total_count > 50:
        total_count = 50

    # 3. Tính toán số trang (Cơ chế làm tròn lên)
    total_pages = (total_count + limit - 1) // limit
    if total_pages == 0: total_pages = 1

    # Tính số bản ghi cần bỏ qua (skip) dựa trên số trang hiện tại
    skip = (page - 1) * limit

    # 4. Thực thi truy vấn lấy dữ liệu đổ về trang hiện tại
    stmt = stmt.order_by(desc(User.userId)).offset(skip).limit(limit)
    result = await db.execute(stmt)
    users = result.scalars().all()

    return {
        "total_pages": total_pages,
        "current_page": page,
        "users": [
            {
                "userId": u.userId,
                "username": getattr(u, 'username', 'User ' + str(u.userId)),
                "role": getattr(u, 'role', 'user'),
                "is_active": getattr(u, 'is_active', True)
            } for u in users
        ]
    }

@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
        user_in: UserCreate,
        admin_user=Depends(get_current_admin),
        db: AsyncSession = Depends(get_db_session)
):
    try:
        new_user = User(
            username=user_in.username,
            password_hash=get_password_hash(user_in.password),
            role=user_in.role,
            is_active=True
        )
        db.add(new_user)
        await db.commit()
        return {"message": "Tạo người dùng thành công"}

    except IntegrityError:
        # Bắt dính lỗi trùng tên đăng nhập hoặc lỗi ràng buộc DB
        await db.rollback() # Hoàn tác giao dịch để không kẹt Database
        raise HTTPException(
            status_code=400,
            detail="Tên đăng nhập này đã tồn tại, vui lòng chọn tên khác!"
        )
    except Exception as e:
        # Bắt các lỗi không lường trước khác
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi hệ thống: {str(e)}"
        )

# API Cập nhật User
@router.put("/users/{user_id}")
async def update_user(
        user_id: int,
        user_in: UserUpdate,
        admin_user=Depends(get_current_admin),
        db: AsyncSession = Depends(get_db_session)
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy User")

    if user_in.username: user.username = user_in.username
    # if user_in.email: user.email = user_in.email
    if user_in.role: user.role = user_in.role

    await db.commit()
    return {"message": "Cập nhật thành công"}


# API Bật/Tắt (Toggle) Trạng thái
@router.patch("/users/{user_id}/toggle")
async def toggle_user_status(
        user_id: int,
        admin_user=Depends(get_current_admin),
        db: AsyncSession = Depends(get_db_session)
):
    if user_id == admin_user.userId:
        raise HTTPException(status_code=400, detail="Lỗi: Bạn không thể tự khóa tài khoản của chính mình!")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy User")

    # Đảo ngược trạng thái hiện tại
    user.is_active = not getattr(user, 'is_active', True)
    await db.commit()

    status_text = "đã kích hoạt" if user.is_active else "đã bị khóa"
    return {"message": f"Tài khoản {status_text}"}


# --- API LẤY DANH SÁCH (Cập nhật output) ---
@router.get("/movies")
async def get_all_movies(
        page: int = 1, limit: int = 5, search: Optional[str] = None,
        admin_user=Depends(get_current_admin), db: AsyncSession = Depends(get_db_session)
):
    stmt = select(Movie)
    if search:
        search_query = search.strip()
        if search_query.isdigit():
            stmt = stmt.where(or_(Movie.movieId == int(search_query), Movie.title.ilike(f"%{search_query}%")))
        else:
            stmt = stmt.where(Movie.title.ilike(f"%{search_query}%"))

    count_stmt = select(func.count()).select_from(stmt)
    total_count = await db.scalar(count_stmt) or 0
    if not search and total_count > 50: total_count = 50

    total_pages = (total_count + limit - 1) // limit
    if total_pages == 0: total_pages = 1
    skip = (page - 1) * limit

    stmt = stmt.order_by(desc(Movie.movieId)).offset(skip).limit(limit)
    result = await db.execute(stmt)
    movies = result.scalars().all()

    # Trả về TOÀN BỘ dữ liệu để Frontend đẩy vào Popup
    return {
        "total_pages": total_pages,
        "current_page": page,
        "movies": [{
            "movieId": m.movieId, "title": m.title, "genres": m.genres,
            "description": m.description, "poster_url": m.poster_url,
            "backdrop_url": m.backdrop_url, "runtime": m.runtime,
            "director": m.director, "cast": m.cast,
            "release_year": m.release_year, "imdb_rating": m.imdb_rating,
            "is_active": getattr(m, 'is_active', True)
        } for m in movies]
    }


# --- API THÊM PHIM ---
@router.post("/movies", status_code=status.HTTP_201_CREATED)
async def create_movie(movie_in: MovieCreate, admin_user=Depends(get_current_admin),
                       db: AsyncSession = Depends(get_db_session)):
    try:
        new_movie = Movie(
            title=movie_in.title, genres=movie_in.genres, description=movie_in.description,
            poster_url=movie_in.poster_url, backdrop_url=movie_in.backdrop_url,
            runtime=movie_in.runtime, director=movie_in.director, cast=movie_in.cast,
            release_year=movie_in.release_year, imdb_rating=movie_in.imdb_rating, is_active=True
        )
        db.add(new_movie)
        await db.commit()
        await db.refresh(new_movie)
        return {"message": "Thêm phim thành công", "movieId": new_movie.movieId}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi: {str(e)}")


# --- API SỬA PHIM ---
@router.put("/movies/{movie_id}")
async def update_movie(movie_id: int, movie_in: MovieUpdate, admin_user=Depends(get_current_admin),
                       db: AsyncSession = Depends(get_db_session)):
    movie = await db.get(Movie, movie_id)
    if not movie: raise HTTPException(status_code=404, detail="Không tìm thấy Phim")

    # Cập nhật các trường có gửi lên
    update_data = movie_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(movie, key, value)

    await db.commit()
    return {"message": "Cập nhật thành công"}

# --- API ẨN/HIỆN PHIM ---
@router.patch("/movies/{movie_id}/toggle")
async def toggle_movie_status(
        movie_id: int, admin_user=Depends(get_current_admin), db: AsyncSession = Depends(get_db_session)
):
    movie = await db.get(Movie, movie_id)
    if not movie: raise HTTPException(status_code=404, detail="Không tìm thấy Phim")
    movie.is_active = not getattr(movie, 'is_active', True)
    await db.commit()
    return {"message": "Đã đổi trạng thái phim"}