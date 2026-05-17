"""
Fundamental analysis playbook — golden rules from classic investing texts.

Sources encoded here (see Stock_Analysis_Complete_Note.md.pdf):
  Graham — margin of safety, defensive criteria (*Intelligent Investor*)
  Lynch — PEG, stock categories (*One Up on Wall Street*)
  Greenblatt — earnings yield + return on capital (*Little Book That Beats the Market*)
  Dorsey — economic moat durability (*Little Book That Builds Wealth*)
  Marks — second-level thinking (quality at a price)
  Damodaran — DCF / reverse-DCF implied growth sanity check
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from app.services.india_market import normalize_nse_symbol
from app.services.intelligent_investor import compute_graham_analysis
from app.services.value_investing import (
    _load_fundamentals,
    _yf_snapshot,
    compute_intrinsic_value_band,
    compute_quality_score,
)

logger = logging.getLogger(__name__)

# Lynch PEG bands
PEG_UNDERVALUED = 1.0
PEG_FAIR_HIGH = 1.5
PEG_EXPENSIVE = 2.0

# FA scoring framework (max 50) — invest with conviction above this
FA_HIGH_CONVICTION_MIN = 35

# Component weights (sum = 1.0)
_FA_WEIGHTS = {
    "business_clarity": 0.10,
    "moat_durability": 0.20,
    "earnings_quality": 0.15,
    "balance_sheet": 0.10,
    "cash_flow": 0.10,
    "management": 0.15,
    "valuation": 0.15,
    "industry_tailwind": 0.05,
}

# Sector → Lynch category hint + moat prior (India-focused examples from playbook)
_SECTOR_MOAT_HINT: dict[str, dict[str, str]] = {
    "Financial Services": {"moat": "switching_costs", "lynch_hint": "stalwart"},
    "Banks": {"moat": "intangible_assets", "lynch_hint": "stalwart"},
    "Information Technology": {"moat": "switching_costs", "lynch_hint": "fast_grower"},
    "Fast Moving Consumer Goods": {"moat": "intangible_assets", "lynch_hint": "stalwart"},
    "Consumer Defensive": {"moat": "intangible_assets", "lynch_hint": "stalwart"},
    "Utilities": {"moat": "efficient_scale", "lynch_hint": "slow_grower"},
    "Energy": {"moat": "cost_advantage", "lynch_hint": "cyclical"},
    "Industrials": {"moat": "cost_advantage", "lynch_hint": "cyclical"},
    "Airlines": {"moat": "none", "lynch_hint": "cyclical"},
}

_INDUSTRY_TAILWIND_SCORE: dict[str, int] = {
    "Information Technology": 4,
    "Financial Services": 4,
    "Healthcare": 4,
    "Industrials": 3,
    "Fast Moving Consumer Goods": 3,
    "Consumer Defensive": 3,
    "Utilities": 2,
    "Energy": 2,
    "Real Estate": 2,
}


def lynch_peg(pe: Optional[float], eps_growth_pct: Optional[float]) -> dict[str, Any]:
    """Peter Lynch PEG = P/E ÷ EPS growth (%)."""
    if pe is None or eps_growth_pct is None or eps_growth_pct <= 0 or pe <= 0:
        return {
            "peg_ratio": None,
            "verdict": "UNKNOWN",
            "note": "Need positive P/E and EPS growth for PEG (Lynch).",
        }
    peg = round(pe / eps_growth_pct, 2)
    if peg < PEG_UNDERVALUED:
        verdict = "UNDERVALUED_GROWTH"
    elif peg <= PEG_FAIR_HIGH:
        verdict = "FAIRLY_VALUED"
    elif peg <= PEG_EXPENSIVE:
        verdict = "STRETCHED"
    else:
        verdict = "EXPENSIVE"
    return {
        "peg_ratio": peg,
        "verdict": verdict,
        "pe_ratio": pe,
        "eps_growth_pct": eps_growth_pct,
        "framework": "Peter Lynch — PEG",
    }


def lynch_stock_category(
    *,
    revenue_growth_pct: Optional[float],
    pe: Optional[float],
    sector: Optional[str],
) -> dict[str, Any]:
    """Heuristic Lynch six categories from growth + sector."""
    hint = (sector and _SECTOR_MOAT_HINT.get(sector, {}).get("lynch_hint")) or None
    rg = revenue_growth_pct
    if rg is not None and abs(rg) < 2:
        rg = rg * 100

    category = hint or "stalwart"
    if rg is not None:
        if rg >= 20:
            category = "fast_grower"
        elif rg >= 12:
            category = category if category != "slow_grower" else "stalwart"
        elif rg < 5:
            category = "slow_grower" if pe and pe < 15 else "cyclical"

    notes = {
        "slow_grower": "Large mature — buy only if very cheap (Lynch).",
        "stalwart": "10–12% growers — sell when P/E stretches.",
        "fast_grower": "20%+ — highest research burden; verify PEG.",
        "cyclical": "Timing the cycle matters; avoid peak earnings.",
        "turnaround": "Needs catalyst — not auto-detected; verify manually.",
        "asset_play": "Hidden assets — verify from AR notes.",
    }
    return {
        "category": category,
        "framework": "Peter Lynch — stock categories",
        "guidance": notes.get(category, ""),
    }


def greenblatt_magic_formula(
    *,
    roce: Optional[float],
    roe: Optional[float],
    pe: Optional[float],
    earnings_yield: Optional[float] = None,
) -> dict[str, Any]:
    """
    Greenblatt: rank by return on capital (quality) and earnings yield (price).
    We emit component scores 1–5 when data exists (full universe rank needs screener).
    """
    roc = roce
    if roc is None and roe is not None:
        roc = roe * 100 if abs(roe) < 2 else roe

    ey = earnings_yield
    if ey is None and pe and pe > 0:
        ey = round(100 / pe, 2)

    roc_score = None
    if roc is not None:
        if roc >= 25:
            roc_score = 5
        elif roc >= 18:
            roc_score = 4
        elif roc >= 12:
            roc_score = 3
        elif roc >= 8:
            roc_score = 2
        else:
            roc_score = 1

    ey_score = None
    if ey is not None:
        if ey >= 12:
            ey_score = 5
        elif ey >= 8:
            ey_score = 4
        elif ey >= 5:
            ey_score = 3
        elif ey >= 3:
            ey_score = 2
        else:
            ey_score = 1

    combined = None
    if roc_score is not None and ey_score is not None:
        combined = roc_score + ey_score  # max 10

    verdict = "NEUTRAL"
    if combined is not None:
        if combined >= 8:
            verdict = "ATTRACTIVE"
        elif combined <= 4:
            verdict = "WEAK"

    return {
        "return_on_capital_pct": roc,
        "earnings_yield_pct": ey,
        "quality_score_1_5": roc_score,
        "price_score_1_5": ey_score,
        "combined_score": combined,
        "verdict": verdict,
        "framework": "Joel Greenblatt — Magic Formula (ROC + earnings yield)",
    }


def dorsey_moat_assessment(
    *,
    sector: Optional[str],
    gross_margin: Optional[float],
    roe: Optional[float],
    debt_equity: Optional[float],
) -> dict[str, Any]:
    """Moat durability proxy from margins, ROE, sector (Dorsey five sources)."""
    hint = _SECTOR_MOAT_HINT.get(sector or "", {})
    primary_source = hint.get("moat", "unknown")

    score = 3
    reasons: list[str] = []

    if roe is not None:
        r = roe * 100 if abs(roe) < 2 else roe
        if r >= 18:
            score += 1
            reasons.append(f"ROE {r:.1f}% supports pricing power")
        elif r < 10:
            score -= 1
            reasons.append(f"ROE {r:.1f}% — weak vs 15% target")

    if gross_margin is not None:
        gm = gross_margin * 100 if abs(gross_margin) < 1 else gross_margin
        if gm >= 40:
            score += 1
            reasons.append("High gross margin — moat strengthening signal")
        elif gm < 20:
            score -= 1
            reasons.append("Low gross margin — competitive pressure risk")

    if debt_equity is not None and debt_equity > 1.5:
        score -= 1
        reasons.append("High leverage weakens moat durability")

    score = max(1, min(5, score))
    if score >= 4:
        width = "wide"
    elif score >= 3:
        width = "narrow"
    else:
        width = "none"

    return {
        "primary_moat_source": primary_source,
        "moat_width": width,
        "durability_score_1_5": score,
        "reasons": reasons,
        "five_sources": [
            "network_effects",
            "switching_costs",
            "cost_advantage",
            "intangible_assets",
            "efficient_scale",
        ],
        "framework": "Pat Dorsey — economic moat",
    }


def _score_component(value: Optional[float], bands: list[tuple[float, int]]) -> int:
    """Map numeric metric to 1–5 using ascending bands."""
    if value is None:
        return 3
    for threshold, score in bands:
        if value >= threshold:
            return score
    return 1


def compute_fundamental_playbook(symbol: str) -> dict[str, Any]:
    """Full fundamental playbook output for agents and API."""
    sym = normalize_nse_symbol(symbol)
    fund = _load_fundamentals(sym)
    snap = _yf_snapshot(sym)
    ratios = fund.get("ratios_json") or {}

    pe = fund.get("pe_ratio") or snap.get("pe_ratio")
    pb = fund.get("pb_ratio") or snap.get("pb_ratio")
    roe = fund.get("roe") or snap.get("roe")
    roce = fund.get("roce")
    debt = fund.get("debt_equity") or snap.get("debt_equity")
    sector = ratios.get("sector") or snap.get("sector")
    rev_g = snap.get("revenue_growth") or ratios.get("revenue_growth")
    earn_g = snap.get("earnings_growth")
    gross = ratios.get("gross_margins")
    fcf = fund.get("fcf")
    promoter = fund.get("promoter_pct")
    pledge = fund.get("pledge_pct")

    if rev_g is not None and abs(rev_g) < 2:
        rev_g_pct = rev_g * 100
    elif rev_g is not None:
        rev_g_pct = rev_g
    else:
        rev_g_pct = None

    eg = earn_g
    if eg is not None and abs(eg) < 2:
        eg_pct = eg * 100
    elif eg is not None:
        eg_pct = eg
    else:
        eg_pct = rev_g_pct

    try:
        graham = compute_graham_analysis(sym)
    except Exception as exc:
        logger.warning("Graham analysis failed for %s: %s", sym, exc)
        graham = {}

    try:
        owner_band = compute_intrinsic_value_band(sym)
    except Exception:
        owner_band = {}

    try:
        quality = compute_quality_score(sym)
    except Exception:
        quality = {}

    peg = lynch_peg(pe, eg_pct)
    lynch_cat = lynch_stock_category(revenue_growth_pct=rev_g_pct, pe=pe, sector=sector)
    greenblatt = greenblatt_magic_formula(roce=roce, roe=roe, pe=pe)
    moat = dorsey_moat_assessment(
        sector=sector,
        gross_margin=gross,
        roe=roe,
        debt_equity=debt,
    )

    # ── FA score components (1–5 each) ─────────────────────────────────────
    business = 3
    if sector and snap.get("industry"):
        business = 4
    if sector in ("Information Technology", "Financial Services", "Fast Moving Consumer Goods"):
        business = 5

    moat_s = moat["durability_score_1_5"]
    q_score = quality.get("quality_score") or 50
    earnings_s = _score_component(q_score, [(75, 5), (60, 4), (45, 3), (30, 2)])
    if rev_g_pct is not None and rev_g_pct < 0:
        earnings_s = max(1, earnings_s - 1)

    bs_s = 3
    cr = graham.get("current_ratio")
    if cr is not None:
        bs_s = _score_component(cr, [(2.5, 5), (2.0, 4), (1.5, 3), (1.0, 2)])
    if debt is not None:
        if debt <= 0.5:
            bs_s = min(5, bs_s + 1)
        elif debt > 1.5:
            bs_s = max(1, bs_s - 1)

    cf_s = 3
    if fcf is not None and fcf > 0:
        cf_s = 4
    elif fcf is not None and fcf < 0:
        cf_s = 2

    mgmt_s = 3
    if promoter is not None:
        mgmt_s = _score_component(promoter, [(50, 5), (40, 4), (30, 3), (20, 2)])
    if pledge is not None and pledge > 25:
        mgmt_s = 1
    elif pledge is not None and pledge > 10:
        mgmt_s = max(1, mgmt_s - 1)

    val_s = 3
    mos = graham.get("margin_of_safety_pct") or owner_band.get("margin_of_safety_pct")
    if mos is not None:
        val_s = _score_component(mos, [(33, 5), (20, 4), (10, 3), (0, 2)])
    if peg.get("verdict") == "UNDERVALUED_GROWTH":
        val_s = min(5, val_s + 1)
    elif peg.get("verdict") == "EXPENSIVE":
        val_s = max(1, val_s - 1)

    industry_s = _INDUSTRY_TAILWIND_SCORE.get(sector or "", 3)

    weighted = (
        business * _FA_WEIGHTS["business_clarity"]
        + moat_s * _FA_WEIGHTS["moat_durability"]
        + earnings_s * _FA_WEIGHTS["earnings_quality"]
        + bs_s * _FA_WEIGHTS["balance_sheet"]
        + cf_s * _FA_WEIGHTS["cash_flow"]
        + mgmt_s * _FA_WEIGHTS["management"]
        + val_s * _FA_WEIGHTS["valuation"]
        + industry_s * _FA_WEIGHTS["industry_tailwind"]
    )
    fa_total = round(weighted * 10, 1)  # scale 1–5 components → ~10–50

    red_flags: list[str] = []
    if debt is not None and debt > 1.5:
        red_flags.append("Debt/equity above 1.5 — balance sheet stress (Graham)")
    if fcf is not None and fcf < 0:
        red_flags.append("Negative FCF — cash flow litmus fail (Bakshi)")
    if pledge is not None and pledge > 50:
        red_flags.append("Promoter pledging >50% — forced selling risk (India)")
    if peg.get("verdict") == "EXPENSIVE":
        red_flags.append(f"PEG {peg.get('peg_ratio')} — paying premium for growth (Lynch)")
    for c in graham.get("defensive_criteria") or []:
        if c.get("status") == "fail" and c.get("id") in ("pe_max_15", "margin_of_safety"):
            red_flags.append(c.get("label", c.get("id")))

    marks_note = (
        "Second-level: "
        + ("quality at an attractive price" if fa_total >= FA_HIGH_CONVICTION_MIN and val_s >= 4 else
           "good company but price may not compensate" if moat_s >= 4 and val_s < 3 else
           "revisit quality vs price trade-off")
    )

    return {
        "symbol": sym,
        "framework_sources": [
            "Graham", "Lynch", "Greenblatt", "Dorsey", "Marks", "Damodaran", "Buffett",
        ],
        "lynch": {"peg": peg, "category": lynch_cat},
        "greenblatt": greenblatt,
        "moat": moat,
        "graham_analysis": {
            "graham_score": graham.get("graham_score"),
            "valuation_verdict": graham.get("valuation_verdict"),
            "margin_of_safety_pct": graham.get("margin_of_safety_pct"),
            "graham_number": graham.get("graham_number"),
        },
        "owner_fair_value": {
            "verdict": owner_band.get("verdict"),
            "margin_of_safety_pct": owner_band.get("margin_of_safety_pct"),
            "fair_value_mid": owner_band.get("fair_value_mid"),
        },
        "quality_score": quality.get("quality_score"),
        "fa_score": {
            "total": fa_total,
            "max": 50,
            "high_conviction": fa_total >= FA_HIGH_CONVICTION_MIN,
            "components": {
                "business_clarity": business,
                "moat_durability": moat_s,
                "earnings_quality": earnings_s,
                "balance_sheet": bs_s,
                "cash_flow": cf_s,
                "management": mgmt_s,
                "valuation": val_s,
                "industry_tailwind": industry_s,
            },
        },
        "marks_second_level": marks_note,
        "red_flags": red_flags,
        "playbook_verdict": _playbook_fundamental_verdict(fa_total, graham, peg, owner_band),
    }


def _playbook_fundamental_verdict(
    fa_total: float,
    graham: dict,
    peg: dict,
    owner_band: dict,
) -> str:
    votes = []
    if graham.get("valuation_verdict"):
        votes.append(graham["valuation_verdict"])
    if owner_band.get("verdict"):
        votes.append(owner_band["verdict"])
    if peg.get("verdict") == "UNDERVALUED_GROWTH":
        votes.append("UNDERVALUED")
    elif peg.get("verdict") == "EXPENSIVE":
        votes.append("OVERVALUED")

    if votes.count("UNDERVALUED") >= 2 or (fa_total >= FA_HIGH_CONVICTION_MIN and "UNDERVALUED" in votes):
        return "UNDERVALUED"
    if votes.count("OVERVALUED") >= 2:
        return "OVERVALUED"
    if fa_total >= FA_HIGH_CONVICTION_MIN:
        return "FAIRLY_VALUED"
    return "FAIRLY_VALUED"
