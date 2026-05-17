"""Stock screener — filter against pre-computed indicator table."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_db
from app.deps import get_current_user

router = APIRouter(prefix="/screener", tags=["screener"])


@router.get("")
async def run_screener(
    rsi_max: Optional[float] = Query(None, description="RSI below this value"),
    rsi_min: Optional[float] = Query(None, description="RSI above this value"),
    pe_max: Optional[float] = Query(None, description="P/E below this value"),
    pe_min: Optional[float] = Query(None, description="P/E above this value"),
    sentiment_min: Optional[float] = Query(None, description="Sentiment score above (0 to 1)"),
    limit: int = Query(20, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Screen stocks against pre-computed indicators.
    All filters are optional and ANDed together.
    """
    conditions = ["tf.timeframe = '1d'"]
    params: dict = {}

    if rsi_max is not None:
        conditions.append("tf.rsi < :rsi_max")
        params["rsi_max"] = rsi_max
    if rsi_min is not None:
        conditions.append("tf.rsi > :rsi_min")
        params["rsi_min"] = rsi_min
    if pe_max is not None:
        conditions.append("f.pe_ratio < :pe_max")
        params["pe_max"] = pe_max
    if pe_min is not None:
        conditions.append("f.pe_ratio > :pe_min")
        params["pe_min"] = pe_min
    if sentiment_min is not None:
        conditions.append("s.composite_score > :sent_min")
        params["sent_min"] = sentiment_min

    where = " AND ".join(conditions)
    params["limit"] = limit

    sql = f"""
        SELECT tf.symbol, tf.rsi, tf.macd, tf.ema20, tf.ema50,
               f.pe_ratio, f.roe, f.roce, f.market_cap,
               s.composite_score
        FROM technical_features tf
        LEFT JOIN fundamentals f ON f.symbol = tf.symbol
        LEFT JOIN sentiment s ON s.symbol = tf.symbol
            AND s.date = (SELECT MAX(date) FROM sentiment WHERE symbol = tf.symbol)
        WHERE tf.date = (SELECT MAX(date) FROM technical_features WHERE symbol = tf.symbol AND timeframe = '1d')
          AND {where}
        ORDER BY tf.rsi ASC NULLS LAST
        LIMIT :limit
    """

    result = await db.execute(text(sql), params)
    rows = result.fetchall()

    def _f(v):
        return round(float(v), 4) if v is not None else None

    return [
        {
            "symbol": r[0],
            "rsi": _f(r[1]),
            "macd": _f(r[2]),
            "ema20": _f(r[3]),
            "ema50": _f(r[4]),
            "pe_ratio": _f(r[5]),
            "roe": _f(r[6]),
            "roce": _f(r[7]),
            "market_cap": int(r[8]) if r[8] else None,
            "sentiment_score": _f(r[9]),
        }
        for r in rows
    ]
