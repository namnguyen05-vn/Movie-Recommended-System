from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.dependencies import get_db_session
from app.core.security import get_current_user_id
from app.services.favorite_service import FavoriteService
from app.schemas.favorite_schema import FavoriteToggleRequest, FavoriteStatusResponse
from app.schemas.movie_schema import MovieResponse

router = APIRouter(prefix="/api/favorites", tags=["Favorites"])

@router.post("/toggle", status_code=status.HTTP_200_OK)
async def toggle_favorite(
    request: FavoriteToggleRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Bấm để Thêm hoặc Xóa phim khỏi danh sách yêu thích"""
    action = await FavoriteService.toggle_favorite(user_id, request.movieId, db)
    return {"status": "success", "action": action}

@router.get("/status/{movie_id}", response_model=FavoriteStatusResponse)
async def get_favorite_status(
    movie_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Kiểm tra trạng thái tim (đỏ hay trống) khi vừa vào trang chi tiết phim"""
    is_fav = await FavoriteService.check_status(user_id, movie_id, db)
    return {"is_favorite": is_fav}

@router.get("/", response_model=list[MovieResponse])
async def get_my_favorites(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Lấy toàn bộ danh sách phim yêu thích của cơ trưởng đang đăng nhập"""
    movies = await FavoriteService.get_user_favorites(user_id, db)
    return movies