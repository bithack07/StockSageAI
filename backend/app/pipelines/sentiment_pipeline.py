"""Pipeline 3 — News & Sentiment (NewsAPI + GNews + FinBERT)."""
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from celery import shared_task

from app.cache import redis_client
from app.config import settings
from app.db import get_db

logger = logging.getLogger(__name__)

# FinBERT loaded once at module level (CPU, ~450MB)
_finbert = None


def _get_finbert():
    global _finbert
    if _finbert is None:
        try:
            from transformers import pipeline as hf_pipeline
            _finbert = hf_pipeline(
                "sentiment-analysis",
                model="ProsusAI/finbert",
                device=-1,  # CPU
                truncation=True,
                max_length=512,
            )
            logger.info("FinBERT loaded on CPU")
        except Exception as e:
            logger.error(f"Failed to load FinBERT: {e}")
    return _finbert


def _score_article(text: str) -> float:
    finbert = _get_finbert()
    if not finbert:
        return 0.0
    result = finbert(text[:512])[0]
    label = result["label"]
    score = result["score"]
    if label == "positive":
        return score
    elif label == "negative":
        return -score
    return 0.0


def _fetch_newsapi(query: str, days_back: int = 3) -> list:
    if not settings.newsapi_key:
        return []
    try:
        from newsapi import NewsApiClient
        client = NewsApiClient(api_key=settings.newsapi_key)
        from_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
        resp = client.get_everything(
            q=query, language="en", sort_by="publishedAt",
            from_param=from_date, page_size=20,
        )
        return resp.get("articles", [])
    except Exception as e:
        logger.warning(f"NewsAPI fetch failed: {e}")
        return []


def _fetch_gnews(query: str) -> list:
    if not settings.gnews_key:
        return []
    try:
        import requests
        resp = requests.get(
            "https://gnews.io/api/v4/search",
            params={"q": query, "token": settings.gnews_key, "lang": "en", "max": 10},
            timeout=10,
        )
        data = resp.json()
        articles = data.get("articles", [])
        # normalise to NewsAPI format
        return [
            {
                "title": a.get("title", ""),
                "description": a.get("description", ""),
                "publishedAt": a.get("publishedAt", ""),
                "source": {"name": a.get("source", {}).get("name", "")},
            }
            for a in articles
        ]
    except Exception as e:
        logger.warning(f"GNews fetch failed: {e}")
        return []


def _parse_dt(dt_str: str) -> datetime:
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            dt = datetime.strptime(dt_str[:19] + "Z", "%Y-%m-%dT%H:%M:%SZ")
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return datetime.now(timezone.utc)


@shared_task(name="pipelines.sentiment_pipeline.run_sentiment_pipeline", bind=True, max_retries=2)
def run_sentiment_pipeline(self, symbol: str, company_name: Optional[str] = None):
    try:
        query = f"{company_name or symbol} OR {symbol}"
        articles = _fetch_newsapi(query) + _fetch_gnews(query)

        if not articles:
            logger.info(f"No news articles for {symbol}")
            return {"symbol": symbol, "articles": 0}

        results = []
        for art in articles:
            art_hash = hashlib.md5((art.get("title") or "").encode()).hexdigest()
            if redis_client.exists(f"news_seen:{art_hash}"):
                continue

            text = (art.get("title") or "") + " " + (art.get("description") or "")[:200]
            score = _score_article(text.strip())
            results.append({
                "hash": art_hash,
                "title": art.get("title", ""),
                "score": score,
                "pub_at": art.get("publishedAt", ""),
                "source": art.get("source", {}).get("name", ""),
            })
            redis_client.setex(f"news_seen:{art_hash}", 86400, "1")

        if not results:
            return {"symbol": symbol, "articles": 0}

        # Time-weighted composite score
        now = datetime.now(timezone.utc)
        weighted_scores, weights = [], []
        for r in results:
            age_h = (now - _parse_dt(r["pub_at"])).total_seconds() / 3600
            w = 3 if age_h < 6 else (2 if age_h < 24 else 1)
            weighted_scores.append(r["score"] * w)
            weights.append(w)

        composite = sum(weighted_scores) / sum(weights) if weights else 0.0
        today = datetime.now(timezone.utc).date()
        top_news = sorted(results, key=lambda x: x["pub_at"], reverse=True)[:5]

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO sentiment (symbol, date, composite_score, article_count, top_news_json, event_flags_json)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (symbol, date) DO UPDATE
                   SET composite_score=EXCLUDED.composite_score,
                       article_count=EXCLUDED.article_count,
                       top_news_json=EXCLUDED.top_news_json""",
                (symbol, today, round(composite, 4), len(results), json.dumps(top_news), json.dumps([])),
            )

        logger.info(f"Sentiment pipeline done for {symbol}: score={composite:.3f}, n={len(results)}")
        return {"symbol": symbol, "composite_score": composite, "articles": len(results)}

    except Exception as exc:
        logger.error(f"Sentiment pipeline failed for {symbol}: {exc}")
        raise self.retry(exc=exc, countdown=120)
