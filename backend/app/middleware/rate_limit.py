"""Redis-backed rate limiting (in-memory fallback when Redis unavailable)."""
import logging
import time
from collections import defaultdict
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings

logger = logging.getLogger(__name__)

# path prefix -> (max_requests, window_seconds)
LIMITS: dict[str, tuple[int, int]] = {
    "/auth/login": (10, 60),
    "/auth/register": (5, 60),
    "/auth/refresh": (20, 60),
    "/ws/analyze": (30, 60),
}

_memory: dict[str, list[float]] = defaultdict(list)


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _match_limit(path: str) -> tuple[int, int] | None:
    for prefix, limit in LIMITS.items():
        if path.startswith(prefix):
            return limit
    return None


async def _redis_incr(key: str, window: int) -> int | None:
    try:
        from app.cache.redis_client import async_redis

        if not async_redis:
            return None
        pipe = async_redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        results = await pipe.execute()
        return int(results[0])
    except Exception as e:
        logger.debug("Rate limit Redis unavailable: %s", e)
        return None


def _memory_incr(key: str, window: int) -> int:
    now = time.time()
    bucket = _memory[key]
    _memory[key] = [t for t in bucket if now - t < window]
    _memory[key].append(now)
    return len(_memory[key])


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not settings.rate_limit_enabled:
            return await call_next(request)

        limit = _match_limit(request.url.path)
        if not limit:
            return await call_next(request)

        max_req, window = limit
        key = f"rl:{request.url.path}:{_client_key(request)}"
        count = await _redis_incr(key, window)
        if count is None:
            count = _memory_incr(key, window)

        if count > max_req:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
            )
        return await call_next(request)
