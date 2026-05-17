"""Pipeline 1 — Market Data Ingestion via yfinance."""
import logging
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf
from celery import shared_task

from app.cache import redis_client
from app.db import get_db

logger = logging.getLogger(__name__)

NIFTY_50_SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "HINDUNILVR.NS",
    "ICICIBANK.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "LT.NS", "SBIN.NS",
    "BAJFINANCE.NS", "ASIANPAINT.NS", "AXISBANK.NS", "MARUTI.NS", "TITAN.NS",
    "NESTLEIND.NS", "HCLTECH.NS", "WIPRO.NS", "SUNPHARMA.NS", "ULTRACEMCO.NS",
    "BAJAJFINSV.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "TECHM.NS",
    "TMPV.NS", "INDUSINDBK.NS", "DIVISLAB.NS", "CIPLA.NS", "JSWSTEEL.NS",
    "HINDALCO.NS", "BPCL.NS", "COALINDIA.NS", "DRREDDY.NS", "ADANIPORTS.NS",
    "BRITANNIA.NS", "EICHERMOT.NS", "GRASIM.NS", "HEROMOTOCO.NS", "M&M.NS",
    "TATASTEEL.NS", "TATACONSUM.NS", "UPL.NS", "VEDL.NS", "SHREECEM.NS",
    "APOLLOHOSP.NS", "BAJAJ-AUTO.NS", "SBILIFE.NS", "HDFCLIFE.NS", "ADANIENT.NS",
]


@shared_task(name="pipelines.market_data.ingest_ohlcv", bind=True, max_retries=3)
def ingest_ohlcv(self, symbol: str, period: str = "5y"):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval="1d")
        if df.empty:
            logger.warning(f"No data returned for {symbol}")
            return {"symbol": symbol, "rows": 0}

        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        df["date"] = pd.to_datetime(df["date"]).dt.date

        with get_db() as conn:
            cur = conn.cursor()
            # Ensure ticker is tracked
            cur.execute(
                "INSERT INTO tracked_tickers (symbol) VALUES (%s) ON CONFLICT DO NOTHING",
                (symbol,),
            )
            for _, row in df.iterrows():
                cur.execute(
                    """INSERT INTO ohlcv (symbol, date, open, high, low, close, volume)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (symbol, date) DO UPDATE
                       SET open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
                           close=EXCLUDED.close, volume=EXCLUDED.volume""",
                    (
                        symbol,
                        row["date"],
                        float(row.get("open", 0) or 0),
                        float(row.get("high", 0) or 0),
                        float(row.get("low", 0) or 0),
                        float(row.get("close", 0) or 0),
                        int(row.get("volume", 0) or 0),
                    ),
                )

        # Cache latest close (60s TTL)
        latest_close = float(df.iloc[-1]["close"])
        redis_client.setex(f"quote:{symbol}", 60, str(latest_close))

        logger.info(f"Ingested {len(df)} rows for {symbol}")
        return {"symbol": symbol, "rows": len(df)}

    except Exception as exc:
        logger.error(f"ingest_ohlcv failed for {symbol}: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(name="pipelines.market_data.ingest_all_tracked")
def ingest_all_tracked():
    """Nightly task: refresh OHLCV for all tracked tickers."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT symbol FROM tracked_tickers")
        symbols = [row[0] for row in cur.fetchall()]

    if not symbols:
        symbols = NIFTY_50_SYMBOLS

    results = []
    for sym in symbols:
        result = ingest_ohlcv.delay(sym, period="5y")
        results.append(result.id)

    return {"queued": len(results)}


@shared_task(name="pipelines.market_data.get_intraday")
def get_intraday(symbol: str, interval: str = "15m"):
    """Fetch intraday candles. yfinance provides 60 days for <=1h, 7 days for <1h."""
    period = "60d" if interval in ("1h", "30m") else "7d"
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval)
    if df.empty:
        return []
    df = df.reset_index()
    df.columns = [c.lower() for c in df.columns]
    return df[["datetime", "open", "high", "low", "close", "volume"]].to_dict(orient="records")


def get_latest_quote(symbol: str) -> dict:
    """Real-time quote: try Redis cache first, fall back to yfinance."""
    cached = redis_client.get(f"quote:{symbol}")
    if cached:
        return {"symbol": symbol, "price": float(cached), "source": "cache"}

    ticker = yf.Ticker(symbol)
    info = ticker.fast_info
    price = getattr(info, "last_price", None) or getattr(info, "regularMarketPrice", None)
    if price:
        redis_client.setex(f"quote:{symbol}", 60, str(price))
        return {
            "symbol": symbol,
            "price": price,
            "change_pct": getattr(info, "regular_market_change_percent", 0),
            "volume": getattr(info, "regular_market_volume", 0),
            "source": "live",
        }
    return {"symbol": symbol, "price": None, "source": "unavailable"}
