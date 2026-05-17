"""Pipeline 2 — Technical Feature Computation (ta library + TA-Lib)."""
import json
import logging

import numpy as np
import pandas as pd
import ta as ta_lib
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, EMAIndicator
from ta.volatility import BollingerBands, AverageTrueRange

try:
    import talib
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False
    logging.warning("TA-Lib not installed; candlestick patterns disabled.")

from celery import shared_task

from app.db import get_db

logger = logging.getLogger(__name__)


def _compute_sr_zones(df: pd.DataFrame, n_levels: int = 3) -> dict:
    """Volume-profile based support / resistance zones."""
    if df.empty or len(df) < 20:
        return {"support": [], "resistance": []}

    price_range = df["close"].max() - df["close"].min()
    bins = 20
    bin_size = price_range / bins
    current_price = df["close"].iloc[-1]

    vol_profile: dict[float, float] = {}
    for _, row in df.iterrows():
        mid = round((row["high"] + row["low"]) / 2 / bin_size) * bin_size
        vol_profile[mid] = vol_profile.get(mid, 0) + float(row["volume"])

    sorted_levels = sorted(vol_profile.items(), key=lambda x: x[1], reverse=True)
    support = sorted(
        [lvl for lvl, _ in sorted_levels if lvl < current_price][:n_levels]
    )
    resistance = sorted(
        [lvl for lvl, _ in sorted_levels if lvl >= current_price][:n_levels]
    )
    return {"support": support, "resistance": resistance}


def _compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    df["RSI_14"] = RSIIndicator(close=close, window=14).rsi()

    macd_ind = MACD(close=close)
    df["MACD_12_26_9"] = macd_ind.macd()
    df["MACDs_12_26_9"] = macd_ind.macd_signal()

    bb = BollingerBands(close=close, window=20, window_dev=2)
    df["BBU_20_2.0"] = bb.bollinger_hband()
    df["BBL_20_2.0"] = bb.bollinger_lband()
    df["BBP_20_2.0"] = bb.bollinger_pband()

    df["ATRr_14"] = AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range()
    df["EMA_20"] = EMAIndicator(close=close, window=20).ema_indicator()
    df["EMA_50"] = EMAIndicator(close=close, window=50).ema_indicator()
    df["EMA_200"] = EMAIndicator(close=close, window=200).ema_indicator()

    stoch = StochasticOscillator(high=high, low=low, close=close, window=14, smooth_window=3)
    df["STOCHk_14_3_3"] = stoch.stoch()
    df["STOCHd_14_3_3"] = stoch.stoch_signal()

    # Simple VWAP (daily reset approximation)
    try:
        typical_price = (high + low + close) / 3
        df["VWAP_D"] = (typical_price * volume).cumsum() / volume.cumsum()
    except Exception:
        pass

    return df


def _compute_candlestick_patterns(df: pd.DataFrame) -> dict:
    if not HAS_TALIB or len(df) < 5:
        return {}
    o = df["open"].values.astype(float)
    h = df["high"].values.astype(float)
    l = df["low"].values.astype(float)
    c = df["close"].values.astype(float)
    patterns = {
        "CDL_ENGULFING": int(talib.CDLENGULFING(o, h, l, c)[-1]),
        "CDL_HAMMER": int(talib.CDLHAMMER(o, h, l, c)[-1]),
        "CDL_DOJI": int(talib.CDLDOJI(o, h, l, c)[-1]),
        "CDL_MORNINGSTAR": int(talib.CDLMORNINGSTAR(o, h, l, c)[-1]),
        "CDL_SHOOTINGSTAR": int(talib.CDLSHOOTINGSTAR(o, h, l, c)[-1]),
        "CDL_HARAMI": int(talib.CDLHARAMI(o, h, l, c)[-1]),
        "CDL_MARUBOZU": int(talib.CDLMARUBOZU(o, h, l, c)[-1]),
        "CDL_THREEWHITESOLDIERS": int(talib.CDL3WHITESOLDIERS(o, h, l, c)[-1]),
        "CDL_DARKCLOUDCOVER": int(talib.CDLDARKCLOUDCOVER(o, h, l, c)[-1]),
    }
    return {k: v for k, v in patterns.items() if v != 0}


@shared_task(name="pipelines.technical_features.compute_technical_features", bind=True, max_retries=3)
def compute_technical_features(self, symbol: str, timeframe: str = "1d"):
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT date, open, high, low, close, volume FROM ohlcv WHERE symbol=%s ORDER BY date",
                (symbol,),
            )
            rows = cur.fetchall()

        if not rows:
            logger.warning(f"No OHLCV data for {symbol}; skipping technical features")
            return

        df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
        df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(float)
        df["volume"] = df["volume"].astype(float)
        df.set_index("date", inplace=True)

        df = _compute_indicators(df)
        patterns = _compute_candlestick_patterns(df.reset_index())
        sr_zones = _compute_sr_zones(df.reset_index())

        latest = df.iloc[-1]
        latest_date = df.index[-1]

        def _safe(val):
            if val is None or (isinstance(val, float) and np.isnan(val)):
                return None
            return round(float(val), 4)

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO technical_features
                   (symbol, date, timeframe, rsi, macd, macd_signal,
                    bb_upper, bb_lower, atr, ema20, ema50, ema200,
                    stoch_k, stoch_d, vwap, patterns_json, sr_zones_json)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (symbol, date, timeframe) DO UPDATE
                   SET rsi=EXCLUDED.rsi, macd=EXCLUDED.macd, macd_signal=EXCLUDED.macd_signal,
                       bb_upper=EXCLUDED.bb_upper, bb_lower=EXCLUDED.bb_lower, atr=EXCLUDED.atr,
                       ema20=EXCLUDED.ema20, ema50=EXCLUDED.ema50, ema200=EXCLUDED.ema200,
                       stoch_k=EXCLUDED.stoch_k, stoch_d=EXCLUDED.stoch_d,
                       vwap=EXCLUDED.vwap, patterns_json=EXCLUDED.patterns_json,
                       sr_zones_json=EXCLUDED.sr_zones_json""",
                (
                    symbol, latest_date, timeframe,
                    _safe(latest.get("RSI_14")),
                    _safe(latest.get("MACD_12_26_9")),
                    _safe(latest.get("MACDs_12_26_9")),
                    _safe(latest.get("BBU_20_2.0")),
                    _safe(latest.get("BBL_20_2.0")),
                    _safe(latest.get("ATRr_14")),
                    _safe(latest.get("EMA_20")),
                    _safe(latest.get("EMA_50")),
                    _safe(latest.get("EMA_200")),
                    _safe(latest.get("STOCHk_14_3_3")),
                    _safe(latest.get("STOCHd_14_3_3")),
                    _safe(latest.get("VWAP_D")),
                    json.dumps(patterns),
                    json.dumps(sr_zones),
                ),
            )

        logger.info(f"Technical features computed for {symbol}")
        return {"symbol": symbol, "date": str(latest_date)}

    except Exception as exc:
        logger.error(f"compute_technical_features failed for {symbol}: {exc}")
        raise self.retry(exc=exc, countdown=60)
