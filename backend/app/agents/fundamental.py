"""Fundamental Analyst Agent — Groq/Llama 4."""
import json
import logging

from groq import Groq

from app.agents.local_heuristics import fundamental_from_data
from app.config import settings
from app.db import get_db
from app.utils.json_helpers import parse_db_json, parse_llm_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a CFA-level fundamental analyst specialising in Indian equities,
grounded in the Stock Analysis Playbook (Graham, Lynch, Greenblatt, Dorsey, Marks, Damodaran).
You receive structured JSON: ratios, DCF, peers, owner_fair_value_band, graham_analysis, and fundamental_playbook.
Use fundamental_playbook when present:
- fa_score (max 50): invest with conviction only if ≥35
- lynch.peg: PEG <1 undervalued growth; >2 expensive
- greenblatt: high ROC + high earnings yield = attractive
- moat.moat_width: wide/narrow/none (Dorsey)
Use Graham formulas when present:
- Graham number = √(22.5 × EPS × BVPS) — max defensive price
- P/E × P/B ≤ 22.5 (combined test)
- Margin of safety = (intrinsic − price) / intrinsic; prefer ≥ 33% discount
- Defensive criteria: P/E≤15, P/B≤1.5, current ratio≥2, debt < net current assets
Your job:
1. Assess UNDERVALUED / FAIRLY_VALUED / OVERVALUED using Graham + peers (explain if graham_analysis disagrees with raw P/E).
2. Flag any red flags: rising debt, falling promoter holding, negative FCF, margin compression.
3. Compare against sector peers. Is this stock best-in-class, average, or lagging?
4. Return ONLY a valid JSON object with keys:
   valuation_verdict, dcf_margin_of_safety_pct, red_flags (list), peer_rank (1=best),
   key_ratios_summary, overall_score (0-10).
No markdown. No preamble."""


def _get_fundamentals(symbol: str) -> dict:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT pe_ratio, pb_ratio, ev_ebitda, roe, roce, debt_equity, fcf, dcf_intrinsic, market_cap, ratios_json FROM fundamentals WHERE symbol=%s",
            (symbol,),
        )
        row = cur.fetchone()
    if not row:
        return {}
    cols = ["pe_ratio", "pb_ratio", "ev_ebitda", "roe", "roce", "debt_equity", "fcf", "dcf_intrinsic", "market_cap", "ratios_json"]
    data = dict(zip(cols, row))
    ratios_json = data.pop("ratios_json", None)
    if ratios_json:
        extra = parse_db_json(ratios_json, default={})
        if isinstance(extra, dict):
            data.update(extra)
    return data


def _get_peers(symbol: str, n: int = 3) -> list:
    """Return top N peers from same sector (approximated from tracked tickers)."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT symbol, pe_ratio, roe, roce, ratios_json FROM fundamentals WHERE symbol != %s ORDER BY market_cap DESC NULLS LAST LIMIT %s",
            (symbol, n),
        )
        rows = cur.fetchall()
    peers = []
    for row in rows:
        extra = parse_db_json(row[4], default={})
        if not isinstance(extra, dict):
            extra = {}
        peers.append({
            "symbol": row[0],
            "pe_ratio": row[1],
            "roe": row[2],
            "roce": row[3],
            "sector": extra.get("sector"),
        })
    return peers


async def run_fundamental_agent(state: dict) -> dict:
    symbol = state["symbol"]
    try:
        ratios = _get_fundamentals(symbol)
        dcf = {"intrinsic_value": ratios.pop("dcf_intrinsic", None), "wacc": 0.10}
        peers = _get_peers(symbol, n=3)
        from app.services.value_investing import compute_intrinsic_value_band

        owner_band = compute_intrinsic_value_band(symbol)
    except Exception as e:
        logger.error("Fundamental data load failed for %s: %s", symbol, e)
        state["fundamental_output"] = fundamental_from_data({}, [], symbol=symbol)
        state["fundamental_output"]["red_flags"] = [f"Data error: {e}"]
        return state

    from app.services.intelligent_investor import compute_graham_analysis

    graham_analysis = compute_graham_analysis(symbol)
    from app.services.fundamental_playbook import compute_fundamental_playbook

    try:
        fundamental_playbook = compute_fundamental_playbook(symbol)
    except Exception as exc:
        logger.warning("Fundamental playbook failed for %s: %s", symbol, exc)
        fundamental_playbook = {}

    payload = json.dumps(
        {
            "ratios": ratios,
            "dcf": dcf,
            "peers": peers,
            "owner_fair_value_band": owner_band,
            "graham_analysis": graham_analysis,
            "fundamental_playbook": fundamental_playbook,
        },
        default=str,
    )

    if not settings.groq_api_key:
        state["fundamental_output"] = fundamental_from_data(ratios, peers, symbol=symbol)
        return state

    try:
        client = Groq(api_key=settings.groq_api_key)
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Analyse {symbol}: {payload}"},
            ],
            response_format={"type": "json_object"},
            max_tokens=800,
            temperature=0.1,
        )
        output = parse_llm_json(response.choices[0].message.content)
    except Exception as e:
        logger.error("Fundamental agent LLM call failed for %s: %s", symbol, e)
        output = fundamental_from_data(ratios, peers, symbol=symbol)
        output["red_flags"] = list(output.get("red_flags", [])) + [f"LLM fallback: {e}"]

    state["fundamental_output"] = output
    return state
