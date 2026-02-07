from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/evalkit"
    redis_url: str = "redis://localhost:6379"

    secret_key: str = "change-me-in-production"

    anthropic_api_key: str = ""
    openai_api_key: str = ""

    small_model: str = "gpt-4o-mini"
    large_model: str = "gpt-4o"
    confidence_threshold: float = 0.80

    allowed_origins: str = "http://localhost:3000"

    redis_cache_ttl: int = 604800  # 7 days

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
