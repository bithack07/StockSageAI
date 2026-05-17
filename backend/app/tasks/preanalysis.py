"""Background pre-analysis for watchlist / favorites."""
import asyncio
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


def _run_async(coro):
    return asyncio.run(coro)


@shared_task(name="tasks.preanalysis.analyze_symbol")
def analyze_symbol(symbol: str):
    from app.services.preanalysis import run_preanalysis

    result = _run_async(run_preanalysis(symbol))
    return result


@shared_task(name="tasks.preanalysis.analyze_watchlist_all")
def analyze_all_watchlist_symbols():
    """Pre-analyze every distinct symbol on any user's watchlist."""
    from app.db import get_db
    from app.services.symbols import canonical_symbol

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT symbol FROM watchlist")
        symbols = [canonical_symbol(r[0]) for r in cur.fetchall()]

    unique = list(dict.fromkeys(symbols))
    for sym in unique:
        analyze_symbol.delay(sym)
    logger.info("Queued pre-analysis for %d watchlist symbols", len(unique))
    return {"queued": len(unique)}
