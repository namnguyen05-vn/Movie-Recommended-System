import urllib.parse
import secrets
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # Feature flags
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env" # Khai báo để Pydantic biết tìm file .env ở đâu

    # Synchronous database URL (for migration scripts, legacy code)
    @property
    def DATABASE_URL(self) -> str:
        """MySQL URL with pymysql (synchronous driver)"""
        encoded_password = urllib.parse.quote_plus(self.DB_PASSWORD)
        return f"mysql+pymysql://{self.DB_USER}:{encoded_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    # Asynchronous database URL (for FastAPI)
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """MySQL URL with aiomysql (async driver)"""
        encoded_password = urllib.parse.quote_plus(self.DB_PASSWORD)
        return f"mysql+aiomysql://{self.DB_USER}:{encoded_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

# Khởi tạo một biến settings duy nhất để dùng chung cho toàn bộ dự án
settings = Settings()