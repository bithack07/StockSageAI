"""Sentiment Analyst Agent — Groq/Llama 4."""
import json
import logging
from datetime import datetime, timezone

from groq import Groq

from app.agents.local_heuristics import sentiment_from_data
from app.config import settings
from app.db import get_db
from app.utils.json_helpers import parse_db_json, parse_llm_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a financial news analyst. You receive:
1. A composite sentiment score (-1 to +1) for the stock.
2. The top 5 most recent news headlines with individual scores.
3. Any detected high-impact event flags.
Your job:
1. Summarise the current market MOOD for this stock.
2. Identify if any HIGH_IMPACT events could override technical signals.
   Categories: EARNINGS_SURPRISE, MA_MERGER, MANAGEMENT_CHANGE, REGULATORY, MACRO.
3. Estimate the SENTIMENT_TREND: improving, stable, or deteriorating vs. 7 days ago.
4. Give a SENTIMENT_SIGNAL: VERY_POSITIVE / POSITIVE / NEUTRAL / NEGATIVE / VERY_NEGATIVE.
Return ONLY valid JSON."""


def _get_sentiment(symbol: str) -> dict:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT composite_score, article_count, top_news_json, event_flags_json, date
               FROM sentiment WHERE symbol=%s ORDER BY date DESC LIMIT 2""",
            (symbol,),
        )
        rows = cur.fetchall()

    if not rows:
        return {"composite_score": 0.0, "headlines": [], "event_flags": [], "trend": "stable"}

    latest = rows[0]
    prev = rows[1] if len(rows) > 1 else None

    composite = float(latest[0] or 0)
    top_news = parse_db_json(latest[2], default=[])
    event_flags = parse_db_json(latest[3], default=[])
    if not isinstance(top_news, list):
        top_news = []
    if not isinstance(event_flags, list):
        event_flags = []

    trend = "stable"
    if prev:
        prev_score = float(prev[0] or 0)
        delta = composite - prev_score
        if delta > 0.05:
            trend = "improving"
        elif delta < -0.05:
            trend = "deteriorating"

    return {
        "composite_score": composite,
        "headlines": top_news[:5],
        "event_flags": event_flags,
        "trend_vs_7d": trend,
        "article_count": latest[1],
        "date": str(latest[4]),
    }


async def run_sentiment_agent(state: dict) -> dict:
    symbol = state["symbol"]
    sent_data = _get_sentiment(symbol)

    if not settings.groq_api_key:
        state["sentiment_output"] = sentiment_from_data(sent_data)
        return state

    try:
        client = Groq(api_key=settings.groq_api_key)
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(sent_data)},
            ],
            response_format={"type": "json_object"},
            max_tokens=600,
            temperature=0.1,
        )
        output = parse_llm_json(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Sentiment agent LLM call failed for {symbol}: {e}")
        output = sentiment_from_data(sent_data)
        output["error"] = str(e)

    state["sentiment_output"] = output
    return state
