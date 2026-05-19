import jwt
import bcrypt
from datetime import timezone, datetime, timedelta
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.dependencies import get_db_session
from app.db.models import User

security = HTTPBearer()


# ==========================================
# 1. BẢO MẬT MẬT KHẨU (DÙNG BCRYPT CHÍNH CHỦ)
# ==========================================

def get_password_hash(password: str) -> str:
    """Băm mật khẩu: Chuyển string sang byte -> hash -> trả về string để lưu DB"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
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
        return payload.get("sub")
    except:
        return None


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Token không chứa ID người dùng")

        return int(user_id)

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token đã hết hạn! Vui lòng đăng nhập lại.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token bị sai hoặc làm giả!")


# ==========================================
# 3. PHÂN QUYỀN (ROLE-BASED ACCESS CONTROL)
# ==========================================

# Hàm lính gác: Lấy ID từ Token -> Tìm User trong DB -> Kiểm tra Role
async def get_current_admin(
        user_id: int = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db_session)
):
    """
    Hàm này dùng để bảo vệ các API dành riêng cho Admin.
    Nó lấy ID từ Token, truy vấn DB để kiểm tra chính xác quyền hiện tại.
    """
    stmt = select(User).where(User.userId == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()

    # Nếu không tồn tại user hoặc user không phải admin
    if not user or user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Quyền truy cập bị từ chối. Bạn không phải là Quản trị viên!"
        )

    return user