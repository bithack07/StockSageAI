"""Market overview endpoint — Nifty indices, sector data, movers."""
import asyncio

import yfinance as yf
from fastapi import APIRouter, Depends, Query

from app.cache import cache_delete, cache_get, cache_set
from app.deps import get_current_user
from app.market_hours import get_nse_market_status

router = APIRouter(prefix="/market", tags=["market"])

INDICES = {
    "NIFTY_50": "^NSEI",
    "NIFTY_BANK": "^NSEBANK",
    "NIFTY_IT": "^CNXIT",
    "NIFTY_PHARMA": "^CNXPHARMA",
    "NIFTY_AUTO": "^CNXAUTO",
    "NIFTY_FMCG": "^CNXFMCG",
    "SENSEX": "^BSESN",
}


def _fetch_index(name: str, symbol: str) -> dict:
    try:
        ticker = yf.Ticker(symbol)
        fast = ticker.fast_info
        hist = ticker.history(period="1y", interval="1d")
        rsi = None
        if not hist.empty and len(hist) >= 14:
            from ta.momentum import RSIIndicator
            rsi_series = RSIIndicator(close=hist["Close"], window=14).rsi()
            if rsi_series is not None and not rsi_series.empty:
                rsi = round(float(rsi_series.iloc[-1]), 2)

        return {
            "name": name,
            "symbol": symbol,
            "price": round(float(getattr(fast, "last_price", 0) or 0), 2),
            "change_pct": round(float(getattr(fast, "regular_market_change_percent", 0) or 0), 2),
            "52w_high": round(float(getattr(fast, "year_high", 0) or 0), 2),
            "52w_low": round(float(getattr(fast, "year_low", 0) or 0), 2),
            "rsi": rsi,
        }
    except Exception:
        return {"name": name, "symbol": symbol, "price": None}


@router.get("/overview")
async def market_overview(
    user: dict = Depends(get_current_user),
    force: bool = Query(False, description="Bypass Redis cache and fetch live quotes"),
):
    """Nifty indices + sector data + top movers."""
    cache_key = "market_overview:v2"
    if not force:
        cached = await cache_get(cache_key)
        if cached:
            return cached
    else:
        await cache_delete(cache_key)

    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(None, _fetch_index, name, sym)
        for name, sym in INDICES.items()
    ]
    indices_data = await asyncio.gather(*tasks)

    session = get_nse_market_status()
    result = {
        "indices": list(indices_data),
        "market_status": session["market_status"],
        "session": session.get("session"),
        "next_open_hint": session.get("next_open_hint"),
    }

    await cache_set(cache_key, result, ttl=300)  # 5 min cache
    return result
