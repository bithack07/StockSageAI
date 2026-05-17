"""Health and readiness probes for load balancers."""
import logging

from sqlalchemy import text

from app.config import settings

logger = logging.getLogger(__name__)


async def check_database() -> dict:
    try:
        from app.db.connection import async_engine

        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        logger.warning("DB health check failed: %s", e)
        return {"status": "error", "detail": str(e) if settings.debug else "unavailable"}


async def check_redis() -> dict:
    try:
        from app.cache.redis_client import async_redis

        if not async_redis:
            return {"status": "skipped", "detail": "not configured"}
        await async_redis.ping()
        return {"status": "ok"}
    except Exception as e:
        logger.warning("Redis health check failed: %s", e)
        return {"status": "error", "detail": str(e) if settings.debug else "unavailable"}


async def full_health() -> dict:
    db = await check_database()
    redis = await check_redis()
    checks = {"database": db, "redis": redis}
    critical_ok = db["status"] == "ok"
    overall = "ok" if critical_ok else "degraded"
    return {
        "status": overall,
        "service": "stocksage-ai",
        "version": "1.0.0",
        "environment": settings.environment,
        "checks": checks,
    }
