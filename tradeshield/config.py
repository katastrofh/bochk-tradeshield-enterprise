from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "BOC TradeShield Enterprise")
    env: str = os.getenv("ENV", "local")
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-change-me")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "720"))
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./tradeshield.db")
    cors_origins: str = os.getenv("CORS_ORIGINS", "*")
    storage_dir: str = os.getenv("STORAGE_DIR", "./storage")


@lru_cache
def get_settings() -> Settings:
    return Settings()
