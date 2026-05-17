"""On-demand symbol data refresh (sync fallback when Celery worker is not running)."""
import asyncio
import logging

from app.db import get_db

logger = logging.getLogger(__name__)


def _ohlcv_count(symbol: str) -> int:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ohlcv WHERE symbol = %s", (symbol,))
        return int(cur.fetchone()[0])


def _technical_features_count(symbol: str) -> int:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM technical_features WHERE symbol = %s AND timeframe = '1d'",
            (symbol,),
        )
        return int(cur.fetchone()[0])


def refresh_symbol_data_sync(symbol: str) -> dict:
    """Run ingestion pipelines synchronously via Celery task .run()."""
    from app.pipelines.market_data import ingest_ohlcv
    from app.pipelines.technical_features import compute_technical_features
    from app.pipelines.fundamentals import ingest_fundamentals
    from app.pipelines.sentiment_pipeline import run_sentiment_pipeline

    results: dict = {}
    try:
        results["ohlcv"] = ingest_ohlcv.run(symbol)
        results["technical"] = compute_technical_features.run(symbol)
        results["fundamentals"] = ingest_fundamentals.run(symbol)
        results["sentiment"] = run_sentiment_pipeline.run(symbol)
    except Exception as exc:
        logger.error("Sync data refresh failed for %s: %s", symbol, exc)
        results["error"] = str(exc)
    return results


async def ensure_symbol_data(symbol: str) -> bool:
    """Load OHLCV + derived features when the symbol has no cached rows."""
    has_ohlcv = _ohlcv_count(symbol) > 0
    if not has_ohlcv:
        logger.info("No OHLCV for %s — running sync data refresh", symbol)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, refresh_symbol_data_sync, symbol)
        has_ohlcv = _ohlcv_count(symbol) > 0
        if not has_ohlcv:
            logger.warning("Data refresh completed but OHLCV still empty for %s", symbol)
            return False

    if _technical_features_count(symbol) == 0:
        logger.info("OHLCV present but no technical features for %s — computing sync", symbol)
        from app.pipelines.technical_features import compute_technical_features

        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, compute_technical_features.run, symbol)
        except Exception as exc:
            logger.warning("Sync technical feature compute failed for %s: %s", symbol, exc)

    return True
