"""NSE/BSE regular session hours (Asia/Kolkata)."""
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

# NSE cash market: Mon–Fri, pre-open 9:00–9:15, regular 9:15–15:30 IST
PRE_OPEN_START = time(9, 0)
REGULAR_OPEN = time(9, 15)
REGULAR_CLOSE = time(15, 30)

# NSE trading holidays (extend annually). Source: NSE circulars.
NSE_HOLIDAYS: set[date] = {
    # 2025
    date(2025, 2, 26), date(2025, 3, 14), date(2025, 3, 31), date(2025, 4, 10),
    date(2025, 4, 14), date(2025, 4, 18), date(2025, 5, 1), date(2025, 8, 15),
    date(2025, 8, 27), date(2025, 10, 2), date(2025, 10, 21), date(2025, 10, 22),
    date(2025, 11, 5), date(2025, 12, 25),
    # 2026
    date(2026, 1, 26), date(2026, 3, 3), date(2026, 3, 26), date(2026, 3, 31),
    date(2026, 4, 3), date(2026, 4, 14), date(2026, 5, 1), date(2026, 5, 28),
    date(2026, 6, 26), date(2026, 8, 15), date(2026, 10, 2), date(2026, 10, 20),
    date(2026, 11, 9), date(2026, 11, 24), date(2026, 12, 25),
}


def get_nse_market_status(now: datetime | None = None) -> dict:
    """
    Return market_status and human-readable session label.
    Status: OPEN | PREOPEN | CLOSED
    """
    now = now or datetime.now(IST)
    if now.tzinfo is None:
        now = now.replace(tzinfo=IST)
    else:
        now = now.astimezone(IST)

    today = now.date()
    t = now.time()

    if today.weekday() >= 5:  # Saturday, Sunday
        return {
            "market_status": "CLOSED",
            "session": "Weekend",
            "next_open_hint": "Monday 9:15 AM IST",
        }

    if today in NSE_HOLIDAYS:
        return {
            "market_status": "CLOSED",
            "session": "Holiday",
            "next_open_hint": "Next trading session 9:15 AM IST",
        }

    if PRE_OPEN_START <= t < REGULAR_OPEN:
        return {"market_status": "PREOPEN", "session": "Pre-open", "next_open_hint": None}

    if REGULAR_OPEN <= t <= REGULAR_CLOSE:
        return {"market_status": "OPEN", "session": "Regular", "next_open_hint": None}

    if t < PRE_OPEN_START:
        return {
            "market_status": "CLOSED",
            "session": "Before hours",
            "next_open_hint": "Opens 9:15 AM IST today",
        }

    return {
        "market_status": "CLOSED",
        "session": "After hours",
        "next_open_hint": "Opens 9:15 AM IST next trading day",
    }
