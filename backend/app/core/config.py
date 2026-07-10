from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='BACKEND_', env_file=str(BASE_DIR / '.env'), extra='ignore')

    app_name: str = 'Restaurant Menu Management System'
    api_prefix: str = '/api/v1'
    database_url: str = 'sqlite:///./restaurant.db'
    secret_key: str = 'change-me-in-production-please-use-a-32-char-secret'
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24
    otp_expire_minutes: int = 5
    otp_resend_cooldown_seconds: int = 60
    otp_max_attempts: int = 3
    allow_waitress_override: bool = True
    demo_otp_passthrough: bool = True
    cors_origins: str = 'http://localhost:5173'


@lru_cache
def get_settings() -> Settings:
    return Settings()
