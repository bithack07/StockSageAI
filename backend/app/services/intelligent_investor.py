"""
Benjamin Graham — *The Intelligent Investor* (1949, rev. 1973).

Warren Buffett describes this as the best book on investing. Formulas here power
StockSage fundamental, technical (Mr. Market), and ML overlays.

References (chapter themes):
  Ch 3–4  — Defensive vs enterprising investor
  Ch 7–8  — Mr. Market, margin of safety
  Ch 11–14 — Security analysis for lay investors (P/E, P/B, growth, quality)
  Ch 20   — “Century of evidence” checklist
"""
from __future__ import annotations

import logging
import math
from typing import Any, Optional

import yfinance as yf

from app.services.india_market import normalize_nse_symbol
from app.services.value_investing import _load_fundamentals, _safe_float, _yf_snapshot

logger = logging.getLogger(__name__)

# ── Graham constants (defensive investor, Ch 14) ─────────────────────────────
MAX_PE_DEFENSIVE = 15.0
MAX_PB_DEFENSIVE = 1.5
PE_PB_PRODUCT_MAX = 22.5  # P/E × P/B must not exceed (Graham combined test)
GRAHAM_NUMBER_FACTOR = 22.5  # √(22.5 × EPS × BVPS) — max defensive buy price
MIN_CURRENT_RATIO = 2.0
MIN_EPS_GROWTH_10Y_PCT = 33.0  # ~3% CAGR over 10 years
MARGIN_OF_SAFETY_BUY_PCT = 33.0  # prefer price ≤ 2/3 of intrinsic (Ch 20)
MR_MARKET_RSI_GREED = 70.0
MR_MARKET_RSI_FEAR = 30.0


def graham_number(eps: Optional[float], book_value_per_share: Optional[float]) -> Optional[float]:
    """Graham number = √(22.5 × EPS × BVPS). Upper bound for defensive investor price."""
    if not eps or not book_value_per_share or eps <= 0 or book_value_per_share <= 0:
        return None
    return round(math.sqrt(GRAHAM_NUMBER_FACTOR * eps * book_value_per_share), 2)


def margin_of_safety_pct(intrinsic: Optional[float], price: Optional[float]) -> Optional[float]:
    """(Intrinsic − Price) / Intrinsic × 100. Positive = discount (Ch 20)."""
    if not intrinsic or not price or intrinsic <= 0:
        return None
    return round((1 - price / intrinsic) * 100, 1)


def ncav_per_share(
    current_assets: Optional[float],
    total_liabilities: Optional[float],
    shares_outstanding: Optional[float],
) -> Optional[float]:
    """Net current asset value per share (net-net style, Ch 15 enterprising)."""
    if None in (current_assets, total_liabilities, shares_outstanding) or shares_outstanding <= 0:
        return None
    return round((current_assets - total_liabilities) / shares_outstanding, 2)


def pe_times_pb(pe: Optional[float], pb: Optional[float]) -> Optional[float]:
    if pe is None or pb is None or pe <= 0 or pb <= 0:
        return None
    return round(pe * pb, 2)


def _balance_sheet_fields(symbol: str) -> dict[str, Optional[float]]:
    """Latest quarterly balance sheet from yfinance."""
    out: dict[str, Optional[float]] = {
        "current_assets": None,
        "current_liabilities": None,
        "total_liabilities": None,
        "total_debt": None,
        "stockholders_equity": None,
    }
    try:
        bs = yf.Ticker(normalize_nse_symbol(symbol)).quarterly_balance_sheet
        if bs is None or bs.empty:
            return out
        col = bs.columns[0]
        idx = bs.index

        def _row(name: str) -> Optional[float]:
            if name in idx:
                return _safe_float(bs.loc[name, col])
            return None

        out["current_assets"] = _row("Current Assets")
        out["current_liabilities"] = _row("Current Liabilities")
        out["total_liabilities"] = _row("Total Liab")
        out["total_debt"] = _row("Total Debt")
        out["stockholders_equity"] = _row("Stockholders Equity") or _row("Common Stock Equity")
    except Exception as exc:
        logger.debug("balance sheet fetch failed for %s: %s", symbol, exc)
    return out


def _defensive_criteria(data: dict) -> list[dict[str, Any]]:
    """Graham defensive checklist (Ch 14) — each item pass/fail/unknown."""
    pe = data.get("pe_ratio")
    pb = data.get("pb_ratio")
    cr = data.get("current_ratio")
    debt = data.get("total_debt")
    nca = data.get("net_current_assets")
    eg = data.get("earnings_growth_pct")
    pe_pb = data.get("pe_times_pb")
    price = data.get("price")
    gnum = data.get("graham_number")
    mos = data.get("margin_of_safety_pct")

    checks = [
        {
            "id": "pe_max_15",
            "label": f"P/E ≤ {MAX_PE_DEFENSIVE:.0f} (defensive)",
            "passed": pe is not None and 0 < pe <= MAX_PE_DEFENSIVE,
            "value": pe,
        },
        {
            "id": "pb_max_1_5",
            "label": f"P/B ≤ {MAX_PB_DEFENSIVE} (defensive)",
            "passed": pb is not None and 0 < pb <= MAX_PB_DEFENSIVE,
            "value": pb,
        },
        {
            "id": "pe_pb_max_22_5",
            "label": f"P/E × P/B ≤ {PE_PB_PRODUCT_MAX} (Graham combined)",
            "passed": pe_pb is not None and pe_pb <= PE_PB_PRODUCT_MAX,
            "value": pe_pb,
        },
        {
            "id": "current_ratio_2",
            "label": f"Current ratio ≥ {MIN_CURRENT_RATIO}",
            "passed": cr is not None and cr >= MIN_CURRENT_RATIO,
            "value": cr,
        },
        {
            "id": "debt_below_nca",
            "label": "Long-term debt < net current assets",
            "passed": (
                debt is not None and nca is not None and debt < nca
            ) if debt is not None and nca is not None else None,
            "value": {"debt": debt, "net_current_assets": nca},
        },
        {
            "id": "eps_growth_10y",
            "label": f"Earnings growth ≥ {MIN_EPS_GROWTH_10Y_PCT:.0f}% (proxy)",
            "passed": eg is not None and eg >= MIN_EPS_GROWTH_10Y_PCT,
            "value": eg,
        },
        {
            "id": "margin_of_safety",
            "label": f"Margin of safety ≥ {MARGIN_OF_SAFETY_BUY_PCT:.0f}% vs Graham #",
            "passed": mos is not None and mos >= MARGIN_OF_SAFETY_BUY_PCT,
            "value": mos,
        },
        {
            "id": "price_below_graham",
            "label": "Price ≤ Graham number",
            "passed": (
                price is not None and gnum is not None and price <= gnum
            ) if price and gnum else None,
            "value": {"price": price, "graham_number": gnum},
        },
    ]
    for c in checks:
        if c["passed"] is None:
            c["status"] = "unknown"
        else:
            c["status"] = "pass" if c["passed"] else "fail"
    return checks


def compute_graham_analysis(symbol: str) -> dict[str, Any]:
    """
    Full Graham framework for one symbol.
    Used by fundamental agent, technical (Mr. Market), and ML overlay.
    """
    sym = normalize_nse_symbol(symbol)
    fund = _load_fundamentals(sym)
    snap = _yf_snapshot(sym)
    ratios = fund.get("ratios_json") or {}
    bs = _balance_sheet_fields(sym)

    price = snap.get("price")
    eps = snap.get("eps") or ratios.get("eps")
    bvps = snap.get("book_value")
    shares = snap.get("shares_outstanding")
    pe = fund.get("pe_ratio") or snap.get("pe_ratio")
    pb = fund.get("pb_ratio") or snap.get("pb_ratio")

    if pe and pe > 200:
        pe = pe / 100 if pe > 10 else pe
    if pb and pb > 20:
        pb = pb / 100 if pb > 5 else pb

    current_ratio = None
    if bs["current_assets"] and bs["current_liabilities"] and bs["current_liabilities"] > 0:
        current_ratio = round(bs["current_assets"] / bs["current_liabilities"], 2)

    net_current_assets = None
    if bs["current_assets"] is not None and bs["total_liabilities"] is not None:
        net_current_assets = bs["current_assets"] - bs["total_liabilities"]

    gnum = graham_number(eps, bvps)
    ncav = ncav_per_share(bs["current_assets"], bs["total_liabilities"], shares)
    pe_pb = pe_times_pb(pe, pb)

    intrinsic = gnum
    if ncav and ncav > 0:
        intrinsic = min(filter(None, [gnum, ncav]), default=gnum)

    mos = margin_of_safety_pct(intrinsic, price)

    eg = snap.get("earnings_growth")
    if eg is not None and abs(eg) < 2:
        eg_pct = round(eg * 100, 1)
    elif eg is not None:
        eg_pct = round(eg, 1)
    else:
        eg_pct = None

    data = {
        "symbol": sym,
        "price": price,
        "pe_ratio": pe,
        "pb_ratio": pb,
        "eps": eps,
        "book_value_per_share": bvps,
        "current_ratio": current_ratio,
        "total_debt": bs["total_debt"],
        "net_current_assets": net_current_assets,
        "earnings_growth_pct": eg_pct,
        "pe_times_pb": pe_pb,
        "graham_number": gnum,
        "ncav_per_share": ncav,
        "margin_of_safety_pct": mos,
    }

    checks = _defensive_criteria(data)
    known = [c for c in checks if c["status"] != "unknown"]
    passed = sum(1 for c in known if c["status"] == "pass")
    graham_score = round(100 * passed / len(known), 1) if known else None

    verdict = graham_fundamental_verdict(price, gnum, mos, pe, pb, pe_pb, graham_score)

    return {
        **data,
        "defensive_criteria": checks,
        "defensive_pass_count": passed,
        "defensive_total_known": len(known),
        "graham_score": graham_score,
        "valuation_verdict": verdict,
        "framework": "The Intelligent Investor (Graham)",
        "formulas": {
            "graham_number": "√(22.5 × EPS × BVPS)",
            "pe_pb_test": "P/E × P/B ≤ 22.5",
            "margin_of_safety": "(Intrinsic − Price) / Intrinsic",
            "ncav_per_share": "(Current Assets − Total Liabilities) / Shares",
        },
    }


def graham_fundamental_verdict(
    price: Optional[float],
    gnum: Optional[float],
    mos: Optional[float],
    pe: Optional[float],
    pb: Optional[float],
    pe_pb: Optional[float],
    graham_score: Optional[float],
) -> str:
    """Map Graham metrics to UNDERVALUED / FAIRLY_VALUED / OVERVALUED."""
    if price and gnum:
        if price <= gnum * (1 - MARGIN_OF_SAFETY_BUY_PCT / 100):
            return "UNDERVALUED"
        if price > gnum * 1.15:
            return "OVERVALUED"

    if mos is not None:
        if mos >= MARGIN_OF_SAFETY_BUY_PCT:
            return "UNDERVALUED"
        if mos < -15:
            return "OVERVALUED"

    if pe_pb is not None:
        if pe_pb <= PE_PB_PRODUCT_MAX * 0.85:
            pass  # cheap on combined test
        elif pe_pb > PE_PB_PRODUCT_MAX * 1.25:
            return "OVERVALUED"

    if pe is not None and pe > MAX_PE_DEFENSIVE * 1.2:
        return "OVERVALUED"
    if pb is not None and pb > MAX_PB_DEFENSIVE * 1.2:
        return "OVERVALUED"

    if graham_score is not None:
        if graham_score >= 70:
            return "UNDERVALUED"
        if graham_score <= 35:
            return "OVERVALUED"

    return "FAIRLY_VALUED"


def graham_mr_market_technical(
    symbol: str,
    *,
    rsi: Optional[float] = None,
    price: Optional[float] = None,
    ema200: Optional[float] = None,
) -> dict[str, Any]:
    """
    Ch 8 — Mr. Market: treat price quotes as offers, not facts.
    Maps RSI + price vs Graham # + 200-day EMA into technical-style signal.
    """
    graham = compute_graham_analysis(symbol)
    price = price or graham.get("price")
    gnum = graham.get("graham_number")
    mos = graham.get("margin_of_safety_pct")

    mood = "NEUTRAL"
    if rsi is not None:
        if rsi >= MR_MARKET_RSI_GREED:
            mood = "EUPHORIC"
        elif rsi <= MR_MARKET_RSI_FEAR:
            mood = "FEARFUL"

    # Distance from Graham intrinsic (Mr. Market offering)
    offer_vs_value = None
    if price and gnum and gnum > 0:
        offer_vs_value = round((price / gnum - 1) * 100, 1)

    signal = "NEUTRAL"
    trend = "SIDEWAYS"

    if offer_vs_value is not None:
        if offer_vs_value <= -MARGIN_OF_SAFETY_BUY_PCT:
            signal = "STRONG_BUY"
            trend = "UPTREND"
        elif offer_vs_value <= -10:
            signal = "BUY"
        elif offer_vs_value >= 25:
            signal = "STRONG_SELL"
            trend = "DOWNTREND"
        elif offer_vs_value >= 10:
            signal = "SELL"

    if rsi is not None:
        if mood == "EUPHORIC" and signal in ("BUY", "STRONG_BUY"):
            signal = "NEUTRAL"
        elif mood == "FEARFUL" and signal in ("SELL", "STRONG_SELL") and (mos or 0) > 0:
            signal = "BUY"

    if ema200 and price:
        if price > ema200 * 1.02:
            trend = "UPTREND" if trend == "SIDEWAYS" else trend
        elif price < ema200 * 0.98:
            trend = "DOWNTREND" if trend == "SIDEWAYS" else trend

    return {
        "framework": "Mr. Market (Graham Ch 8)",
        "mr_market_mood": mood,
        "offer_vs_graham_number_pct": offer_vs_value,
        "margin_of_safety_pct": mos,
        "graham_number": gnum,
        "signal": signal,
        "trend": trend,
        "momentum": mood,
        "rsi_used": rsi,
        "source": "intelligent_investor",
    }


def graham_ml_features(symbol: str) -> dict[str, float]:
    """
    Normalised features for ML (training + inference).
    Names match ml_training/train_all.py GRAHAM_FEATURES.
    """
    g = compute_graham_analysis(symbol)
    score = (g.get("graham_score") or 50) / 100.0
    mos = g.get("margin_of_safety_pct")
    mos_norm = max(-1.0, min(1.0, (mos or 0) / 50.0))
    pe_pb = g.get("pe_times_pb")
    pe_pb_norm = min(2.0, (pe_pb or PE_PB_PRODUCT_MAX) / PE_PB_PRODUCT_MAX)
    price = g.get("price")
    gnum = g.get("graham_number")
    price_vs_g = 1.0
    if price and gnum and gnum > 0:
        price_vs_g = min(2.0, max(0.0, price / gnum))

    return {
        "graham_score_norm": round(score, 4),
        "graham_mos_norm": round(mos_norm, 4),
        "graham_pe_pb_norm": round(pe_pb_norm, 4),
        "graham_price_ratio": round(price_vs_g, 4),
    }


def graham_direction_prior(symbol: str) -> dict[str, Any]:
    """
    7-day direction prior from Graham rules (used to blend with XGBoost/LSTM).
    """
    g = compute_graham_analysis(symbol)
    tech = graham_mr_market_technical(symbol)
    verdict = g.get("valuation_verdict", "FAIRLY_VALUED")
    sig = tech.get("signal", "NEUTRAL")

    bull = 0.33
    bear = 0.33
    if verdict == "UNDERVALUED":
        bull += 0.25
        bear -= 0.1
    elif verdict == "OVERVALUED":
        bear += 0.25
        bull -= 0.1

    if sig in ("STRONG_BUY", "BUY"):
        bull += 0.15
    elif sig in ("STRONG_SELL", "SELL"):
        bear += 0.15

    mos = g.get("margin_of_safety_pct") or 0
    bull += min(0.15, mos / 200)
    bear += min(0.15, max(0, -mos) / 200)

    total = bull + bear + 0.34
    return {
        "bullish_prob": round(bull / total, 3),
        "bearish_prob": round(bear / total, 3),
        "neutral_prob": round(0.34 / total, 3),
        "graham_verdict": verdict,
        "mr_market_signal": sig,
        "source": "intelligent_investor_prior",
    }


# Feature names appended when retraining XGBoost (see ml_training/train_all.py)
GRAHAM_ML_FEATURE_NAMES = [
    "graham_score_norm",
    "graham_mos_norm",
    "graham_pe_pb_norm",
    "graham_price_ratio",
]
