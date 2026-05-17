"""Price and indicator alert CRUD."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_db
from app.deps import get_current_user

router = APIRouter(prefix="/alerts", tags=["alerts"])

AlertCondition = Literal[
    "price_above", "price_below", "rsi_above", "rsi_below",
    "macd_crossover", "sentiment_drop", "earnings_date",
]


class AlertCreate(BaseModel):
    symbol: str
    condition: AlertCondition
    threshold: Optional[float] = None


@router.get("")
async def list_alerts(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        text(
            "SELECT id, symbol, condition, threshold, is_active, created_at "
            "FROM alerts WHERE user_id = :uid ORDER BY created_at DESC"
        ),
        {"uid": user["id"]},
    )
    rows = result.fetchall()
    return [
        {
            "id": str(r[0]),
            "symbol": r[1],
            "condition": r[2],
            "threshold": float(r[3]) if r[3] else None,
            "is_active": r[4],
            "created_at": str(r[5]),
        }
        for r in rows
    ]


@router.post("", status_code=201)
async def create_alert(
    body: AlertCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    await db.execute(
        text(
            "INSERT INTO alerts (user_id, symbol, condition, threshold) "
            "VALUES (:uid, :sym, :cond, :thresh)"
        ),
        {
            "uid": user["id"],
            "sym": body.symbol.upper(),
            "cond": body.condition,
            "thresh": body.threshold,
        },
    )
    return {"message": "Alert created", "symbol": body.symbol.upper(), "condition": body.condition}


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        text("DELETE FROM alerts WHERE id = :aid AND user_id = :uid RETURNING id"),
        {"aid": alert_id, "uid": user["id"]},
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"message": "Alert deleted"}
