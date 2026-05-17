import logging
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

INSECURE_JWT_PLACEHOLDERS = frozenset({
    "change-me-in-production-use-openssl-rand-hex-32",
    "dev-secret-key-change-in-prod-abc123",
})


class Settings(BaseSettings):
    # LLM
    groq_api_key: str = ""
    gemini_api_key: str = ""

    # Market data
    alpha_vantage_key: str = ""
    finnhub_key: str = ""
    newsapi_key: str = ""
    gnews_key: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/stocksage"
    sqlite_url: str = "sqlite+aiosqlite:///./stocksage_local.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # ChromaDB
    chroma_persist_dir: str = "./chroma_db"

    # App
    environment: str = "development"  # development | staging | production
    debug: bool = False
    allowed_origins: str = "http://localhost:5173,http://localhost:8081,tauri://localhost"
    rate_limit_enabled: bool = True
    enable_openapi: bool = True

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @field_validator("allowed_origins")
    @classmethod
    def strip_origins(cls, v: str) -> str:
        return ",".join(o.strip() for o in v.split(",") if o.strip())

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def validate_production_settings(s: Settings) -> None:
    """Fail fast when production is misconfigured."""
    if not s.is_production:
        return
    errors: list[str] = []
    if s.jwt_secret_key in INSECURE_JWT_PLACEHOLDERS or len(s.jwt_secret_key) < 32:
        errors.append("JWT_SECRET_KEY must be a strong secret (openssl rand -hex 32)")
    if "*" in s.allowed_origins.split(","):
        errors.append("ALLOWED_ORIGINS must not include '*' in production")
    if s.debug:
        errors.append("DEBUG must be false in production")
    if errors:
        raise RuntimeError("Production configuration invalid:\n  - " + "\n  - ".join(errors))


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
