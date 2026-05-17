"""Watchlist CRUD + pre-analysis previews."""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_db
from app.deps import get_current_user
from app.services.symbols import canonical_symbol, symbol_display, symbols_equivalent
from app.pipelines.market_data import get_latest_quote

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class WatchlistAdd(BaseModel):
    symbol: str


def _in_clause(variants: list[str]) -> tuple[str, dict]:
    if not variants:
        return "FALSE", {}
    keys = [f"v{i}" for i in range(len(variants))]
    clause = ", ".join(f":{k}" for k in keys)
    params = {k: v for k, v in zip(keys, variants)}
    return f"symbol IN ({clause})", params


async def _fetch_analysis_preview(db: AsyncSession, symbol: str) -> dict | None:
    from app.services.symbols import match_variants

    variants = match_variants(symbol)
    where_sql, params = _in_clause(variants)
    result = await db.execute(
        text(
            f"""
            SELECT prediction_json, created_at
            FROM analyses
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        params,
    )
    row = result.fetchone()
    if not row or not row[0]:
        return None
    pred = row[0]
    if isinstance(pred, str):
        pred = json.loads(pred)
    return {
        "direction": pred.get("direction"),
        "conviction": pred.get("conviction"),
        "confidence_pct": pred.get("confidence_pct"),
        "analyzed_at": str(row[1]),
        "status": "ready",
    }


def _enrich_watchlist_row(row, preview: dict | None, quote: dict | None) -> dict:
    sym = canonical_symbol(row[1])
    name = (quote or {}).get("name") or sym
    disp = symbol_display(sym, name)
    out = {
        "id": str(row[0]),
        "symbol": sym,
        "added_at": str(row[2]),
        **disp,
        "preview": preview or {"status": "pending"},
    }
    if quote:
        out["price"] = quote.get("price")
        out["change_pct"] = quote.get("change_pct")
    return out


@router.get("")
async def get_watchlist(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        text("SELECT id, symbol, added_at FROM watchlist WHERE user_id = :uid ORDER BY added_at DESC"),
        {"uid": user["id"]},
    )
    rows = result.fetchall()
    items = []
    for row in rows:
        sym = canonical_symbol(row[1])
        preview = await _fetch_analysis_preview(db, sym)
        quote = None
        try:
            quote = get_latest_quote(sym)
        except Exception:
            pass
        items.append(_enrich_watchlist_row(row, preview, quote))
    return items


@router.post("", status_code=201)
async def add_to_watchlist(
    body: WatchlistAdd,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    canon = canonical_symbol(body.symbol)

    existing = await db.execute(
        text("SELECT id, symbol FROM watchlist WHERE user_id = :uid"),
        {"uid": user["id"]},
    )
    for row in existing.fetchall():
        if symbols_equivalent(row[1], canon):
            disp = symbol_display(canon)
            raise HTTPException(
                status_code=400,
                detail=f"Already on your watchlist as {disp['short_label']} ({row[1]} stored)",
            )

    try:
        await db.execute(
            text("INSERT INTO watchlist (user_id, symbol) VALUES (:uid, :sym)"),
            {"uid": user["id"], "sym": canon},
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Could not add symbol")

    try:
        from app.tasks.preanalysis import analyze_symbol
        analyze_symbol.delay(canon)
    except Exception as exc:
        logger.debug("Pre-analysis queue skipped: %s", exc)

    disp = symbol_display(canon)
    return {
        "message": "Added to watchlist — pre-analysis queued",
        "symbol": canon,
        **disp,
    }


@router.post("/refresh-preanalysis")
async def refresh_watchlist_preanalysis(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Queue fresh AI analysis for all symbols on this user's watchlist."""
    result = await db.execute(
        text("SELECT symbol FROM watchlist WHERE user_id = :uid"),
        {"uid": user["id"]},
    )
    symbols = list({canonical_symbol(r[0]) for r in result.fetchall()})
    try:
        from app.tasks.preanalysis import analyze_symbol
        for sym in symbols:
            analyze_symbol.delay(sym)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Worker unavailable: {exc}")
    return {"message": f"Pre-analysis queued for {len(symbols)} symbols", "symbols": symbols}


@router.delete("/{watchlist_id}")
async def remove_from_watchlist(
    watchlist_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        text("DELETE FROM watchlist WHERE id = :wid AND user_id = :uid RETURNING id"),
        {"wid": watchlist_id, "uid": user["id"]},
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    return {"message": "Removed from watchlist"}
