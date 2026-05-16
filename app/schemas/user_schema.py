from pydantic import BaseModel, Field

# ==========================================
# 1. KHUÔN MẪU NHẬN DỮ LIỆU TỪ FRONTEND (REQUEST)
# ==========================================
# Dùng cho cả API Đăng ký và Đăng nhập
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=50)
# ==========================================
# 2. KHUÔN MẪU TRẢ DỮ LIỆU VỀ FRONTEND (RESPONSE)
# ==========================================
# Trả về thông tin user nhưng TUYỆT ĐỐI KHÔNG trả về password_hash
class UserResponse(BaseModel):
    userId: int
    username: str

    class Config:
        # Cấu hình này rất quan trọng: Giúp Pydantic tự động đọc hiểu dữ liệu
        # được rút ra từ SQLAlchemy (ORM) thay vì chỉ đọc dạng Dictionary thông thường.
        from_attributes = True

# Khuôn mẫu trả về khi Đăng nhập thành công (kèm thẻ Token)
class Token(BaseModel):
    access_token: str
    token_type: str