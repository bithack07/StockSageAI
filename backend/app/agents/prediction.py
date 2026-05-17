"""Orchestrator synthesis — Gemini primary, Groq fallback, heuristics last resort."""
import asyncio
import json
import logging
from datetime import datetime, timezone

from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the lead investment analyst for Indian equities (NSE/BSE).

You receive:
- fundamental: AI fundamental agent (valuation_verdict: UNDERVALUED / FAIRLY_VALUED / OVERVALUED from ratios & peers)
- technical, sentiment, ml_scores: near-term price drivers
- owner_fair_value: DCF / earnings-band model (long-term fair value)
- graham_analysis: Benjamin Graham *Intelligent Investor* (Graham number, defensive checklist, margin of safety)
- unified_playbook: FA score (Lynch PEG, Greenblatt, Dorsey moat) + TA (Weinstein stage, Murphy, Wyckoff checklist)

IMPORTANT — two valuation lenses:
- owner_fair_value.verdict = long-term intrinsic band (DCF + sector P/E)
- fundamental.valuation_verdict = AI read of quality, peers, and multiples
- direction (BULLISH/BEARISH/NEUTRAL) = near-term actionable bias (14-day horizon), driven mainly by technical + sentiment + ML, moderated by fundamental

Rules:
- Do NOT say a stock is "undervalued" in rationale if fundamental.valuation_verdict is OVERVALUED unless you explain owner_fair_value says UNDERVALUED (long-term vs near-term).
- If owner_fair_value is UNDERVALUED but technical is SELL and fundamental is OVERVALUED → direction is usually BEARISH or NEUTRAL with LOW/MEDIUM conviction; explain the split clearly.
- If signals conflict, lower conviction and prefer NEUTRAL over extreme direction.
- ML bullish_prob < 0.35 with technical SELL supports bearish lean.
- Always cite which agent drove direction.

Return ONLY valid JSON with keys:
  direction (BULLISH/BEARISH/NEUTRAL),
  conviction (HIGH/MEDIUM/LOW),
  confidence_pct (0-100),
  target_price_range [low, high] or [null, null],
  horizon_days (7, 14, or 30),
  rationale (3-4 sentences),
  key_signals (list of 3-5 bullet strings),
  risk_factors (list of 2-3 strings),
  do_not_trade_if (single string — market condition that invalidates this view),
  valuation_note (1-2 sentences on how owner_fair_value vs fundamental.valuation_verdict relate to direction)."""


def _build_payload(state: dict) -> dict:
    from app.services.value_investing import compute_intrinsic_value_band

    symbol = state.get("symbol", "")
    owner_fair_value = {}
    if symbol:
        try:
            owner_fair_value = compute_intrinsic_value_band(symbol)
        except Exception as exc:
            logger.warning("owner_fair_value failed for %s: %s", symbol, exc)

    graham_analysis = {}
    if symbol:
        try:
            from app.services.intelligent_investor import compute_graham_analysis

            graham_analysis = compute_graham_analysis(symbol)
        except Exception as exc:
            logger.warning("graham_analysis failed for %s: %s", symbol, exc)

    unified_playbook = {}
    if symbol:
        try:
            from app.services.analysis_playbook import compute_unified_playbook

            unified_playbook = compute_unified_playbook(symbol)
        except Exception as exc:
            logger.warning("unified_playbook failed for %s: %s", symbol, exc)

    return {
        "fundamental": state.get("fundamental_output", {}),
        "technical": state.get("technical_output", {}),
        "sentiment": state.get("sentiment_output", {}),
        "ml_scores": state.get("ml_scores", {}),
        "owner_fair_value": owner_fair_value,
        "graham_analysis": graham_analysis,
        "unified_playbook": unified_playbook,
    }


def _detect_conflicts(payload: dict, direction: str) -> list[str]:
    fund = payload.get("fundamental", {})
    owner = payload.get("owner_fair_value", {})
    tech = payload.get("technical", {})

    fund_v = fund.get("valuation_verdict") or "FAIRLY_VALUED"
    owner_v = owner.get("verdict") or "INSUFFICIENT_DATA"
    tech_sig = tech.get("signal", "NEUTRAL")
    conflicts: list[str] = []

    if owner_v == "UNDERVALUED" and fund_v == "OVERVALUED":
        conflicts.append(
            "Long-term DCF band suggests undervaluation, but the fundamental agent sees rich valuation vs peers."
        )
    if owner_v == "UNDERVALUED" and direction == "BEARISH":
        conflicts.append(
            "Fair-value model looks attractive for holders, but near-term agents lean bearish (often technical downtrend)."
        )
    if owner_v == "OVERVALUED" and direction == "BULLISH":
        conflicts.append(
            "Price may be extended vs fair-value band despite a bullish near-term signal."
        )
    if fund_v == "OVERVALUED" and tech_sig in ("BUY", "STRONG_BUY"):
        conflicts.append(
            "Technical buy signal conflicts with overvalued fundamental verdict."
        )
    if fund_v == "UNDERVALUED" and tech_sig in ("SELL", "STRONG_SELL"):
        conflicts.append(
            "Technical sell signal conflicts with undervalued fundamental verdict — possible pullback in a value name."
        )
    return conflicts


def _valuation_note(payload: dict, direction: str) -> str:
    fund_v = payload.get("fundamental", {}).get("valuation_verdict", "—")
    owner = payload.get("owner_fair_value", {})
    owner_v = owner.get("verdict", "—")
    tech = payload.get("technical", {}).get("signal", "—")
    parts = [
        f"AI fundamental: {fund_v}. DCF fair-value model: {owner_v}.",
        f"Near-term direction {direction} weighs technical ({tech}), sentiment, and ML on a ~14-day horizon.",
    ]
    if owner_v == "UNDERVALUED" and fund_v == "OVERVALUED":
        parts.append(
            "Long-term value and near-term price action are telling different stories — treat conviction accordingly."
        )
    return " ".join(parts)


def _enrich_prediction(prediction: dict, payload: dict, symbol: str) -> dict:
    direction = prediction.get("direction", "NEUTRAL")
    conflicts = _detect_conflicts(payload, direction)
    prediction.setdefault("conflicts", conflicts)
    if not prediction.get("valuation_note"):
        prediction["valuation_note"] = _valuation_note(payload, direction)
    prediction["agent_fundamental_verdict"] = payload.get("fundamental", {}).get("valuation_verdict")
    prediction["owner_fair_value_verdict"] = payload.get("owner_fair_value", {}).get("verdict")
    prediction["analyzed_at"] = datetime.now(timezone.utc).isoformat()

    if conflicts and prediction.get("conviction") == "HIGH":
        prediction["conviction"] = "MEDIUM"
        conf = prediction.get("confidence_pct", 60)
        if isinstance(conf, (int, float)):
            prediction["confidence_pct"] = min(int(conf), 65)

    return prediction


def _gemini_synthesis(payload: dict, symbol: str) -> dict:
    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(
        SYSTEM_PROMPT + f"\n\nSymbol: {symbol}\nAgent outputs:\n" + json.dumps(payload, default=str),
        generation_config={"response_mime_type": "application/json"},
    )
    result = json.loads(response.text)
    result["source"] = "gemini"
    return result


def _groq_synthesis(payload: dict, symbol: str) -> dict:
    from groq import Groq

    client = Groq(api_key=settings.groq_api_key)
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Synthesise analysis for {symbol}: {json.dumps(payload, default=str)}"},
        ],
        response_format={"type": "json_object"},
        max_tokens=900,
        temperature=0.15,
    )
    result = json.loads(response.choices[0].message.content)
    result["source"] = "groq"
    return result


async def run_orchestrator_synthesis(state: dict) -> dict:
    payload = _build_payload(state)
    symbol = state.get("symbol", "")
    prediction = None

    if settings.gemini_api_key:
        try:
            prediction = await asyncio.wait_for(
                asyncio.to_thread(_gemini_synthesis, payload, symbol),
                timeout=20.0,
            )
        except Exception as e:
            logger.warning(f"Gemini synthesis failed for {symbol}: {e}")

    if prediction is None and settings.groq_api_key:
        try:
            prediction = await asyncio.wait_for(
                asyncio.to_thread(_groq_synthesis, payload, symbol),
                timeout=25.0,
            )
            logger.info(f"Orchestrator used Groq synthesis for {symbol}")
        except Exception as e:
            logger.error(f"Groq synthesis failed for {symbol}: {e}")

    if prediction is None:
        prediction = _rule_based_synthesis(payload, symbol)

    state["prediction"] = _enrich_prediction(prediction, payload, symbol)
    return state


def _trade_invalidation(direction: str, payload: dict) -> str:
    tech = payload.get("technical", {})
    supports = tech.get("support_levels") or []
    resistances = tech.get("resistance_levels") or []
    if direction == "BULLISH" and supports:
        return f"Price closes below support near ₹{supports[0]} with rising volume."
    if direction == "BEARISH" and resistances:
        return f"Price breaks above resistance near ₹{resistances[0]} on strong buying."
    if direction == "NEUTRAL":
        return "Agents align on a clear directional signal — reassess if conviction strengthens."
    return "Major negative news or a sharp index sell-off invalidates this setup."


def _rule_based_synthesis(payload: dict, symbol: str) -> dict:
    """Deterministic synthesis when LLM APIs are unavailable."""
    tech_signal = payload["technical"].get("signal", "NEUTRAL")
    fund_verdict = payload["fundamental"].get("valuation_verdict", "FAIRLY_VALUED")
    owner_verdict = payload.get("owner_fair_value", {}).get("verdict")
    sent_signal = payload["sentiment"].get("sentiment_signal", "NEUTRAL")
    ml = payload["ml_scores"]
    ml_bull = ml.get("bullish_prob", 0.5)
    lstm = ml.get("lstm") or {}
    lstm_up = lstm.get("up_prob", 0.5)

    bullish_count = sum([
        tech_signal in ("STRONG_BUY", "BUY"),
        fund_verdict == "UNDERVALUED",
        sent_signal in ("VERY_POSITIVE", "POSITIVE"),
        ml_bull > 0.55,
        lstm.get("direction") == "BULLISH",
    ])
    bearish_count = sum([
        tech_signal in ("STRONG_SELL", "SELL"),
        fund_verdict == "OVERVALUED",
        sent_signal in ("VERY_NEGATIVE", "NEGATIVE"),
        ml.get("bearish_prob", 0.25) > 0.45,
        lstm.get("direction") == "BEARISH",
    ])

    if bullish_count >= 3 and bearish_count < 3:
        direction = "BULLISH"
        conviction = "HIGH" if bullish_count >= 4 and bearish_count <= 1 else "MEDIUM"
    elif bearish_count >= 3 and bullish_count < 3:
        direction = "BEARISH"
        conviction = "HIGH" if bearish_count >= 4 and bullish_count <= 1 else "MEDIUM"
    elif bearish_count >= 2 and bullish_count >= 2:
        direction = "NEUTRAL"
        conviction = "LOW"
    elif bearish_count > bullish_count:
        direction = "BEARISH"
        conviction = "MEDIUM" if bearish_count == 2 else "LOW"
    elif bullish_count > bearish_count:
        direction = "BULLISH"
        conviction = "MEDIUM" if bullish_count == 2 else "LOW"
    else:
        direction = "NEUTRAL"
        conviction = "LOW"

    conflicts = _detect_conflicts(payload, direction)
    if conflicts and conviction == "HIGH":
        conviction = "MEDIUM"

    confidence = (
        min(40 + bullish_count * 12, 90) if direction == "BULLISH"
        else min(40 + bearish_count * 12, 90) if direction == "BEARISH"
        else 40
    )
    if conflicts:
        confidence = min(confidence, 65)

    rationale_parts = [
        f"For {symbol}, technical reads {tech_signal}, AI fundamental {fund_verdict}, sentiment {sent_signal}.",
        f"ML direction model: {ml_bull:.0%} bullish; LSTM 7d up: {lstm_up:.0%}.",
    ]
    if owner_verdict and owner_verdict not in ("INSUFFICIENT_DATA", fund_verdict):
        rationale_parts.append(f"DCF fair-value model: {owner_verdict} (long-term; separate from AI agents).")
    if direction == "BULLISH":
        rationale_parts.append(f"{bullish_count} near-term signal buckets lean bullish.")
    elif direction == "BEARISH":
        rationale_parts.append(f"{bearish_count} near-term signal buckets lean bearish.")
    else:
        rationale_parts.append("Near-term signals are mixed; no strong edge until agents align.")

    return {
        "direction": direction,
        "conviction": conviction,
        "confidence_pct": confidence,
        "target_price_range": [None, None],
        "horizon_days": 14,
        "rationale": " ".join(rationale_parts),
        "key_signals": [
            f"Technical: {tech_signal}",
            f"AI fundamental: {fund_verdict}",
            f"DCF model: {owner_verdict or '—'}",
            f"Sentiment: {sent_signal}",
            f"ML bullish probability: {ml_bull:.0%}",
            f"LSTM ({lstm.get('horizon_days', 7)}d): {lstm.get('direction', 'N/A')} ({lstm_up:.0%} up)",
        ],
        "risk_factors": [
            "Heuristic synthesis only — confirm with fresh price action.",
            "Indian market macro or sector news can override model signals quickly.",
        ],
        "do_not_trade_if": _trade_invalidation(direction, payload),
        "valuation_note": _valuation_note(payload, direction),
        "conflicts": conflicts,
        "source": "fallback_heuristic",
    }
