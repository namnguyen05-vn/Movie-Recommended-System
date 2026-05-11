from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Nhập khẩu các module đã xây dựng
from app.api import auth, recommend
from app.db.database import engine
from app.db import models

# Lệnh ma thuật: Tự động kiểm tra và tạo bảng trong MySQL nếu chưa có
models.Base.metadata.create_all(bind=engine)

# Khởi tạo ứng dụng
app = FastAPI(title="Movie Recommender API - Kiến trúc chuẩn Production")

# Cấu hình CORS để Frontend (HTML/JS) có thể gọi được API mà không bị chặn
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cắm nhánh API Đăng ký / Đăng nhập vào Tổng đài
app.include_router(auth.router)
app.include_router(recommend.router)

# Một API test nhỏ để kiểm tra server có sống không
@app.get("/")
def root():
    return {"message": "✅ Máy chủ Backend đã hoạt động trơn tru!"}