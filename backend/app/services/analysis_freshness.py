"""When to reuse saved analysis vs run agents again — keep compute minimal."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from app.market_hours import get_nse_market_status

# During NSE regular session, prices move — refresh sooner.
TTL_MINUTES_MARKET_OPEN = 4 * 60
# After close / weekend, same thesis can sit overnight.
TTL_MINUTES_MARKET_CLOSED = 24 * 60


def analysis_ttl_minutes() -> int:
    status = get_nse_market_status().get("market_status", "CLOSED")
    return TTL_MINUTES_MARKET_OPEN if status == "OPEN" else TTL_MINUTES_MARKET_CLOSED


def _parse_created_at(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def analysis_age_minutes(created_at: Any) -> Optional[int]:
    dt = _parse_created_at(created_at)
    if not dt:
        return None
    delta = datetime.now(timezone.utc) - dt.astimezone(timezone.utc)
    return max(0, int(delta.total_seconds() // 60))


def is_analysis_fresh(created_at: Any) -> bool:
    age = analysis_age_minutes(created_at)
    if age is None:
        return False
    return age <= analysis_ttl_minutes()


def freshness_meta(created_at: Any) -> dict:
    age = analysis_age_minutes(created_at)
    ttl = analysis_ttl_minutes()
    fresh = age is not None and age <= ttl
    expires_in = max(0, ttl - age) if age is not None else None
    return {
        "fresh": fresh,
        "stale": age is not None and not fresh,
        "age_minutes": age,
        "ttl_minutes": ttl,
        "expires_in_minutes": expires_in,
        "market_status": get_nse_market_status().get("market_status"),
    }


def _json_load(val: Any) -> dict:
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            return {}
    return {}


def build_latest_payload(row: tuple, canon_symbol: str, display: dict) -> dict:
    """Row: id, symbol, created_at, fundamental, technical, sentiment, prediction."""
    created_at = row[2]
    meta = freshness_meta(created_at)
    pred = _json_load(row[6])
    return {
        "id": str(row[0]),
        "created_at": str(created_at),
        "symbol": canon_symbol,
        "fundamental": _json_load(row[3]),
        "technical": _json_load(row[4]),
        "sentiment": _json_load(row[5]),
        "prediction": pred,
        **meta,
        **display,
    }
