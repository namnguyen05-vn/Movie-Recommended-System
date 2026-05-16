import jwt
import bcrypt
from datetime import timezone
from datetime import datetime, timedelta
from app.core.config import settings
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException

security = HTTPBearer()
# ==========================================
# 1. BẢO MẬT MẬT KHẨU (DÙNG BCRYPT CHÍNH CHỦ)
# ==========================================

def get_password_hash(password: str) -> str:
    """Băm mật khẩu: Chuyển string sang byte -> hash -> trả về string để lưu DB"""
    # Chuyển password sang dạng bytes (UTF-8)
    password_bytes = password.encode('utf-8')

    # Tạo muối (salt) và băm
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)

    # Trả về dạng string để SQLAlchemy lưu vào MySQL dễ dàng
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Kiểm tra mật khẩu: Đối chiếu pass thô với pass đã băm trong DB"""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


# ==========================================
# 2. THẺ THÔNG HÀNH (JWT TOKEN)
# ==========================================
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload.get("sub") # Trả về userId đã lưu trong Token
    except:
        return None


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    token = credentials.credentials  # FastAPI đã tự động cắt chữ Bearer đi giúp ta
    try:
        # Giải mã Token bằng chìa khóa bí mật
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Token không chứa ID người dùng")

        return int(user_id)  # Trả về số nguyên để nhét vào AI

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token đã hết hạn! Vui lòng đăng nhập lại.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token bị sai hoặc làm giả!")