from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

import psycopg2
import psycopg2.extras
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Async engine for FastAPI endpoints
async_engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.debug,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@contextmanager
def get_db() -> Generator:
    """Sync psycopg2 connection for Celery pipeline tasks."""
    dsn = settings.database_url.replace("+asyncpg", "")
    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


async def init_db():
    """Create all tables from schema.sql on startup (one statement at a time)."""
    import os
    import re
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path) as f:
        raw = f.read()

    # Strip line comments before splitting so chunks that start with a comment
    # but contain real DDL are not incorrectly filtered out.
    raw_no_comments = re.sub(r"--[^\n]*", "", raw)
    statements = [s.strip() for s in raw_no_comments.split(";") if s.strip()]

    async with async_engine.begin() as conn:
        for stmt in statements:
            await conn.execute(text(stmt))
