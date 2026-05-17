"""Technical Analyst Agent — Groq/Llama 4."""
import json
import logging
from decimal import Decimal

from groq import Groq

from app.agents.local_heuristics import technical_from_features
from app.config import settings
from app.db import get_db
from app.utils.json_helpers import parse_db_json, parse_llm_json
from app.pipelines.technical_features import _compute_sr_zones

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a technical analyst using the Stock Analysis Playbook (Murphy, Weinstein, Wyckoff, Van Tharp)
plus Graham's *Mr. Market* (Ch 8).
You receive indicators (15m, 1H, 1D), technical_playbook, and graham_mr_market.
Use technical_playbook when present:
- weinstein_stage: only buy longs in Stage 2 (Advancing)
- murphy_alignment: multi-timeframe trend
- wyckoff_volume: volume confirms price
- pre_trade_checklist: trade_allowed if ≥7/10 checks pass
- playbook_signal: rule-based composite
Your job:
1. TREND: UPTREND / DOWNTREND / SIDEWAYS (include EMA stack).
2. MOMENTUM: RSI, MACD, Stochastic — note Mr. Market EUPHORIC (RSI>70) vs FEARFUL (RSI<30).
3. Candlestick PATTERNS if any.
4. TIMEFRAME ALIGNMENT across 3 frames.
5. SUPPORT / RESISTANCE (3 each).
6. SIGNAL: STRONG_BUY / BUY / NEUTRAL / SELL / STRONG_SELL — weigh offer_vs_graham_number_pct:
   large discount to Graham # → less bearish; large premium → less bullish.
Return ONLY valid JSON. No markdown."""


def _coerce_numeric(val):
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (int, float)):
        return float(val)
    return val


def _get_tech_features(symbol: str, timeframe: str) -> dict:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT rsi, macd, macd_signal, bb_upper, bb_lower, atr,
                      ema20, ema50, ema200, stoch_k, stoch_d, vwap,
                      patterns_json, sr_zones_json
               FROM technical_features
               WHERE symbol=%s AND timeframe=%s
               ORDER BY date DESC LIMIT 1""",
            (symbol, timeframe),
        )
        row = cur.fetchone()
    if not row:
        return {}
    cols = [
        "rsi", "macd", "macd_signal", "bb_upper", "bb_lower", "atr",
        "ema20", "ema50", "ema200", "stoch_k", "stoch_d", "vwap",
        "patterns_json", "sr_zones_json",
    ]
    data = {col: _coerce_numeric(val) for col, val in zip(cols, row)}
    data["patterns_json"] = parse_db_json(data.get("patterns_json"), default={})
    data["sr_zones_json"] = parse_db_json(data.get("sr_zones_json"), default={})
    return data


def _ensure_technical_output(output: dict, tech_features: dict, sr_zones: dict, symbol: str) -> dict:
    """Guarantee a non-empty payload for the orchestrator even after partial failures."""
    if output and output.get("signal"):
        return output
    fallback = technical_from_features(tech_features, sr_zones, symbol=symbol)
    if output:
        fallback.update({k: v for k, v in output.items() if v is not None})
    return fallback


async def run_technical_agent(state: dict) -> dict:
    symbol = state["symbol"]

    try:
        tech_features = {
            "1D": _get_tech_features(symbol, "1d"),
            "1H": _get_tech_features(symbol, "1h"),
            "15m": _get_tech_features(symbol, "15m"),
        }
        daily = dict(tech_features.get("1D") or {})
        sr_zones = dict(daily.pop("sr_zones_json", None) or {})

        from app.services.intelligent_investor import graham_mr_market_technical

        try:
            graham_mr = graham_mr_market_technical(
                symbol,
                rsi=daily.get("rsi"),
                ema200=daily.get("ema200"),
            )
        except Exception as exc:
            logger.warning("Graham Mr. Market overlay failed for %s: %s", symbol, exc)
            graham_mr = {}

        from app.services.technical_playbook import compute_technical_playbook

        try:
            technical_playbook = compute_technical_playbook(symbol)
        except Exception as exc:
            logger.warning("Technical playbook failed for %s: %s", symbol, exc)
            technical_playbook = {}

        payload = json.dumps(
            {
                "indicators": tech_features,
                "sr_zones": sr_zones,
                "graham_mr_market": graham_mr,
                "technical_playbook": technical_playbook,
            },
            default=str,
        )

        if not settings.groq_api_key:
            output = technical_from_features(tech_features, sr_zones, symbol=symbol)
        else:
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
                logger.error("Technical agent LLM call failed for %s: %s", symbol, e)
                output = technical_from_features(tech_features, sr_zones, symbol=symbol)
                output["llm_error"] = str(e)

        if not daily and not any(tech_features.get(tf) for tf in ("1H", "15m")):
            output.setdefault(
                "data_note",
                "Daily indicators not in DB yet — using Graham Mr. Market heuristics. Re-run analysis after data refresh.",
            )

        state["technical_output"] = _ensure_technical_output(output, tech_features, sr_zones, symbol)
    except Exception as exc:
        logger.exception("Technical agent failed for %s", symbol)
        state["technical_output"] = {
            "signal": "NEUTRAL",
            "trend": "SIDEWAYS",
            "momentum": "NEUTRAL",
            "patterns": [],
            "timeframe_alignment": False,
            "support_levels": [],
            "resistance_levels": [],
            "source": "fallback",
            "error": str(exc),
        }

    return state
