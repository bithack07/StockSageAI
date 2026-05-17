"""User-facing step logs streamed over WebSocket during analysis."""
import time
from typing import Any

AGENT_LABELS: dict[str, str] = {
    "system": "System",
    "fundamental": "Fundamental",
    "technical": "Technical",
    "sentiment": "Sentiment",
    "ml": "ML models",
    "orchestrator": "Lead analyst",
}

PHASE_LABELS: dict[str, str] = {
    "data": "Market data",
    "cache": "Saved analysis",
    "agents": "Specialist agents",
    "synthesis": "Final prediction",
    "save": "Saving results",
}


async def send_step(
    websocket,
    *,
    phase: str,
    message: str,
    agent: str = "system",
    status: str = "info",
    detail: str | None = None,
) -> None:
    """Emit a single user-friendly log line (type: step_log)."""
    await websocket.send_json({
        "type": "step_log",
        "phase": phase,
        "phase_label": PHASE_LABELS.get(phase, phase.title()),
        "agent": agent,
        "agent_label": AGENT_LABELS.get(agent, agent.replace("_", " ").title()),
        "status": status,
        "message": message,
        "detail": detail,
        "timestamp": time.time(),
    })


def agent_result_summary(agent: str, output: dict[str, Any]) -> str:
    """One-line summary after an agent finishes."""
    if not output:
        return "Completed (limited data available)"

    if agent == "fundamental":
        verdict = output.get("valuation_verdict", "—")
        score = output.get("overall_score")
        suffix = f" · quality {score}/10" if score is not None else ""
        flags = output.get("red_flags") or []
        flag_note = f" · {len(flags)} flag(s)" if flags else ""
        return f"Valuation: {verdict}{suffix}{flag_note}"

    if agent == "technical":
        signal = output.get("signal", "—")
        trend = output.get("trend", "")
        trend_note = f" · trend {trend}" if trend else ""
        return f"Technical signal: {signal}{trend_note}"

    if agent == "sentiment":
        sig = output.get("sentiment_signal", "—")
        mood = output.get("market_mood") or output.get("mood", "")
        mood_note = f" · mood: {mood}" if mood else ""
        return f"Sentiment: {sig}{mood_note}"

    if agent == "ml":
        bull = output.get("bullish_prob")
        lstm = output.get("lstm") or {}
        graham = output.get("graham_prior") or {}
        parts = []
        if graham.get("graham_verdict"):
            parts.append(f"Graham {graham['graham_verdict']}")
        if bull is not None:
            parts.append(f"direction model {bull:.0%} bullish")
        if lstm.get("direction"):
            up = lstm.get("up_prob")
            up_s = f" ({up:.0%} up)" if up is not None else ""
            parts.append(f"LSTM 7d {lstm['direction']}{up_s}")
        prophet = output.get("prophet")
        if isinstance(prophet, dict) and prophet.get("trend"):
            parts.append(f"Prophet trend {prophet['trend']}")
        return " · ".join(parts) if parts else "ML scores computed"

    return "Analysis complete"
