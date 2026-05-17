"""Rule-based agent outputs when LLM APIs are unavailable or rate-limited."""
from app.services.intelligent_investor import compute_graham_analysis, graham_mr_market_technical


def fundamental_from_data(ratios: dict, peers: list, symbol: str | None = None) -> dict:
    graham = {}
    playbook = {}
    if symbol:
        try:
            graham = compute_graham_analysis(symbol)
        except Exception:
            graham = {}
        try:
            from app.services.fundamental_playbook import compute_fundamental_playbook

            playbook = compute_fundamental_playbook(symbol)
        except Exception:
            playbook = {}

    if playbook.get("playbook_verdict"):
        verdict = playbook["playbook_verdict"]
        fa_total = (playbook.get("fa_score") or {}).get("total") or 30
        score = round(min(10, fa_total / 5), 1)
    elif graham.get("valuation_verdict"):
        verdict = graham["valuation_verdict"]
        score = round((graham.get("graham_score") or 50) / 10, 1)
    else:
        pe = ratios.get("pe_ratio")
        verdict = "FAIRLY_VALUED"
        if pe is not None:
            peer_pes = [p.get("pe_ratio") for p in peers if p.get("pe_ratio")]
            avg_pe = sum(peer_pes) / len(peer_pes) if peer_pes else pe
            if pe < avg_pe * 0.85:
                verdict = "UNDERVALUED"
            elif pe > avg_pe * 1.15:
                verdict = "OVERVALUED"
        score = 8 if verdict == "UNDERVALUED" else 4 if verdict == "OVERVALUED" else 6

    red_flags = []
    debt = ratios.get("debt_equity")
    roe = ratios.get("roe")
    if debt is not None and debt > 1.5:
        red_flags.append("High debt/equity")
    if roe is not None and roe < 0.08:
        red_flags.append("Low ROE")
    for c in graham.get("defensive_criteria") or []:
        if c.get("status") == "fail" and c.get("id") in (
            "pe_max_15", "pb_max_1_5", "current_ratio_2", "debt_below_nca",
        ):
            red_flags.append(c.get("label", c.get("id")))
    red_flags.extend(playbook.get("red_flags") or [])

    return {
        "valuation_verdict": verdict,
        "dcf_margin_of_safety_pct": graham.get("margin_of_safety_pct") or ratios.get("dcf_intrinsic") or 0,
        "red_flags": red_flags,
        "peer_rank": 1 if verdict == "UNDERVALUED" else 2,
        "key_ratios_summary": {
            **{k: ratios[k] for k in ("pe_ratio", "pb_ratio", "roe", "roce", "debt_equity") if ratios.get(k) is not None},
            **{
                k: graham[k]
                for k in ("graham_number", "pe_times_pb", "margin_of_safety_pct")
                if graham.get(k) is not None
            },
        },
        "overall_score": score,
        "graham": {
            "score": graham.get("graham_score"),
            "graham_number": graham.get("graham_number"),
            "defensive_pass": graham.get("defensive_pass_count"),
            "framework": graham.get("framework"),
        },
        "playbook": {
            "fa_score": (playbook.get("fa_score") or {}).get("total"),
            "lynch_peg": (playbook.get("lynch") or {}).get("peg", {}).get("peg_ratio"),
            "moat_width": (playbook.get("moat") or {}).get("moat_width"),
            "greenblatt_verdict": (playbook.get("greenblatt") or {}).get("verdict"),
        } if playbook else None,
        "source": "analysis_playbook" if playbook else ("intelligent_investor" if graham else "local_heuristic"),
    }


def technical_from_features(
    features: dict,
    sr_zones: dict | None = None,
    symbol: str | None = None,
) -> dict:
    daily = features.get("1D") or features.get("1d") or {}
    rsi = daily.get("rsi")
    ema200 = daily.get("ema200")

    graham_tech = {}
    playbook_tech = {}
    if symbol:
        try:
            graham_tech = graham_mr_market_technical(symbol, rsi=rsi, ema200=ema200)
        except Exception:
            graham_tech = {}
        try:
            from app.services.technical_playbook import compute_technical_playbook

            playbook_tech = compute_technical_playbook(symbol)
        except Exception:
            playbook_tech = {}

    pb_signal = playbook_tech.get("playbook_signal")
    if pb_signal and playbook_tech.get("pre_trade_checklist", {}).get("trade_allowed"):
        sr = sr_zones or daily.get("sr_zones_json") or {}
        if isinstance(sr, str):
            import json
            try:
                sr = json.loads(sr)
            except Exception:
                sr = {}
        return {
            "trend": playbook_tech.get("playbook_trend", "SIDEWAYS"),
            "momentum": (playbook_tech.get("rsi") or {}).get("zone", "NEUTRAL"),
            "patterns": daily.get("patterns_json") or [],
            "timeframe_alignment": (playbook_tech.get("murphy_alignment") or {}).get("hourly_aligned", False),
            "support_levels": (sr.get("support") or [])[:3],
            "resistance_levels": (sr.get("resistance") or [])[:3],
            "signal": pb_signal,
            "weinstein_stage": (playbook_tech.get("weinstein_stage") or {}).get("label"),
            "pre_trade_checklist_passed": True,
            "source": "analysis_playbook",
        }

    if graham_tech.get("signal"):
        sr = sr_zones or daily.get("sr_zones_json") or {}
        if isinstance(sr, str):
            import json
            try:
                sr = json.loads(sr)
            except Exception:
                sr = {}
        return {
            "trend": graham_tech.get("trend", "SIDEWAYS"),
            "momentum": graham_tech.get("momentum", "NEUTRAL"),
            "patterns": daily.get("patterns_json") or [],
            "timeframe_alignment": bool(features.get("1H") or features.get("1h")),
            "support_levels": (sr.get("support") or [])[:3],
            "resistance_levels": (sr.get("resistance") or [])[:3],
            "signal": graham_tech["signal"],
            "mr_market_mood": graham_tech.get("mr_market_mood"),
            "offer_vs_graham_number_pct": graham_tech.get("offer_vs_graham_number_pct"),
            "source": "intelligent_investor",
        }

    macd = daily.get("macd")
    macd_signal = daily.get("macd_signal")
    signal = "NEUTRAL"
    trend = "SIDEWAYS"
    momentum = "NEUTRAL"

    if rsi is not None:
        if rsi >= 70:
            momentum = "OVERBOUGHT"
            signal = "SELL"
        elif rsi <= 30:
            momentum = "OVERSOLD"
            signal = "BUY"

    if macd is not None and macd_signal is not None:
        if macd > macd_signal:
            trend = "UPTREND"
            if signal == "NEUTRAL":
                signal = "BUY"
        elif macd < macd_signal:
            trend = "DOWNTREND"
            if signal == "NEUTRAL":
                signal = "SELL"

    sr = sr_zones or daily.get("sr_zones_json") or {}
    if isinstance(sr, str):
        import json
        try:
            sr = json.loads(sr)
        except Exception:
            sr = {}

    return {
        "trend": trend,
        "momentum": momentum,
        "patterns": daily.get("patterns_json") or [],
        "timeframe_alignment": bool(features.get("1H") or features.get("1h")),
        "support_levels": (sr.get("support") or [])[:3],
        "resistance_levels": (sr.get("resistance") or [])[:3],
        "signal": signal,
        "source": "local_heuristic",
    }


def sentiment_from_data(sent_data: dict) -> dict:
    score = float(sent_data.get("composite_score") or 0)
    if score >= 0.25:
        sig = "POSITIVE"
    elif score >= 0.1:
        sig = "POSITIVE"
    elif score <= -0.25:
        sig = "NEGATIVE"
    elif score <= -0.1:
        sig = "NEGATIVE"
    else:
        sig = "NEUTRAL"

    return {
        "mood": "positive" if score > 0.1 else "negative" if score < -0.1 else "neutral",
        "high_impact_events": sent_data.get("event_flags") or [],
        "sentiment_trend": sent_data.get("trend_vs_7d", "stable"),
        "sentiment_signal": sig,
        "composite_score": score,
        "source": "local_heuristic",
    }
