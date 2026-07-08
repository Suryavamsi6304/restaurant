from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='BACKEND_', env_file='.env', extra='ignore')

    app_name: str = 'Restaurant Menu Management System'
    api_prefix: str = '/api/v1'
    database_url: str = 'sqlite:///./restaurant.db'
    secret_key: str = 'change-me-in-production'
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24
    otp_expire_minutes: int = 5
    otp_resend_cooldown_seconds: int = 60
    otp_max_attempts: int = 3
    allow_waitress_override: bool = True
    demo_otp_passthrough: bool = True
    cors_origins: list[str] = ['http://localhost:5173']

    @field_validator('cors_origins', mode='before')
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(',') if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
