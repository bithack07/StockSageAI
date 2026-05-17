"""Stock search, quote, history, and analysis endpoints."""
import json
from typing import Optional

import yfinance as yf
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import cache_get, cache_set
from app.db import get_async_db
from app.deps import get_current_user
from app.pipelines.market_data import get_latest_quote
from app.services.analysis_freshness import analysis_ttl_minutes, build_latest_payload
from app.services.symbols import canonical_symbol, dedupe_search_results, match_variants, symbol_display

router = APIRouter(prefix="/stocks", tags=["stocks"])


def _resolve_symbol(symbol: str) -> str:
    return canonical_symbol(symbol)


@router.get("/search")
async def search_stocks(
    q: str = Query(..., min_length=1),
    user: dict = Depends(get_current_user),
):
    """Search for stocks by name or symbol. Returns top 10 matches."""
    cache_key = f"search:{q.lower()}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    try:
        results = yf.Search(q, max_results=10)
        quotes = results.quotes if hasattr(results, "quotes") else []
        data = [
            {
                "symbol": r.get("symbol"),
                "name": r.get("longname") or r.get("shortname"),
                "exchange": r.get("exchange"),
                "type": r.get("quoteType"),
            }
            for r in quotes
            if r.get("symbol")
        ]
        data = dedupe_search_results(data)
    except Exception:
        canon = canonical_symbol(q)
        data = [symbol_display(canon, q)]

    await cache_set(cache_key, data, ttl=600)
    return data


@router.get("/{symbol}/quote")
async def get_quote(
    symbol: str,
    user: dict = Depends(get_current_user),
):
    """Latest real-time quote (Redis cached 60s)."""
    symbol = _resolve_symbol(symbol)
    cache_key = f"quote_full:{symbol}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    quote = get_latest_quote(symbol)
    quote.update(symbol_display(symbol, quote.get("name")))
    await cache_set(cache_key, quote, ttl=60)
    return quote


@router.get("/{symbol}/history")
async def get_history(
    symbol: str,
    period: str = Query("1mo", pattern="^(1d|5d|1mo|3mo|6mo|1y|2y|5y|10y|ytd|max)$"),
    interval: str = Query("1d", pattern="^(1m|2m|5m|15m|30m|60m|90m|1h|1d|5d|1wk|1mo|3mo)$"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """OHLCV history. Serves from DB if available, falls back to yfinance live."""
    symbol = _resolve_symbol(symbol)
    if interval == "1d" and period in ("1mo", "3mo", "6mo", "1y", "2y", "5y"):
        result = await db.execute(
            text(
                "SELECT date, open, high, low, close, volume FROM ohlcv "
                "WHERE symbol = :sym ORDER BY date DESC LIMIT 1250"
            ),
            {"sym": symbol},
        )
        rows = result.fetchall()
        if rows:
            return [
                {"date": str(r[0]), "open": float(r[1] or 0), "high": float(r[2] or 0),
                 "low": float(r[3] or 0), "close": float(r[4] or 0), "volume": int(r[5] or 0)}
                for r in reversed(rows)
            ]

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        cols = [c for c in ["date", "datetime", "open", "high", "low", "close", "volume"] if c in df.columns]
        return df[cols].to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/analysis/latest")
async def get_latest_analysis(
    symbol: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Last cached analysis for a ticker (matches INFY, INFY.NS, etc.)."""
    canon = _resolve_symbol(symbol)
    variants = match_variants(canon)
    keys = [f"v{i}" for i in range(len(variants))]
    in_clause = ", ".join(f":{k}" for k in keys)
    params = {k: v for k, v in zip(keys, variants)}
    result = await db.execute(
        text(
            "SELECT id, symbol, created_at, fundamental_json, technical_json, sentiment_json, prediction_json "
            f"FROM analyses WHERE symbol IN ({in_clause}) ORDER BY created_at DESC LIMIT 1"
        ),
        params,
    )
    row = result.fetchone()
    if not row:
        return {
            "symbol": canon,
            "analysis": None,
            "fresh": False,
            "stale": False,
            "age_minutes": None,
            "ttl_minutes": analysis_ttl_minutes(),
            "expires_in_minutes": None,
            **symbol_display(canon),
        }

    return build_latest_payload(row, canon, symbol_display(canon))


@router.get("/{symbol}/playbook")
async def get_analysis_playbook(
    symbol: str,
    user: dict = Depends(get_current_user),
):
    """
    Golden-rules technical + fundamental playbook for a symbol.
    Encodes Stock_Analysis_Complete_Note.md.pdf (Graham, Lynch, Murphy, Weinstein, etc.).
    """
    sym = _resolve_symbol(symbol)
    cache_key = f"playbook:{sym}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    try:
        from app.services.analysis_playbook import compute_unified_playbook

        data = compute_unified_playbook(sym)
        data.update(symbol_display(sym))
        await cache_set(cache_key, data, ttl=300)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
