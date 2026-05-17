"""StockSage AI — FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings, validate_production_settings
from app.db import init_db
from app.logging_config import setup_logging
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security import SecurityHeadersMiddleware
from app.auth.router import router as auth_router
from app.api import (
    stocks_router,
    portfolio_router,
    watchlist_router,
    alerts_router,
    market_router,
    screener_router,
    analysis_router,
    ws_router,
    investor_router,
)

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_production_settings(settings)
    try:
        await init_db()
        logger.info("Database schema ready")
    except Exception as e:
        logger.error("Database init failed: %s", e)
        if settings.is_production:
            raise
        logger.warning("Continuing without DB (development only)")

    try:
        from app.cache.redis_client import get_async_redis
        await get_async_redis()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning("Redis unavailable: %s", e)

    yield

    try:
        from app.cache.redis_client import async_redis
        if async_redis:
            await async_redis.close()
    except Exception:
        pass


app = FastAPI(
    title="StockSage AI",
    description="Agentic Stock Analysis Platform — NSE/BSE predictions via multi-agent AI",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.enable_openapi and not settings.is_production else None,
    redoc_url="/redoc" if settings.enable_openapi and not settings.is_production else None,
    openapi_url="/openapi.json" if settings.enable_openapi and not settings.is_production else None,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router)
app.include_router(stocks_router)
app.include_router(portfolio_router)
app.include_router(watchlist_router)
app.include_router(alerts_router)
app.include_router(market_router)
app.include_router(screener_router)
app.include_router(analysis_router)
app.include_router(ws_router)
app.include_router(investor_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    detail = str(exc) if settings.debug else "Internal server error"
    return JSONResponse(status_code=500, content={"detail": detail})


@app.get("/health")
async def health():
    """Liveness probe — process is up."""
    return {"status": "ok", "service": "stocksage-ai", "version": "1.0.0"}


@app.get("/health/ready")
async def health_ready():
    """Readiness probe — dependencies available."""
    from app.health import full_health
    body = await full_health()
    status_code = 200 if body["status"] == "ok" else 503
    return JSONResponse(status_code=status_code, content=body)
