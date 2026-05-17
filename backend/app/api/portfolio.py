"""Portfolio CRUD + analysis endpoint."""
import json
from datetime import date
from typing import Optional

import yfinance as yf
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_db
from app.deps import get_current_user
from app.services.symbols import canonical_symbol, symbol_display

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


class HoldingCreate(BaseModel):
    symbol: str
    quantity: float
    avg_buy_price: float
    buy_date: Optional[date] = None


@router.get("")
async def get_portfolio(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Fetch user's portfolio with live P&L."""
    # Get portfolio
    p_result = await db.execute(
        text("SELECT id, name FROM portfolios WHERE user_id = :uid LIMIT 1"),
        {"uid": user["id"]},
    )
    portfolio = p_result.fetchone()
    if not portfolio:
        return {
            "portfolio": None,
            "holdings": [],
            "total_invested": 0,
            "total_current_value": 0,
            "total_pnl": 0,
            "total_pnl_pct": 0,
        }

    h_result = await db.execute(
        text("SELECT id, symbol, quantity, avg_buy_price, buy_date FROM holdings WHERE portfolio_id = :pid"),
        {"pid": str(portfolio[0])},
    )
    holdings_rows = h_result.fetchall()

    holdings = []
    total_invested = 0.0
    total_current = 0.0

    for row in holdings_rows:
        holding_id, symbol, qty, avg_price, buy_date = row
        qty = float(qty or 0)
        avg_price = float(avg_price or 0)

        # Try to get current price from yfinance
        current_price = avg_price
        try:
            ticker = yf.Ticker(symbol)
            fast = ticker.fast_info
            current_price = float(getattr(fast, "last_price", None) or avg_price)
        except Exception:
            pass

        invested = qty * avg_price
        current_val = qty * current_price
        pnl = current_val - invested
        pnl_pct = (pnl / invested * 100) if invested > 0 else 0.0

        total_invested += invested
        total_current += current_val

        holdings.append({
            "id": str(holding_id),
            "symbol": symbol,
            "quantity": qty,
            "avg_buy_price": avg_price,
            "current_price": current_price,
            "current_value": round(current_val, 2),
            "invested_value": round(invested, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "buy_date": str(buy_date) if buy_date else None,
        })

    total_pnl = total_current - total_invested
    return {
        "portfolio_id": str(portfolio[0]),
        "portfolio_name": portfolio[1],
        "total_invested": round(total_invested, 2),
        "total_current_value": round(total_current, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round((total_pnl / total_invested * 100) if total_invested > 0 else 0, 2),
        "holdings": holdings,
    }


@router.post("", status_code=201)
async def add_holding(
    body: HoldingCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    p_result = await db.execute(
        text("SELECT id FROM portfolios WHERE user_id = :uid LIMIT 1"),
        {"uid": user["id"]},
    )
    portfolio = p_result.fetchone()
    if not portfolio:
        p_result = await db.execute(
            text("INSERT INTO portfolios (user_id, name) VALUES (:uid, 'My Portfolio') RETURNING id"),
            {"uid": user["id"]},
        )
        portfolio = p_result.fetchone()

    await db.execute(
        text(
            "INSERT INTO holdings (portfolio_id, symbol, quantity, avg_buy_price, buy_date) "
            "VALUES (:pid, :sym, :qty, :price, :bdate)"
        ),
        {
            "pid": str(portfolio[0]),
            "sym": canonical_symbol(body.symbol),
            "qty": body.quantity,
            "price": body.avg_buy_price,
            "bdate": body.buy_date,
        },
    )
    return {"message": "Holding added", "symbol": body.symbol.upper()}


@router.delete("/{holding_id}")
async def remove_holding(
    holding_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    # Ensure holding belongs to user
    result = await db.execute(
        text(
            "SELECT h.id FROM holdings h "
            "JOIN portfolios p ON p.id = h.portfolio_id "
            "WHERE h.id = :hid AND p.user_id = :uid"
        ),
        {"hid": holding_id, "uid": user["id"]},
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Holding not found")

    await db.execute(text("DELETE FROM holdings WHERE id = :hid"), {"hid": holding_id})
    return {"message": "Holding removed"}
