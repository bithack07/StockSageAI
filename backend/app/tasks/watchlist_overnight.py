"""Overnight batch tasks for watchlist, fundamentals, and technical features."""
import logging

from celery import shared_task, group

from app.db import get_db

logger = logging.getLogger(__name__)


def _get_all_tracked() -> list[str]:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT symbol FROM tracked_tickers")
        return [r[0] for r in cur.fetchall()]


@shared_task(name="tasks.watchlist_overnight.compute_all_technical")
def compute_all_technical():
    from app.pipelines.technical_features import compute_technical_features
    symbols = _get_all_tracked()
    for sym in symbols:
        compute_technical_features.delay(sym)
    logger.info(f"Queued technical features for {len(symbols)} symbols")
    return {"queued": len(symbols)}


@shared_task(name="tasks.watchlist_overnight.run_all_sentiment")
def run_all_sentiment():
    from app.pipelines.sentiment_pipeline import run_sentiment_pipeline
    symbols = _get_all_tracked()
    for sym in symbols:
        run_sentiment_pipeline.delay(sym)
    logger.info(f"Queued sentiment pipeline for {len(symbols)} symbols")
    return {"queued": len(symbols)}


@shared_task(name="tasks.watchlist_overnight.refresh_all_fundamentals")
def refresh_all_fundamentals():
    from app.pipelines.fundamentals import ingest_fundamentals
    symbols = _get_all_tracked()
    for sym in symbols:
        ingest_fundamentals.delay(sym)
    logger.info(f"Queued fundamentals for {len(symbols)} symbols")
    return {"queued": len(symbols)}
