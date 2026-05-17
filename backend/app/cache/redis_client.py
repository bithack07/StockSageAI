import json
from typing import Any, Optional

import redis.asyncio as aioredis
import redis as sync_redis

from app.config import settings

# Async client for FastAPI routes
async_redis: Optional[aioredis.Redis] = None

# Sync client for Celery tasks
redis_client: sync_redis.Redis = sync_redis.from_url(settings.redis_url, decode_responses=True)


async def get_async_redis() -> aioredis.Redis:
    global async_redis
    if async_redis is None:
        async_redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return async_redis


async def cache_get(key: str) -> Optional[Any]:
    r = await get_async_redis()
    val = await r.get(key)
    if val is None:
        return None
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return val


async def cache_set(key: str, value: Any, ttl: int = 300):
    r = await get_async_redis()
    serialized = json.dumps(value) if not isinstance(value, str) else value
    await r.setex(key, ttl, serialized)


async def cache_delete(key: str):
    r = await get_async_redis()
    await r.delete(key)


def cache_exists(key: str) -> bool:
    return bool(redis_client.exists(key))


def cache_set_sync(key: str, value: Any, ttl: int = 300):
    serialized = json.dumps(value) if not isinstance(value, str) else value
    redis_client.setex(key, ttl, serialized)


def cache_get_sync(key: str) -> Optional[Any]:
    val = redis_client.get(key)
    if val is None:
        return None
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return val
