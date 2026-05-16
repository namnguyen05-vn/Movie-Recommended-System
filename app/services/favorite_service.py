from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.db.models import Favorite, Movie
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FavoriteService:

    @staticmethod
    async def toggle_favorite(user_id: int, movie_id: int, db: AsyncSession) -> str:
        """Thêm vào yêu thích nếu chưa có, xóa nếu đã tồn tại (Toggle)"""
        logger.info(f"User {user_id} toggling favorite for movie {movie_id}")

        # Kiểm tra xem đã yêu thích chưa
        stmt = select(Favorite).where(Favorite.userId == user_id, Favorite.movieId == movie_id)
        result = await db.execute(stmt)
        existing = result.scalars().first()

        if existing:
            # Nếu đã có -> Xóa đi
            await db.execute(delete(Favorite).where(Favorite.userId == user_id, Favorite.movieId == movie_id))
            await db.commit()
            logger.debug(f"Removed movie {movie_id} from user {user_id} favorites")
            return "removed"
        else:
            # Nếu chưa có -> Thêm mới
            new_fav = Favorite(userId=user_id, movieId=movie_id)
            db.add(new_fav)
            await db.commit()
            logger.debug(f"Added movie {movie_id} to user {user_id} favorites")
            return "added"

    @staticmethod
    async def check_status(user_id: int, movie_id: int, db: AsyncSession) -> bool:
        """Kiểm tra xem một bộ phim cụ thể đã được user này thích chưa"""
        stmt = select(Favorite).where(Favorite.userId == user_id, Favorite.movieId == movie_id)
        result = await db.execute(stmt)
        return result.scalars().first() is not None

    @staticmethod
    async def get_user_favorites(user_id: int, db: AsyncSession) -> list:
        """Lấy danh sách thông tin đầy đủ của các bộ phim đã yêu thích"""
        # Join bảng Favorite với bảng Movie để lấy thông tin phim
        stmt = select(Movie).join(Favorite, Movie.movieId == Favorite.movieId).where(Favorite.userId == user_id)
        result = await db.execute(stmt)
        return result.scalars().all()