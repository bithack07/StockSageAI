"""Alert checker — runs every 5 min during market hours via Celery beat."""
import logging

from celery import shared_task

from app.cache import redis_client
from app.db import get_db
from app.pipelines.market_data import get_latest_quote

logger = logging.getLogger(__name__)


@shared_task(name="tasks.alert_checker.check_all_alerts")
def check_all_alerts():
    """Evaluate all active alerts and mark triggered ones."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, user_id, symbol, condition, threshold FROM alerts WHERE is_active = TRUE"
        )
        alerts = cur.fetchall()

    triggered = []
    for alert_id, user_id, symbol, condition, threshold in alerts:
        try:
            quote = get_latest_quote(symbol)
            price = quote.get("price")
            if price is None:
                continue

            triggered_flag = False

            if condition == "price_above" and price > float(threshold):
                triggered_flag = True
            elif condition == "price_below" and price < float(threshold):
                triggered_flag = True
            elif condition in ("rsi_above", "rsi_below"):
                rsi = _get_latest_rsi(symbol)
                if rsi is not None:
                    if condition == "rsi_above" and rsi > float(threshold):
                        triggered_flag = True
                    elif condition == "rsi_below" and rsi < float(threshold):
                        triggered_flag = True

            if triggered_flag:
                triggered.append((alert_id, user_id, symbol, condition, threshold, price))

        except Exception as e:
            logger.error(f"Alert check failed for {symbol}: {e}")

    if triggered:
        with get_db() as conn:
            cur = conn.cursor()
            for alert_id, user_id, symbol, condition, threshold, price in triggered:
                cur.execute(
                    "UPDATE alerts SET is_active=FALSE, triggered_at=NOW() WHERE id=%s",
                    (alert_id,),
                )
                # Publish to Redis channel for real-time notification
                redis_client.publish(
                    f"alerts:{user_id}",
                    f"ALERT:{symbol}:{condition}:{threshold}:current={price}",
                )

    logger.info(f"Alert check: {len(alerts)} active, {len(triggered)} triggered")
    return {"checked": len(alerts), "triggered": len(triggered)}


def _get_latest_rsi(symbol: str) -> float | None:
    cached = redis_client.get(f"rsi:{symbol}")
    if cached:
        return float(cached)
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT rsi FROM technical_features WHERE symbol=%s AND timeframe='1d' ORDER BY date DESC LIMIT 1",
                (symbol,),
            )
            row = cur.fetchone()
        if row and row[0]:
            rsi = float(row[0])
            redis_client.setex(f"rsi:{symbol}", 300, str(rsi))
            return rsi
    except Exception:
        pass
    return None
