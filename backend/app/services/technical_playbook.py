"""
Technical analysis playbook — rules from Murphy, Weinstein, Wyckoff, O'Neil, Bulkowski, Van Tharp.

Encoded from Stock_Analysis_Complete_Note.md.pdf for programmatic scoring in agents.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

import numpy as np
import pandas as pd

from app.services.india_market import normalize_nse_symbol

logger = logging.getLogger(__name__)

# Murphy — three principles (metadata for UI/agents)
MURPHY_PRINCIPLES = [
    "Price discounts everything",
    "Price moves in trends",
    "History repeats — psychology creates patterns",
]

# Weinstein stages
STAGE_ACCUMULATION = 1
STAGE_ADVANCING = 2
STAGE_DISTRIBUTION = 3
STAGE_DECLINING = 4

# RSI (Constance Brown — strong trend can hold >70)
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
RSI_NEUTRAL_LOW = 40
RSI_NEUTRAL_HIGH = 60

# ADX (Murphy / playbook)
ADX_STRONG_TREND = 25
ADX_WEAK_TREND = 20

# Van Tharp — minimum R:R
MIN_RISK_REWARD = 2.0

# High-conviction checklist: need most items true
_CHECKLIST_MIN_PASS = 7


def _load_ohlcv(symbol: str, limit: int = 260) -> pd.DataFrame:
    sym = normalize_nse_symbol(symbol)
    try:
        from app.db import get_db

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT date, open, high, low, close, volume FROM ohlcv "
                "WHERE symbol=%s ORDER BY date DESC LIMIT %s",
                (sym, limit),
            )
            rows = cur.fetchall()
    except Exception as exc:
        logger.debug("OHLCV DB unavailable for %s: %s", sym, exc)
        return pd.DataFrame()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
    df = df.iloc[::-1].reset_index(drop=True)
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _load_tech_row(symbol: str, timeframe: str = "1d") -> dict:
    sym = normalize_nse_symbol(symbol)
    try:
        from app.db import get_db

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT rsi, macd, macd_signal, bb_upper, bb_lower, atr,
                          ema20, ema50, ema200, stoch_k, stoch_d, vwap,
                          patterns_json, sr_zones_json
                   FROM technical_features
                   WHERE symbol=%s AND timeframe=%s
                   ORDER BY date DESC LIMIT 1""",
                (sym, timeframe),
            )
            row = cur.fetchone()
    except Exception as exc:
        logger.debug("Technical features DB unavailable for %s: %s", sym, exc)
        return {}
    if not row:
        return {}
    cols = [
        "rsi", "macd", "macd_signal", "bb_upper", "bb_lower", "atr",
        "ema20", "ema50", "ema200", "stoch_k", "stoch_d", "vwap",
        "patterns_json", "sr_zones_json",
    ]
    data = dict(zip(cols, row))
    for k in ("patterns_json", "sr_zones_json"):
        if isinstance(data.get(k), str):
            try:
                data[k] = json.loads(data[k])
            except json.JSONDecodeError:
                data[k] = {}
    return data


def compute_adx(df: pd.DataFrame, period: int = 14) -> Optional[float]:
    """ADX from OHLCV (Wilder). Returns latest ADX or None."""
    if df is None or len(df) < period + 5:
        return None
    high, low, close = df["high"], df["low"], df["close"]
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr)
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)) * 100
    adx = dx.ewm(alpha=1 / period, adjust=False).mean()
    val = adx.iloc[-1]
    return round(float(val), 2) if val == val else None


def weinstein_stage(df: pd.DataFrame, ema50: Optional[float], ema200: Optional[float]) -> dict[str, Any]:
    """
    Stan Weinstein four-stage model (30-week ≈ 150d; we use 50/200 EMA proxy).
    Only buy longs in Stage 2; only short in Stage 4.
    """
    if df.empty or len(df) < 30:
        return {
            "stage": None,
            "label": "UNKNOWN",
            "trade_bias": "WAIT",
            "note": "Insufficient OHLCV for stage analysis",
        }

    close = float(df["close"].iloc[-1])
    ema50 = ema50 or float(df["close"].ewm(span=50, adjust=False).mean().iloc[-1])
    ema200 = ema200 or float(df["close"].ewm(span=200, adjust=False).mean().iloc[-1])

    # Slope of 50 EMA over ~10 weeks
    ema50_series = df["close"].ewm(span=50, adjust=False).mean()
    slope = float(ema50_series.iloc[-1] - ema50_series.iloc[max(0, len(ema50_series) - 25)])
    vol_recent = float(df["volume"].tail(20).mean())
    vol_prior = float(df["volume"].iloc[-60:-20].mean()) if len(df) >= 60 else vol_recent
    vol_ratio = vol_recent / vol_prior if vol_prior > 0 else 1.0

    pct_from_200 = (close / ema200 - 1) * 100 if ema200 else 0

    stage = STAGE_ACCUMULATION
    label = "Accumulation"
    bias = "AVOID_NEW_LONGS"

    if close > ema200 and slope > 0 and close > ema50:
        stage = STAGE_ADVANCING
        label = "Advancing (Stage 2)"
        bias = "BUY_LONGS_ONLY"
    elif close > ema200 and abs(slope) < close * 0.002 and vol_ratio > 1.1:
        stage = STAGE_DISTRIBUTION
        label = "Distribution (Stage 3)"
        bias = "DANGER_NO_BUY"
    elif close < ema200 and slope < 0:
        stage = STAGE_DECLINING
        label = "Declining (Stage 4)"
        bias = "SHORT_ONLY_OR_AVOID"
    elif abs(pct_from_200) < 8 and abs(slope) < close * 0.001:
        stage = STAGE_ACCUMULATION
        label = "Accumulation (Stage 1)"
        bias = "WATCHLIST_ONLY"

    return {
        "stage": stage,
        "label": label,
        "trade_bias": bias,
        "close": close,
        "ema50": round(ema50, 2),
        "ema200": round(ema200, 2),
        "ema50_slope_25d": round(slope, 2),
        "volume_expansion_ratio": round(vol_ratio, 2),
        "framework": "Stan Weinstein — stage analysis",
    }


def murphy_trend_alignment(
    daily: dict,
    hourly: dict,
    ema_stack_bull: bool,
) -> dict[str, Any]:
    """Top-down alignment: daily captain, 1H navigator."""
    d_trend = "SIDEWAYS"
    price_above_200 = None
    if daily.get("ema200") and daily.get("close"):
        price_above_200 = daily.get("close") > daily["ema200"]
    elif daily.get("ema200"):
        pass

    if daily.get("ema20") and daily.get("ema50") and daily.get("ema200"):
        if daily["ema20"] > daily["ema50"] > daily["ema200"]:
            d_trend = "UPTREND"
        elif daily["ema20"] < daily["ema50"] < daily["ema200"]:
            d_trend = "DOWNTREND"

    h_align = False
    if hourly.get("ema20") and hourly.get("ema50"):
        h_align = (hourly["ema20"] > hourly["ema50"]) == (d_trend == "UPTREND")

    golden_cross = False
    death_cross = False
    if daily.get("ema50") and daily.get("ema200"):
        golden_cross = daily["ema50"] > daily["ema200"]
        death_cross = daily["ema50"] < daily["ema200"]

    score = 0
    if d_trend == "UPTREND":
        score += 2
    if h_align:
        score += 1
    if golden_cross:
        score += 1
    if ema_stack_bull:
        score += 1

    return {
        "daily_trend": d_trend,
        "hourly_aligned": h_align,
        "golden_cross": golden_cross,
        "death_cross": death_cross,
        "alignment_score": score,
        "max_score": 5,
        "framework": "John Murphy — multi-timeframe / trend",
    }


def wyckoff_volume_signal(df: pd.DataFrame) -> dict[str, Any]:
    """Wyckoff: price direction vs volume (Anna Coulling / playbook)."""
    if len(df) < 5:
        return {"signal": "UNKNOWN", "framework": "Wyckoff — volume confirmation"}

    last = df.iloc[-1]
    prev = df.iloc[-2]
    price_up = last["close"] > prev["close"]
    vol_up = last["volume"] > prev["volume"]

    if price_up and vol_up:
        sig, note = "BULLISH_CONFIRM", "Price up + volume up — genuine demand"
    elif price_up and not vol_up:
        sig, note = "WEAK_RALLY", "Price up + volume down — suspect rally"
    elif not price_up and vol_up:
        sig, note = "DISTRIBUTION_OR_CAPITULATION", "Price down + volume up — distribution or capitulation"
    else:
        sig, note = "HEALTHY_PULLBACK", "Price down + low volume — normal pullback"

    return {"signal": sig, "note": note, "framework": "Wyckoff — volume analysis"}


def rsi_interpretation(rsi: Optional[float], trend: str) -> dict[str, Any]:
    """Constance Brown: RSI>70 can be continuation in strong uptrends."""
    if rsi is None:
        return {"zone": "UNKNOWN", "action_hint": "NEUTRAL"}
    if rsi >= RSI_OVERBOUGHT:
        zone = "OVERBOUGHT"
        hint = "CONTINUATION" if trend == "UPTREND" else "CAUTION_SELL"
    elif rsi <= RSI_OVERSOLD:
        zone = "OVERSOLD"
        hint = "CAUTION_BUY" if trend == "DOWNTREND" else "REVERSAL_WATCH"
    elif RSI_NEUTRAL_LOW <= rsi <= RSI_NEUTRAL_HIGH:
        zone = "NEUTRAL"
        hint = "NEUTRAL"
    else:
        zone = "MID"
        hint = "NEUTRAL"
    return {
        "rsi": rsi,
        "zone": zone,
        "action_hint": hint,
        "framework": "RSI — Murphy / Constance Brown",
    }


def bollinger_state(
    close: Optional[float],
    bb_upper: Optional[float],
    bb_lower: Optional[float],
    df: pd.DataFrame,
) -> dict[str, Any]:
    """Bollinger squeeze and band ride detection."""
    if close is None or bb_upper is None or bb_lower is None:
        return {"state": "UNKNOWN"}
    width = (bb_upper - bb_lower) / close if close else None
    squeeze = False
    if not df.empty and len(df) >= 20 and width is not None:
        # Compare current band width to 20d average width proxy
        recent = df["close"].tail(20)
        std = recent.std()
        squeeze = width < (2 * std / close) if close and std == std else False

    state = "MID"
    if close >= bb_upper * 0.99:
        state = "UPPER_BAND_RIDE"
    elif close <= bb_lower * 1.01:
        state = "LOWER_BAND_RIDE"

    return {
        "state": state,
        "squeeze": squeeze,
        "band_width_pct": round(width * 100, 2) if width else None,
        "framework": "Bollinger Bands — playbook Phase 6",
    }


def pattern_signals(patterns: dict) -> dict[str, Any]:
    """Map TA-Lib candle codes to Bulkowski-style bias."""
    if not patterns:
        return {"active_patterns": [], "bias": "NEUTRAL"}

    bullish = {
        "CDL_HAMMER", "CDL_MORNINGSTAR", "CDL_ENGULFING",
        "CDL_THREEWHITESOLDIERS", "CDL_HARAMI",
    }
    bearish = {
        "CDL_SHOOTINGSTAR", "CDL_DARKCLOUDCOVER", "CDL_MARUBOZU",
    }
    active = [k for k, v in patterns.items() if v and v != 0]
    bias = "NEUTRAL"
    if any(p in bullish for p in active):
        bias = "BULLISH"
    if any(p in bearish for p in active):
        bias = "BEARISH" if bias == "NEUTRAL" else "MIXED"

    return {
        "active_patterns": active,
        "bias": bias,
        "framework": "Bulkowski / candlestick — pattern confirmation only",
    }


def van_tharp_risk_hint(
    close: Optional[float],
    atr: Optional[float],
    support_levels: list,
) -> dict[str, Any]:
    """ATR-based stop and 1:2 R:R framing (Van Tharp)."""
    if not close or not atr:
        return {"framework": "Van Tharp — R-multiple", "note": "Need price and ATR for stop sizing"}

    stop_atr = round(close - 2 * atr, 2)
    stop_support = support_levels[0] if support_levels else stop_atr
    stop = min(stop_atr, stop_support) if support_levels else stop_atr
    risk_per_share = close - stop if stop < close else atr
    target = round(close + risk_per_share * MIN_RISK_REWARD, 2)

    return {
        "entry": close,
        "stop_loss": round(stop, 2),
        "target_1_2R": target,
        "risk_per_share": round(risk_per_share, 2),
        "min_risk_reward": MIN_RISK_REWARD,
        "framework": "Van Tharp — position sizing / R-multiples",
    }


def pre_trade_checklist(
    *,
    stage: dict,
    murphy: dict,
    wyckoff: dict,
    rsi_info: dict,
    adx: Optional[float],
    patterns: dict,
    has_sr: bool,
    risk: dict,
) -> dict[str, Any]:
    """Phase 10 non-negotiable checklist (programmatic)."""
    items = [
        {
            "id": "trend_weekly_daily",
            "label": "Trend confirmed on daily (weekly proxy via 200 EMA)",
            "passed": murphy.get("daily_trend") in ("UPTREND", "DOWNTREND"),
        },
        {
            "id": "stage_2_long",
            "label": "Stage 2 for longs (Weinstein)",
            "passed": stage.get("stage") == STAGE_ADVANCING,
        },
        {
            "id": "support_zone",
            "label": "Near support / structure zone",
            "passed": has_sr,
        },
        {
            "id": "volume_confirms",
            "label": "Volume confirms (Wyckoff)",
            "passed": wyckoff.get("signal") in ("BULLISH_CONFIRM", "HEALTHY_PULLBACK"),
        },
        {
            "id": "indicators_aligned",
            "label": "≥2 indicators aligned",
            "passed": (
                murphy.get("alignment_score", 0) >= 2
                and rsi_info.get("action_hint") in ("NEUTRAL", "CONTINUATION", "REVERSAL_WATCH")
            ),
        },
        {
            "id": "pattern_present",
            "label": "Chart/candle pattern present",
            "passed": bool(patterns.get("active_patterns")),
        },
        {
            "id": "stop_defined",
            "label": "Stop loss level defined",
            "passed": risk.get("stop_loss") is not None,
        },
        {
            "id": "risk_reward",
            "label": f"Risk:reward ≥ 1:{MIN_RISK_REWARD:.0f}",
            "passed": risk.get("target_1_2R") is not None,
        },
        {
            "id": "adx_trend",
            "label": f"ADX ≥ {ADX_WEAK_TREND} (trend exists)",
            "passed": adx is not None and adx >= ADX_WEAK_TREND,
        },
        {
            "id": "rsi_not_euphoric_entry",
            "label": "RSI not euphoric for new long (40–60 ideal pullback)",
            "passed": rsi_info.get("zone") in ("NEUTRAL", "MID", "OVERSOLD"),
        },
    ]
    passed = sum(1 for i in items if i["passed"])
    return {
        "items": items,
        "passed_count": passed,
        "total": len(items),
        "trade_allowed": passed >= _CHECKLIST_MIN_PASS,
        "framework": "Pre-trade checklist — playbook Phase 10",
    }


def technical_playbook_signal(
    stage: dict,
    murphy: dict,
    wyckoff: dict,
    rsi_info: dict,
    checklist: dict,
    graham_mr: Optional[dict] = None,
) -> str:
    """Composite TA signal from playbook layers."""
    if stage.get("stage") == STAGE_DECLINING:
        return "STRONG_SELL"
    if stage.get("stage") == STAGE_DISTRIBUTION:
        return "SELL"
    if stage.get("stage") != STAGE_ADVANCING:
        return "NEUTRAL"

    sig = "NEUTRAL"
    if murphy.get("daily_trend") == "UPTREND" and wyckoff.get("signal") == "BULLISH_CONFIRM":
        sig = "BUY"
    if murphy.get("golden_cross") and checklist.get("passed_count", 0) >= _CHECKLIST_MIN_PASS:
        sig = "STRONG_BUY"
    if wyckoff.get("signal") == "WEAK_RALLY":
        sig = "NEUTRAL"
    if rsi_info.get("zone") == "OVERBOUGHT" and rsi_info.get("action_hint") == "CAUTION_SELL":
        sig = "SELL"

    if graham_mr:
        g_sig = graham_mr.get("signal")
        if g_sig in ("STRONG_BUY", "BUY") and sig in ("NEUTRAL", "BUY"):
            sig = g_sig
        elif g_sig in ("STRONG_SELL", "SELL"):
            sig = g_sig

    return sig


def compute_technical_playbook(symbol: str) -> dict[str, Any]:
    """Full technical playbook for one symbol."""
    sym = normalize_nse_symbol(symbol)
    df = _load_ohlcv(sym)
    daily = _load_tech_row(sym, "1d")
    hourly = _load_tech_row(sym, "1h")

    if not df.empty:
        daily = {**daily, "close": float(df["close"].iloc[-1])}

    ema20, ema50, ema200 = daily.get("ema20"), daily.get("ema50"), daily.get("ema200")
    ema_stack_bull = bool(
        ema20 and ema50 and ema200 and ema20 > ema50 > ema200
    )

    stage = weinstein_stage(df, ema50, ema200)
    murphy = murphy_trend_alignment(daily, hourly, ema_stack_bull)
    wyckoff = wyckoff_volume_signal(df) if not df.empty else {"signal": "UNKNOWN"}
    adx = compute_adx(df) if not df.empty else None

    trend = murphy.get("daily_trend", "SIDEWAYS")
    rsi_info = rsi_interpretation(daily.get("rsi"), trend)
    bb = bollinger_state(
        daily.get("close"),
        daily.get("bb_upper"),
        daily.get("bb_lower"),
        df,
    )
    patterns = pattern_signals(daily.get("patterns_json") or {})
    sr = daily.get("sr_zones_json") or {}
    supports = sr.get("support") or []
    risk = van_tharp_risk_hint(daily.get("close"), daily.get("atr"), supports)

    checklist = pre_trade_checklist(
        stage=stage,
        murphy=murphy,
        wyckoff=wyckoff,
        rsi_info=rsi_info,
        adx=adx,
        patterns=patterns,
        has_sr=bool(supports),
        risk=risk,
    )

    graham_mr = None
    try:
        from app.services.intelligent_investor import graham_mr_market_technical

        graham_mr = graham_mr_market_technical(
            sym,
            rsi=daily.get("rsi"),
            ema200=ema200,
        )
    except Exception as exc:
        logger.debug("Graham MR overlay: %s", exc)

    signal = technical_playbook_signal(
        stage, murphy, wyckoff, rsi_info, checklist, graham_mr
    )

    adx_note = "choppy" if adx is not None and adx < ADX_WEAK_TREND else (
        "strong trend" if adx and adx >= ADX_STRONG_TREND else "developing"
    )

    return {
        "symbol": sym,
        "murphy_principles": MURPHY_PRINCIPLES,
        "weinstein_stage": stage,
        "murphy_alignment": murphy,
        "wyckoff_volume": wyckoff,
        "adx": {"value": adx, "regime": adx_note},
        "rsi": rsi_info,
        "bollinger": bb,
        "patterns": patterns,
        "support_resistance": sr,
        "van_tharp_risk": risk,
        "pre_trade_checklist": checklist,
        "graham_mr_market": graham_mr,
        "playbook_signal": signal,
        "playbook_trend": trend,
        "framework_sources": [
            "Murphy", "Weinstein", "Wyckoff", "O'Neil", "Bulkowski", "Van Tharp", "Graham",
        ],
    }
