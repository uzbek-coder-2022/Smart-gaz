"""Application configuration loaded from environment variables."""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "development"
    DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    DATABASE_URL: str = "sqlite+aiosqlite:///./smartgaz.db"
    DATABASE_URL_SYNC: str = "sqlite:///./smartgaz.db"

    SECRET_KEY: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    BOT_TOKEN: Optional[str] = None
    SMS_PROVIDER: str = "eskiz"
    SMS_API_KEY: Optional[str] = None

    DEFAULT_COOLDOWN_DAYS: int = 20
    DEFAULT_PRICE_PER_KG: int = 2800
    DEFAULT_GPS_INTERVAL_SEC: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
