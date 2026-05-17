"""Celery app + beat schedule for all background pipelines."""
from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "stocksage",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.pipelines.market_data",
        "app.pipelines.technical_features",
        "app.pipelines.sentiment_pipeline",
        "app.pipelines.fundamentals",
        "app.tasks.alert_checker",
        "app.tasks.watchlist_overnight",
        "app.tasks.preanalysis",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

celery_app.conf.beat_schedule = {
    # Nightly OHLCV refresh — 18:30 IST = 13:00 UTC on weekdays
    "nightly-market-ingest": {
        "task": "pipelines.market_data.ingest_all_tracked",
        "schedule": crontab(hour=13, minute=0, day_of_week="1-5"),
    },
    # Technical features after OHLCV (18:45 IST = 13:15 UTC)
    "nightly-technical-features": {
        "task": "tasks.watchlist_overnight.compute_all_technical",
        "schedule": crontab(hour=13, minute=15, day_of_week="1-5"),
    },
    # Sentiment every 30 min during market hours (9:15 - 15:30 IST)
    "intraday-sentiment": {
        "task": "tasks.watchlist_overnight.run_all_sentiment",
        "schedule": crontab(minute="*/30", hour="3-10", day_of_week="1-5"),  # 9:00-16:00 IST
    },
    # Alert checker every 5 minutes during market hours
    "alert-checker": {
        "task": "tasks.alert_checker.check_all_alerts",
        "schedule": crontab(minute="*/5", hour="3-10", day_of_week="1-5"),
    },
    # Weekly fundamentals refresh (Sunday 3am IST)
    "weekly-fundamentals": {
        "task": "tasks.watchlist_overnight.refresh_all_fundamentals",
        "schedule": crontab(hour=21, minute=30, day_of_week="0"),  # Sunday 3am IST = Saturday 21:30 UTC
    },
    # Pre-analyze watchlist symbols after market close (18:00 IST = 12:30 UTC weekdays)
    "watchlist-preanalysis": {
        "task": "tasks.preanalysis.analyze_watchlist_all",
        "schedule": crontab(hour=12, minute=30, day_of_week="1-5"),
    },
}
