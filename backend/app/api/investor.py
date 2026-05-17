"""Value-investing endpoints — India (NSE/BSE) focused."""
import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_db
from app.deps import get_current_user
from app.services.india_market import normalize_nse_symbol
from app.services.value_investing import (
    compare_to_benchmarks,
    compute_intrinsic_value_band,
    compute_quality_score,
    earnings_calendar_for_symbols,
    portfolio_insights,
)

router = APIRouter(prefix="/investor", tags=["investor"])


class InvestorProfileUpdate(BaseModel):
    net_worth_inr: Optional[float] = Field(None, ge=0)
    annual_fd_rate_pct: Optional[float] = Field(None, ge=0, le=20)


class OwnerChecklistUpdate(BaseModel):
    moat_rating: Optional[int] = Field(None, ge=1, le=5)
    management_rating: Optional[int] = Field(None, ge=1, le=5)
    circle_of_competence: Optional[bool] = None
    understand_business: Optional[bool] = None
    comfortable_10y: Optional[bool] = None
    notes: Optional[str] = None


class ThesisUpdate(BaseModel):
    thesis_text: Optional[str] = None
    moat_notes: Optional[str] = None
    management_notes: Optional[str] = None
    ten_year_thesis: Optional[str] = None


async def _get_profile(db: AsyncSession, user_id: str) -> dict:
    r = await db.execute(
        text("SELECT net_worth_inr, annual_fd_rate_pct FROM user_investor_profile WHERE user_id = :uid"),
        {"uid": user_id},
    )
    row = r.fetchone()
    if not row:
        return {"net_worth_inr": None, "annual_fd_rate_pct": 7.0, "currency": "INR"}
    return {
        "net_worth_inr": float(row[0]) if row[0] is not None else None,
        "annual_fd_rate_pct": float(row[1]) if row[1] is not None else 7.0,
        "currency": "INR",
    }


@router.get("/profile")
async def get_investor_profile(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await _get_profile(db, user["id"])


@router.patch("/profile")
async def update_investor_profile(
    body: InvestorProfileUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    existing = await _get_profile(db, user["id"])
    nw = body.net_worth_inr if body.net_worth_inr is not None else existing["net_worth_inr"]
    fd = body.annual_fd_rate_pct if body.annual_fd_rate_pct is not None else existing["annual_fd_rate_pct"]
    await db.execute(
        text(
            """INSERT INTO user_investor_profile (user_id, net_worth_inr, annual_fd_rate_pct, updated_at)
               VALUES (:uid, :nw, :fd, NOW())
               ON CONFLICT (user_id) DO UPDATE
               SET net_worth_inr = EXCLUDED.net_worth_inr,
                   annual_fd_rate_pct = EXCLUDED.annual_fd_rate_pct,
                   updated_at = NOW()"""
        ),
        {"uid": user["id"], "nw": nw, "fd": fd},
    )
    return await _get_profile(db, user["id"])


@router.get("/stocks/{symbol}/valuation")
async def stock_valuation(symbol: str, user: dict = Depends(get_current_user)):
    sym = normalize_nse_symbol(symbol)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, compute_intrinsic_value_band, sym)


@router.get("/stocks/{symbol}/quality")
async def stock_quality(symbol: str, user: dict = Depends(get_current_user)):
    sym = normalize_nse_symbol(symbol)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, compute_quality_score, sym)


@router.get("/stocks/{symbol}/buffett-kit")
async def stock_buffett_kit(symbol: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_async_db)):
    """Combined valuation + quality + benchmark + checklist for one NSE/BSE symbol."""
    sym = normalize_nse_symbol(symbol)
    profile = await _get_profile(db, user["id"])
    loop = asyncio.get_event_loop()
    valuation, quality, benchmark = await asyncio.gather(
        loop.run_in_executor(None, compute_intrinsic_value_band, sym),
        loop.run_in_executor(None, compute_quality_score, sym),
        loop.run_in_executor(None, compare_to_benchmarks, sym, profile["annual_fd_rate_pct"]),
    )
    cl = await db.execute(
        text(
            """SELECT moat_rating, management_rating, circle_of_competence,
                      understand_business, comfortable_10y, notes
               FROM symbol_owner_checklist WHERE user_id = :uid AND symbol = :sym"""
        ),
        {"uid": user["id"], "sym": sym},
    )
    row = cl.fetchone()
    checklist = None
    if row:
        checklist = {
            "moat_rating": row[0],
            "management_rating": row[1],
            "circle_of_competence": row[2],
            "understand_business": row[3],
            "comfortable_10y": row[4],
            "notes": row[5],
        }
    return {
        "symbol": sym,
        "market": "India (NSE/BSE)",
        "valuation": valuation,
        "quality": quality,
        "benchmark": benchmark,
        "owner_checklist": checklist,
    }


@router.get("/stocks/{symbol}/checklist")
async def get_checklist(
    symbol: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    sym = normalize_nse_symbol(symbol)
    r = await db.execute(
        text(
            """SELECT moat_rating, management_rating, circle_of_competence,
                      understand_business, comfortable_10y, notes
               FROM symbol_owner_checklist WHERE user_id = :uid AND symbol = :sym"""
        ),
        {"uid": user["id"], "sym": sym},
    )
    row = r.fetchone()
    if not row:
        return {"symbol": sym, "checklist": None}
    return {
        "symbol": sym,
        "checklist": {
            "moat_rating": row[0],
            "management_rating": row[1],
            "circle_of_competence": row[2],
            "understand_business": row[3],
            "comfortable_10y": row[4],
            "notes": row[5],
        },
    }


@router.put("/stocks/{symbol}/checklist")
async def put_checklist(
    symbol: str,
    body: OwnerChecklistUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    sym = normalize_nse_symbol(symbol)
    await db.execute(
        text(
            """INSERT INTO symbol_owner_checklist
               (user_id, symbol, moat_rating, management_rating, circle_of_competence,
                understand_business, comfortable_10y, notes, updated_at)
               VALUES (:uid, :sym, :moat, :mgmt, :coc, :ub, :c10, :notes, NOW())
               ON CONFLICT (user_id, symbol) DO UPDATE SET
                 moat_rating = COALESCE(EXCLUDED.moat_rating, symbol_owner_checklist.moat_rating),
                 management_rating = COALESCE(EXCLUDED.management_rating, symbol_owner_checklist.management_rating),
                 circle_of_competence = COALESCE(EXCLUDED.circle_of_competence, symbol_owner_checklist.circle_of_competence),
                 understand_business = COALESCE(EXCLUDED.understand_business, symbol_owner_checklist.understand_business),
                 comfortable_10y = COALESCE(EXCLUDED.comfortable_10y, symbol_owner_checklist.comfortable_10y),
                 notes = COALESCE(EXCLUDED.notes, symbol_owner_checklist.notes),
                 updated_at = NOW()"""
        ),
        {
            "uid": user["id"],
            "sym": sym,
            "moat": body.moat_rating,
            "mgmt": body.management_rating,
            "coc": body.circle_of_competence,
            "ub": body.understand_business,
            "c10": body.comfortable_10y,
            "notes": body.notes,
        },
    )
    return await get_checklist(sym, user, db)


@router.get("/portfolio/insights")
async def get_portfolio_insights(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    from app.api.portfolio import get_portfolio

    port = await get_portfolio(user, db)
    profile = await _get_profile(db, user["id"])
    loop = asyncio.get_event_loop()
    insights = await loop.run_in_executor(
        None,
        portfolio_insights,
        port.get("holdings") or [],
        profile.get("net_worth_inr"),
    )
    return {**insights, "portfolio_summary": {
        "total_invested": port.get("total_invested"),
        "total_current_value": port.get("total_current_value"),
        "total_pnl_pct": port.get("total_pnl_pct"),
    }}


@router.get("/watchlist/earnings-calendar")
async def watchlist_earnings(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    r = await db.execute(
        text("SELECT symbol FROM watchlist WHERE user_id = :uid ORDER BY added_at"),
        {"uid": user["id"]},
    )
    symbols = [row[0] for row in r.fetchall()]
    loop = asyncio.get_event_loop()
    events = await loop.run_in_executor(None, earnings_calendar_for_symbols, symbols)
    return {"events": events, "market": "India (NSE/BSE)", "count": len(events)}


@router.get("/holdings/{holding_id}/thesis")
async def get_thesis(
    holding_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    r = await db.execute(
        text(
            """SELECT h.symbol, t.thesis_text, t.moat_notes, t.management_notes, t.ten_year_thesis, t.updated_at
               FROM holdings h
               JOIN portfolios p ON p.id = h.portfolio_id
               LEFT JOIN holding_thesis t ON t.holding_id = h.id
               WHERE h.id = :hid AND p.user_id = :uid"""
        ),
        {"hid": holding_id, "uid": user["id"]},
    )
    row = r.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Holding not found")
    return {
        "holding_id": holding_id,
        "symbol": row[0],
        "thesis": {
            "thesis_text": row[1],
            "moat_notes": row[2],
            "management_notes": row[3],
            "ten_year_thesis": row[4],
            "updated_at": str(row[5]) if row[5] else None,
        },
    }


@router.put("/holdings/{holding_id}/thesis")
async def put_thesis(
    holding_id: str,
    body: ThesisUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    r = await db.execute(
        text(
            """SELECT h.id FROM holdings h
               JOIN portfolios p ON p.id = h.portfolio_id
               WHERE h.id = :hid AND p.user_id = :uid"""
        ),
        {"hid": holding_id, "uid": user["id"]},
    )
    if not r.fetchone():
        raise HTTPException(status_code=404, detail="Holding not found")

    await db.execute(
        text(
            """INSERT INTO holding_thesis (holding_id, thesis_text, moat_notes, management_notes, ten_year_thesis, updated_at)
               VALUES (:hid, :t, :m, :mgmt, :y10, NOW())
               ON CONFLICT (holding_id) DO UPDATE SET
                 thesis_text = COALESCE(EXCLUDED.thesis_text, holding_thesis.thesis_text),
                 moat_notes = COALESCE(EXCLUDED.moat_notes, holding_thesis.moat_notes),
                 management_notes = COALESCE(EXCLUDED.management_notes, holding_thesis.management_notes),
                 ten_year_thesis = COALESCE(EXCLUDED.ten_year_thesis, holding_thesis.ten_year_thesis),
                 updated_at = NOW()"""
        ),
        {
            "hid": holding_id,
            "t": body.thesis_text,
            "m": body.moat_notes,
            "mgmt": body.management_notes,
            "y10": body.ten_year_thesis,
        },
    )
    return await get_thesis(holding_id, user, db)
