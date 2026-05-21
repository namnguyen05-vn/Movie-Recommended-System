from pydantic import BaseModel, Field
from typing import Optional

# ==========================================
# 1. KHUÔN MẪU NHẬN DỮ LIỆU TỪ FRONTEND (REQUEST)
# ==========================================

# Dùng chung cho Đăng ký, Đăng nhập và Admin Thêm User
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    # email: str = None  # Tạm ẩn theo thiết kế hiện tại
    password: str = Field(..., min_length=6, max_length=50)
    role: str = "user"   # Mặc định là 'user', Admin có thể truyền lên 'admin'

class UserUpdate(BaseModel):
    # Dùng Optional để Admin có thể sửa 1 trường mà không cần sửa các trường khác
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    # email: Optional[str] = None
    role: Optional[str] = None

# ==========================================
# 2. KHUÔN MẪU TRẢ DỮ LIỆU VỀ FRONTEND (RESPONSE)
# ==========================================

# Trả về thông tin user nhưng TUYỆT ĐỐI KHÔNG trả về password_hash
class UserResponse(BaseModel):
    userId: int
    username: str
    role: str

    class Config:
        # Giúp Pydantic tự động đọc hiểu dữ liệu được rút ra từ SQLAlchemy (ORM)
        from_attributes = True

# Khuôn mẫu trả về khi Đăng nhập thành công (kèm thẻ Token)
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str