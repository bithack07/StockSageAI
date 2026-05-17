import os

import pytest

# Use safe test defaults before app imports settings
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only-32chars")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/stocksage",
)

from app.config import get_settings

get_settings.cache_clear()
