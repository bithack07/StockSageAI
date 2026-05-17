"""Run full multi-agent analysis without WebSocket (watchlist pre-cache)."""
import logging

from app.services.symbols import canonical_symbol

logger = logging.getLogger(__name__)


class _NoopWebSocket:
    """Swallows step_log events for background jobs."""

    async def send_json(self, _data: dict) -> None:
        return None


async def run_preanalysis(symbol: str) -> dict:
    """
    Load data if needed, run agents + orchestrator, persist to analyses table.
    Returns {ok, symbol, error?}.
    """
    from app.pipelines.data_refresh import ensure_symbol_data
    from app.agents.orchestrator import stream_analysis

    canon = canonical_symbol(symbol)
    try:
        if not await ensure_symbol_data(canon):
            logger.warning("Pre-analysis skipped — no OHLCV for %s", canon)
            return {"ok": False, "symbol": canon, "error": "no_market_data"}

        await stream_analysis(canon, _NoopWebSocket())
        logger.info("Pre-analysis completed for %s", canon)
        return {"ok": True, "symbol": canon}
    except Exception as exc:
        logger.exception("Pre-analysis failed for %s: %s", canon, exc)
        return {"ok": False, "symbol": canon, "error": str(exc)}
