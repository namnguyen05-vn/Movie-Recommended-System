from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from app.db.database import Base
from pydantic import BaseModel, Field
from sqlalchemy.sql import func
# ==========================================
# BẢNG 1: TÀI KHOẢN NGƯỜI DÙNG (users)
# ==========================================
class User(Base):
    __tablename__ = "users"

    userId = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    password_hash = Column(String(255))

# ==========================================
# BẢNG 2: THÔNG TIN PHIM (movies)
# ==========================================
class Movie(Base):
    __tablename__ = "movies"

    movieId = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    genres = Column(String(255))
    description = Column(Text)
    poster_url = Column(String(255))

# ==========================================
# BẢNG 3: LỊCH SỬ CHẤM ĐIỂM (ratings)
# ==========================================
class Rating(Base):
    __tablename__ = "ratings"

    # SQLAlchemy bắt buộc phải có primary_key để nhận diện dòng dữ liệu.
    # Vì bảng ratings không có cột ID riêng, ta dùng kết hợp cả userId và movieId làm khóa chính.
    userId = Column(Integer, primary_key=True, index=True)
    movieId = Column(Integer, primary_key=True, index=True)
    rating = Column(Float)
    timestamp = Column(DateTime, default=func.now(), onupdate=func.now())
