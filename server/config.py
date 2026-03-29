from pydantic_settings import BaseSettings
import os
from typing import Optional

class Settings(BaseSettings):
    """Настройки приложения"""
    SECRET_KEY: str = "your-secret-key-change-in-production-use-env-variable"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 365  # 1 year (essentially no expiration for desktop app)
    UPLOAD_DIR: str = "uploads"

    # SMTP Settings
    SMTP_HOST: str = "sandbox.smtp.mailtrap.io"
    SMTP_PORT: int = 2525
    SMTP_USER: str = "2dcdfb242a00ac"
    SMTP_PASSWORD: str = "bf10c0e023d643"
    MAIL_FROM: str = "PDF Library <no-reply@sandbox.smtp.mailtrap.io>"
    SMTP_TLS: bool = True

    # Database Settings
    DATABASE_URL: Optional[str] = None  # e.g., "postgresql://user:pass@localhost:5432/db"

    # Task Settings
    TASK_MODE: str = "LOCAL"  # LOCAL (Thread-based) or SERVER (Dramatiq/Redis)
    REDIS_URL: Optional[str] = None  # e.g., "redis://localhost:6379/0"
    SEARCH_GO_URL: Optional[str] = None  # e.g., "http://localhost:8001"

    class Config:
        env_file = ".env"

settings = Settings()

# Default to local SQLite if no DATABASE_URL is provided
if not settings.DATABASE_URL:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    settings.DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}"

# Auto-detect mode if REDIS_URL is provided in .env
if settings.REDIS_URL:
    settings.TASK_MODE = "SERVER"

# Создаем директорию для загрузок
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
