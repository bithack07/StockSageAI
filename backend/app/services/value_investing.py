"""Buffett-style metrics for Indian equities — valuation, quality, portfolio, benchmarks."""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from typing import Any, Optional

import yfinance as yf

from app.services.india_market import (
    DEFAULT_FD_RATE_PCT,
    NIFTY_50_SYMBOL,
    NIFTY_SECTOR_MAP,
    base_ticker,
    normalize_nse_symbol,
)

logger = logging.getLogger(__name__)

CONCENTRATION_STOCK_WARN_PCT = 25.0
CONCENTRATION_SECTOR_WARN_PCT = 40.0


def _safe_float(v) -> Optional[float]:
    try:
        f = float(v)
        return None if f != f else f
    except (TypeError, ValueError):
        return None


def _load_fundamentals(symbol: str) -> dict:
    """Postgres fundamentals when available; empty dict for Kaggle/offline training."""
    sym = normalize_nse_symbol(symbol)
    try:
        from app.db import get_db

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT pe_ratio, pb_ratio, roe, roce, debt_equity, fcf, dcf_intrinsic,
                          market_cap, promoter_pct, ratios_json
                   FROM fundamentals WHERE symbol = %s""",
                (sym,),
            )
            row = cur.fetchone()
    except Exception as exc:
        logger.debug("Fundamentals DB unavailable for %s: %s", sym, exc)
        return {}
    if not row:
        return {}
    ratios = {}
    if row[9]:
        try:
            ratios = json.loads(row[9]) if isinstance(row[9], str) else row[9]
        except json.JSONDecodeError:
            pass
    return {
        "symbol": sym,
        "pe_ratio": _safe_float(row[0]),
        "pb_ratio": _safe_float(row[1]),
        "roe": _safe_float(row[2]),
        "roce": _safe_float(row[3]),
        "debt_equity": _safe_float(row[4]),
        "fcf": _safe_float(row[5]),
        "dcf_intrinsic": _safe_float(row[6]),
        "market_cap": _safe_float(row[7]),
        "promoter_pct": _safe_float(row[8]),
        "ratios_json": ratios,
    }


def _yf_snapshot(symbol: str) -> dict:
    sym = normalize_nse_symbol(symbol)
    try:
        t = yf.Ticker(sym)
        info = t.info or {}
        price = _safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
        shares = _safe_float(info.get("sharesOutstanding"))
        eps = _safe_float(info.get("trailingEps"))
        return {
            "symbol": sym,
            "price": price,
            "shares_outstanding": shares,
            "eps": eps,
            "pe_ratio": _safe_float(info.get("trailingPE")),
            "pb_ratio": _safe_float(info.get("priceToBook")),
            "roe": _safe_float(info.get("returnOnEquity")),
            "debt_equity": _safe_float(info.get("debtToEquity")),
            "revenue_growth": _safe_float(info.get("revenueGrowth")),
            "earnings_growth": _safe_float(info.get("earningsGrowth")),
            "sector": info.get("sector") or NIFTY_SECTOR_MAP.get(base_ticker(sym), "Other"),
            "industry": info.get("industry"),
            "held_percent_insiders": _safe_float(info.get("heldPercentInsiders")),
            "market_cap": _safe_float(info.get("marketCap")),
            "book_value": _safe_float(info.get("bookValue")),
        }
    except Exception as e:
        logger.warning("yfinance snapshot failed for %s: %s", sym, e)
        return {"symbol": sym}


def _return_1y(symbol: str) -> Optional[float]:
    try:
        hist = yf.Ticker(normalize_nse_symbol(symbol)).history(period="1y", interval="1d")
        if hist is None or len(hist) < 2:
            return None
        start = float(hist["Close"].iloc[0])
        end = float(hist["Close"].iloc[-1])
        if start <= 0:
            return None
        return round((end / start - 1) * 100, 2)
    except Exception:
        return None


def compute_intrinsic_value_band(symbol: str) -> dict:
    """DCF + Graham number + earnings-yield fair value band in INR per share."""
    from app.services.intelligent_investor import compute_graham_analysis, graham_number, margin_of_safety_pct

    sym = normalize_nse_symbol(symbol)
    fund = _load_fundamentals(sym)
    snap = _yf_snapshot(sym)
    price = snap.get("price")
    shares = snap.get("shares_outstanding")
    eps = snap.get("eps") or (fund.get("ratios_json") or {}).get("eps")
    bvps = snap.get("book_value")
    dcf_total = fund.get("dcf_intrinsic")
    gnum = graham_number(eps, bvps)

    dcf_per_share = None
    if dcf_total and shares and shares > 0:
        dcf_per_share = round(dcf_total / shares, 2)

    # Earnings yield fair value: EPS × fair P/E (sector-aware conservative)
    fair_pe = 18.0
    sector = (fund.get("ratios_json") or {}).get("sector") or snap.get("sector") or ""
    if sector in ("Financial Services", "Financials", "Banks"):
        fair_pe = 14.0
    elif sector in ("Information Technology", "IT"):
        fair_pe = 22.0
    elif sector in ("Fast Moving Consumer Goods", "FMCG", "Consumer Defensive"):
        fair_pe = 35.0
    elif sector in ("Energy", "Oil & Gas"):
        fair_pe = 12.0

    earnings_fair = round(eps * fair_pe, 2) if eps and eps > 0 else None

    anchors = [v for v in (dcf_per_share, earnings_fair, gnum) if v and v > 0]
    if not anchors:
        return {
            "symbol": sym,
            "currency": "INR",
            "current_price": price,
            "fair_value_low": None,
            "fair_value_mid": None,
            "fair_value_high": None,
            "margin_of_safety_pct": None,
            "verdict": "INSUFFICIENT_DATA",
            "method_notes": [
                "Run fundamentals ingest or refresh data for this NSE symbol.",
                "DCF needs positive FCF; earnings band needs positive EPS.",
            ],
            "dcf_per_share": dcf_per_share,
            "earnings_yield_fair_value": earnings_fair,
            "fair_pe_assumed": fair_pe,
            "graham_number": gnum,
        }

    mid = sum(anchors) / len(anchors)
    low = round(mid * 0.85, 2)
    high = round(mid * 1.15, 2)
    mos = None
    verdict = "FAIRLY_VALUED"
    if price and mid > 0:
        mos = round((1 - price / mid) * 100, 1)
        if price < low:
            verdict = "UNDERVALUED"
        elif price > high:
            verdict = "OVERVALUED"

    return {
        "symbol": sym,
        "currency": "INR",
        "current_price": price,
        "fair_value_low": low,
        "fair_value_mid": round(mid, 2),
        "fair_value_high": high,
        "margin_of_safety_pct": mos,
        "verdict": verdict,
        "dcf_per_share": dcf_per_share,
        "earnings_yield_fair_value": earnings_fair,
        "fair_pe_assumed": fair_pe,
        "graham_number": gnum,
        "graham_margin_of_safety_pct": margin_of_safety_pct(gnum, price),
        "method_notes": [
            "Band blends DCF, Graham number √(22.5×EPS×BVPS), and EPS × sector fair P/E (*Intelligent Investor*).",
            "Margin of safety: prefer price ≤ ⅔ intrinsic (Graham Ch 20).",
            "Verify against BSE/NSE annual reports.",
        ],
    }


def compute_quality_score(symbol: str) -> dict:
    """0–100 quality score for Indian equities."""
    sym = normalize_nse_symbol(symbol)
    fund = _load_fundamentals(sym)
    snap = _yf_snapshot(sym)
    ratios = fund.get("ratios_json") or {}

    roe = fund.get("roe") or snap.get("roe")
    if roe and abs(roe) < 2:
        roe = roe * 100 if roe else None

    debt_eq = fund.get("debt_equity") or snap.get("debt_equity")
    promoter = fund.get("promoter_pct")
    if promoter is None:
        insider = snap.get("held_percent_insiders")
        if insider is not None:
            promoter = round(insider * 100, 2)

    rev_g = snap.get("revenue_growth") or ratios.get("revenue_growth")
    earn_g = snap.get("earnings_growth")
    growth = earn_g if earn_g is not None else rev_g
    if growth is not None and abs(growth) < 2:
        growth = growth * 100

    roe_consistency = _roe_consistency_years(sym)

    components: list[dict] = []
    total_weight = 0
    score = 0.0

    def add(name: str, pts: float, weight: float, detail: str):
        nonlocal score, total_weight
        score += pts * weight
        total_weight += weight
        components.append({"factor": name, "score": round(pts, 1), "weight": weight, "detail": detail})

    if roe is not None:
        if roe >= 20:
            pts = 100
        elif roe >= 15:
            pts = 80
        elif roe >= 10:
            pts = 55
        else:
            pts = 30
        add("ROE (latest)", pts, 0.22, f"ROE {roe:.1f}% — key for Indian compounders")
    else:
        add("ROE (latest)", 50, 0.22, "ROE unavailable")

    if roe_consistency is not None:
        add("ROE consistency (5Y)", roe_consistency, 0.18, "Stability of returns on equity over ~5 years")
    else:
        add("ROE consistency (5Y)", 50, 0.18, "Insufficient history for 5Y ROE trend")

    if debt_eq is not None:
        if debt_eq <= 0.3:
            pts = 95
        elif debt_eq <= 0.8:
            pts = 75
        elif debt_eq <= 1.5:
            pts = 50
        else:
            pts = 25
        add("Debt / Equity", pts, 0.2, f"D/E {debt_eq:.2f} — leverage risk (India: watch pledging separately)")
    else:
        add("Debt / Equity", 50, 0.2, "D/E unavailable")

    if promoter is not None:
        if promoter >= 50:
            pts = 90
        elif promoter >= 35:
            pts = 70
        elif promoter >= 25:
            pts = 50
        else:
            pts = 35
        add("Promoter / insider holding", pts, 0.15, f"Holding ~{promoter:.1f}% (proxy if from yfinance insiders)")
    else:
        add("Promoter / insider holding", 50, 0.15, "Check BSE shareholding pattern — not in feed")

    if growth is not None:
        g = growth * 100 if abs(growth) < 2 else growth
        if g >= 15:
            pts = 90
        elif g >= 8:
            pts = 70
        elif g >= 0:
            pts = 50
        else:
            pts = 25
        add("Earnings / revenue growth", pts, 0.25, f"Growth proxy {g:.1f}% (yfinance; not always 5Y)")
    else:
        add("Earnings / revenue growth", 50, 0.25, "Growth metric unavailable")

    final = round(score / total_weight, 1) if total_weight else 50.0
    grade = "A" if final >= 75 else "B" if final >= 60 else "C" if final >= 45 else "D"

    return {
        "symbol": sym,
        "quality_score": final,
        "grade": grade,
        "components": components,
        "market": "India (NSE/BSE)",
    }


def _roe_consistency_years(symbol: str) -> Optional[float]:
    """Score 0–100 from ROE stability over available annual periods."""
    try:
        t = yf.Ticker(normalize_nse_symbol(symbol))
        fin = t.financials
        bal = t.balance_sheet
        if fin is None or bal is None or fin.empty or bal.empty:
            return None
        roes = []
        for col in list(fin.columns)[:5]:
            try:
                ni = fin.loc["Net Income", col] if "Net Income" in fin.index else None
                eq = bal.loc["Stockholders Equity", col] if "Stockholders Equity" in bal.index else None
                if ni is not None and eq is not None and float(eq) != 0:
                    roes.append(float(ni) / float(eq) * 100)
            except Exception:
                continue
        if len(roes) < 2:
            return None
        avg = sum(roes) / len(roes)
        var = sum((r - avg) ** 2 for r in roes) / len(roes)
        std = var ** 0.5
        if std < 3:
            return 95
        if std < 6:
            return 75
        if std < 10:
            return 55
        return 35
    except Exception:
        return None


def compare_to_benchmarks(symbol: str, fd_rate_pct: float = DEFAULT_FD_RATE_PCT) -> dict:
    """Stock vs Nifty 50 vs fixed deposit (India)."""
    sym = normalize_nse_symbol(symbol)
    stock_ret = _return_1y(sym)
    nifty_ret = _return_1y(NIFTY_50_SYMBOL)
    fd_ret = round(fd_rate_pct, 2)

    verdict = "NEUTRAL"
    notes = []
    if stock_ret is not None and nifty_ret is not None:
        if stock_ret > nifty_ret + 5:
            verdict = "OUTPERFORMING_NIFTY"
            notes.append(f"1Y return beat Nifty 50 by {stock_ret - nifty_ret:.1f} pp")
        elif stock_ret < nifty_ret - 5:
            verdict = "UNDERPERFORMING_NIFTY"
            notes.append(f"1Y return trailed Nifty 50 by {nifty_ret - stock_ret:.1f} pp")
        else:
            notes.append("Roughly in line with Nifty 50 over 1 year")

    if stock_ret is not None:
        if stock_ret < fd_ret:
            notes.append(
                f"1Y return ({stock_ret}%) below typical FD (~{fd_ret}%) — equity risk may not have paid off"
            )
        else:
            notes.append(
                f"1Y return ({stock_ret}%) above typical FD (~{fd_ret}%) — equity risk premium visible"
            )

    return {
        "symbol": sym,
        "period": "1Y",
        "currency": "INR",
        "stock_return_pct": stock_ret,
        "nifty_50_return_pct": nifty_ret,
        "fd_rate_pct": fd_ret,
        "verdict": verdict,
        "notes": notes,
        "disclaimer": "FD rate is indicative (user-configurable). Past returns ≠ future results.",
    }


def portfolio_insights(holdings: list[dict], net_worth_inr: Optional[float]) -> dict:
    """Sector concentration and position sizing for Indian portfolio."""
    if not holdings:
        return {"sectors": [], "warnings": [], "holdings_detail": []}

    total_value = sum(float(h.get("current_value") or 0) for h in holdings)
    sector_totals: dict[str, float] = {}
    details = []

    for h in holdings:
        sym = h.get("symbol", "")
        fund = _load_fundamentals(sym)
        snap = _yf_snapshot(sym)
        sector = (fund.get("ratios_json") or {}).get("sector") or snap.get("sector")
        sector = sector or NIFTY_SECTOR_MAP.get(base_ticker(sym), "Other")
        val = float(h.get("current_value") or 0)
        sector_totals[sector] = sector_totals.get(sector, 0) + val
        pct_port = round(val / total_value * 100, 1) if total_value else 0
        pct_nw = round(val / net_worth_inr * 100, 1) if net_worth_inr and net_worth_inr > 0 else None
        details.append({
            "symbol": sym,
            "sector": sector,
            "current_value": val,
            "pct_of_portfolio": pct_port,
            "pct_of_net_worth": pct_nw,
        })

    sectors = [
        {
            "sector": s,
            "value_inr": round(v, 2),
            "pct": round(v / total_value * 100, 1) if total_value else 0,
        }
        for s, v in sorted(sector_totals.items(), key=lambda x: -x[1])
    ]

    warnings = []
    for d in details:
        if d["pct_of_portfolio"] >= CONCENTRATION_STOCK_WARN_PCT:
            warnings.append(
                f"{d['symbol']}: {d['pct_of_portfolio']}% of portfolio — consider diversification (Buffett: avoid over-concentration unless high conviction)"
            )
        if d.get("pct_of_net_worth") and d["pct_of_net_worth"] >= 15:
            warnings.append(
                f"{d['symbol']}: {d['pct_of_net_worth']}% of net worth — ensure position size matches your conviction"
            )
    for s in sectors:
        if s["pct"] >= CONCENTRATION_SECTOR_WARN_PCT:
            warnings.append(
                f"{s['sector']} sector: {s['pct']}% of portfolio — thematic concentration risk"
            )

    return {
        "total_value_inr": round(total_value, 2),
        "net_worth_inr": net_worth_inr,
        "sectors": sectors,
        "holdings_detail": details,
        "warnings": warnings,
        "market": "India",
    }


def earnings_calendar_for_symbols(symbols: list[str], days_ahead: int = 90) -> list[dict]:
    """Upcoming earnings / events for watchlist (NSE symbols)."""
    events: list[dict] = []
    cutoff = date.today()
    end = cutoff + timedelta(days=days_ahead)

    for symbol in symbols:
        sym = normalize_nse_symbol(symbol)
        try:
            t = yf.Ticker(sym)
            # Earnings dates
            try:
                ed = t.get_earnings_dates(limit=8)
                if ed is not None and not ed.empty:
                    for idx in ed.index[:4]:
                        d = idx.date() if hasattr(idx, "date") else idx
                        if cutoff <= d <= end:
                            events.append({
                                "symbol": sym,
                                "event_type": "EARNINGS",
                                "event_date": str(d),
                                "title": f"Earnings — {base_ticker(sym)}",
                                "reminder": "Review annual report & concall on BSE/NSE after results",
                            })
            except Exception:
                pass
            # Calendar dict
            cal = getattr(t, "calendar", None)
            if cal is not None and isinstance(cal, dict):
                edate = cal.get("Earnings Date") or cal.get("Earnings Average")
                if edate is not None:
                    if hasattr(edate, "__iter__") and not isinstance(edate, str):
                        for item in list(edate)[:1]:
                            d = item.date() if hasattr(item, "date") else item
                            if hasattr(d, "year") and cutoff <= d <= end:
                                events.append({
                                    "symbol": sym,
                                    "event_type": "EARNINGS",
                                    "event_date": str(d),
                                    "title": f"Earnings date — {base_ticker(sym)}",
                                    "reminder": "Check BSE filings & management commentary",
                                })
        except Exception as e:
            logger.debug("Earnings calendar skip %s: %s", sym, e)

    # Annual report reminder (India: usually within 60 days of FY end — Mar for most)
    fy_end = date(date.today().year, 3, 31)
    if fy_end < cutoff:
        fy_end = date(date.today().year + 1, 3, 31)
    ar_deadline = fy_end + timedelta(days=60)
    if cutoff <= ar_deadline <= end:
        for symbol in symbols:
            sym = normalize_nse_symbol(symbol)
            events.append({
                "symbol": sym,
                "event_type": "ANNUAL_REPORT",
                "event_date": str(ar_deadline),
                "title": f"FY annual report season — {base_ticker(sym)}",
                "reminder": "Download AR from BSE India / company investor relations",
            })

    events.sort(key=lambda x: x["event_date"])
    return events
