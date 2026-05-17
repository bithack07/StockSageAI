"""
ML feature vectors from Stock Analysis Playbook (technical + fundamental).

Used by ml_training/train_all.py and app/pipelines/ml_inference.py so book concepts
(Murphy, Weinstein, Wyckoff, Lynch, Greenblatt, Dorsey, Graham) influence model weights.

Technical columns are computed per bar from OHLCV (valid for historical training).
Fundamental columns use latest yfinance snapshot per symbol (replicated across rows).
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import numpy as np
import pandas as pd

from app.services.intelligent_investor import GRAHAM_ML_FEATURE_NAMES, graham_ml_features
from app.services.technical_playbook import (
    ADX_STRONG_TREND,
    ADX_WEAK_TREND,
    STAGE_ADVANCING,
    STAGE_DECLINING,
    compute_adx,
    murphy_trend_alignment,
    rsi_interpretation,
    weinstein_stage,
    wyckoff_volume_signal,
)

logger = logging.getLogger(__name__)

# ── Feature names (order matters — must match train_all & ml_inference) ───────

TECHNICAL_PLAYBOOK_ML_FEATURES = [
    "weinstein_stage_norm",
    "adx_norm",
    "murphy_align_norm",
    "wyckoff_norm",
    "golden_cross",
    "death_cross",
    "ema_stack_bull",
    "price_vs_ema200_norm",
    "rsi_action_norm",
    "checklist_pass_norm",
]

FUNDAMENTAL_PLAYBOOK_ML_FEATURES = [
    "lynch_peg_norm",
    "greenblatt_combined_norm",
    "fa_score_norm",
    "moat_score_norm",
    "fundamental_bias_norm",
]

PLAYBOOK_ML_FEATURE_NAMES = (
    TECHNICAL_PLAYBOOK_ML_FEATURES + FUNDAMENTAL_PLAYBOOK_ML_FEATURES
)

# Full XGBoost feature list (base + graham + playbook)
ML_BASE_FEATURES = [
    "rsi", "macd", "bb_upper", "bb_lower", "atr",
    "ema20", "ema50", "ema200", "composite_score",
    "pe_ratio", "roce", "debt_equity",
]

ML_FULL_FEATURE_NAMES = ML_BASE_FEATURES + GRAHAM_ML_FEATURE_NAMES + PLAYBOOK_ML_FEATURE_NAMES

# LSTM: base price features + playbook technical (per timestep)
LSTM_BASE_FEATURES = ["close_norm", "volume_norm", "rsi_norm", "macd_norm", "bb_pos"]
LSTM_PLAYBOOK_FEATURES = [
    "weinstein_stage_norm",
    "adx_norm",
    "murphy_align_norm",
    "wyckoff_norm",
    "graham_mos_row_norm",
]
LSTM_FEATURE_COLS = LSTM_BASE_FEATURES + LSTM_PLAYBOOK_FEATURES

_LYNCH_CATEGORY_MAP = {
    "slow_grower": 0.1,
    "stalwart": 0.35,
    "fast_grower": 0.85,
    "cyclical": 0.5,
    "turnaround": 0.2,
    "asset_play": 0.6,
}


def _clip(v: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return round(float(max(lo, min(hi, v))), 4)


def _encode_wyckoff(signal: str) -> float:
    return {
        "BULLISH_CONFIRM": 1.0,
        "HEALTHY_PULLBACK": 0.4,
        "WEAK_RALLY": -0.3,
        "DISTRIBUTION_OR_CAPITULATION": -0.8,
        "UNKNOWN": 0.0,
    }.get(signal, 0.0)


def _encode_rsi_action(hint: str) -> float:
    return {
        "CONTINUATION": 0.6,
        "NEUTRAL": 0.0,
        "REVERSAL_WATCH": 0.5,
        "CAUTION_BUY": 0.3,
        "CAUTION_SELL": -0.5,
    }.get(hint, 0.0)


def fundamental_playbook_ml_snapshot(symbol: str, fund: Optional[dict] = None) -> dict[str, float]:
    """Fundamental playbook features (constant per symbol for training rows)."""
    try:
        from app.services.fundamental_playbook import compute_fundamental_playbook

        pb = compute_fundamental_playbook(symbol)
    except Exception as exc:
        logger.debug("fundamental playbook ML snapshot failed %s: %s", symbol, exc)
        return {k: 0.0 for k in FUNDAMENTAL_PLAYBOOK_ML_FEATURES}

    peg = (pb.get("lynch") or {}).get("peg") or {}
    peg_val = peg.get("peg_ratio")
    peg_norm = 0.0
    if peg_val is not None and peg_val > 0:
        peg_norm = _clip(1.0 - peg_val, -1, 1)  # PEG<1 → positive

    gb = pb.get("greenblatt") or {}
    gb_combined = (gb.get("combined_score") or 5) / 10.0

    fa_total = (pb.get("fa_score") or {}).get("total") or 25
    fa_norm = _clip(fa_total / 50.0, 0, 1)

    moat_s = (pb.get("moat") or {}).get("durability_score_1_5") or 3
    moat_norm = _clip(moat_s / 5.0, 0, 1)

    verdict = pb.get("playbook_verdict", "FAIRLY_VALUED")
    bias = {"UNDERVALUED": 0.7, "FAIRLY_VALUED": 0.0, "OVERVALUED": -0.7}.get(verdict, 0.0)

    return {
        "lynch_peg_norm": peg_norm,
        "greenblatt_combined_norm": _clip(gb_combined, 0, 1),
        "fa_score_norm": fa_norm,
        "moat_score_norm": moat_norm,
        "fundamental_bias_norm": bias,
    }


def technical_playbook_row(
    df: pd.DataFrame,
    idx: int,
    *,
    rsi: Optional[float] = None,
    ema20: Optional[float] = None,
    ema50: Optional[float] = None,
    ema200: Optional[float] = None,
) -> dict[str, float]:
    """Playbook technical features at one index (uses history df.iloc[:idx+1])."""
    if idx < 0 or idx >= len(df):
        return {k: 0.0 for k in TECHNICAL_PLAYBOOK_ML_FEATURES}

    hist = df.iloc[: idx + 1].copy()
    if "close" not in hist.columns:
        return {k: 0.0 for k in TECHNICAL_PLAYBOOK_ML_FEATURES}

    close = float(hist["close"].iloc[-1])
    rsi_v = rsi
    if rsi_v is None and "rsi" in hist.columns:
        rsi_v = hist["rsi"].iloc[-1]
    e20 = ema20 if ema20 is not None else (hist["ema20"].iloc[-1] if "ema20" in hist.columns else None)
    e50 = ema50 if ema50 is not None else (hist["ema50"].iloc[-1] if "ema50" in hist.columns else None)
    e200 = ema200 if ema200 is not None else (hist["ema200"].iloc[-1] if "ema200" in hist.columns else None)

    stage = weinstein_stage(hist, e50, e200)
    stage_norm = (stage.get("stage") or 1) / 4.0

    adx = compute_adx(hist)
    adx_norm = _clip((adx or 15) / 50.0, 0, 1)

    daily = {"ema20": e20, "ema50": e50, "ema200": e200, "close": close}
    murphy = murphy_trend_alignment(daily, {}, bool(e20 and e50 and e200 and e20 > e50 > e200))
    murphy_norm = _clip((murphy.get("alignment_score") or 0) / 5.0, 0, 1)

    wyckoff = wyckoff_volume_signal(hist.tail(2)) if len(hist) >= 2 else {"signal": "UNKNOWN"}
    wyckoff_norm = _encode_wyckoff(wyckoff.get("signal", "UNKNOWN"))

    golden = 1.0 if murphy.get("golden_cross") else 0.0
    death = 1.0 if murphy.get("death_cross") else 0.0
    stack_bull = 1.0 if (e20 and e50 and e200 and e20 > e50 > e200) else 0.0

    price_vs_200 = 0.0
    if e200 and e200 > 0:
        price_vs_200 = _clip((close / e200 - 1) * 2, -1, 1)

    trend = murphy.get("daily_trend", "SIDEWAYS")
    rsi_info = rsi_interpretation(
        float(rsi_v) if rsi_v is not None and rsi_v == rsi_v else None,
        trend,
    )
    rsi_action = _encode_rsi_action(rsi_info.get("action_hint", "NEUTRAL"))

    # Checklist proxy (5 quick checks)
    checks = [
        stage.get("stage") == STAGE_ADVANCING,
        trend == "UPTREND",
        wyckoff.get("signal") in ("BULLISH_CONFIRM", "HEALTHY_PULLBACK"),
        adx is not None and adx >= ADX_WEAK_TREND,
        rsi_info.get("zone") in ("NEUTRAL", "MID", "OVERSOLD"),
    ]
    checklist_norm = sum(checks) / len(checks)

    return {
        "weinstein_stage_norm": round(stage_norm, 4),
        "adx_norm": adx_norm,
        "murphy_align_norm": murphy_norm,
        "wyckoff_norm": wyckoff_norm,
        "golden_cross": golden,
        "death_cross": death,
        "ema_stack_bull": stack_bull,
        "price_vs_ema200_norm": price_vs_200,
        "rsi_action_norm": rsi_action,
        "checklist_pass_norm": round(checklist_norm, 4),
    }


def graham_mos_row_norm(df: pd.DataFrame, idx: int) -> float:
    """Rolling proxy for margin of safety: discount to 200 EMA (training)."""
    if idx < 200 or "ema200" not in df.columns:
        return 0.0
    close = float(df["close"].iloc[idx])
    e200 = float(df["ema200"].iloc[idx])
    if e200 <= 0:
        return 0.0
    # Below 200 EMA → positive MOS proxy
    return _clip((1 - close / e200) * 1.5, -1, 1)


def _vectorized_technical_playbook(df: pd.DataFrame) -> pd.DataFrame:
    """Fast technical playbook columns for training (vectorized)."""
    out = df.copy()
    close = out["close"]
    ema50 = out["ema50"] if "ema50" in out.columns else close.ewm(span=50, adjust=False).mean()
    ema200 = out["ema200"] if "ema200" in out.columns else close.ewm(span=200, adjust=False).mean()
    ema20 = out["ema20"] if "ema20" in out.columns else close.ewm(span=20, adjust=False).mean()

    slope = ema50 - ema50.shift(25)
    vol_r = out["volume"].rolling(20).mean() / (out["volume"].shift(20).rolling(40).mean() + 1e-8)

    stage = np.where(
        (close > ema200) & (slope > 0) & (close > ema50),
        STAGE_ADVANCING / 4.0,
        np.where(
            (close < ema200) & (slope < 0),
            STAGE_DECLINING / 4.0,
            np.where((close > ema200) & (vol_r > 1.1), 3 / 4.0, 1 / 4.0),
        ),
    )
    out["weinstein_stage_norm"] = stage

    # ADX proxy: 20d trend strength (faster than per-row Wilder ADX)
    trend_strength = close.pct_change(20).abs().rolling(5).mean() * 500
    out["adx_norm"] = trend_strength.clip(0, 50) / 50.0

    stack = (ema20 > ema50) & (ema50 > ema200)
    out["ema_stack_bull"] = stack.astype(float)
    out["golden_cross"] = (ema50 > ema200).astype(float)
    out["death_cross"] = (ema50 < ema200).astype(float)
    out["price_vs_ema200_norm"] = ((close / ema200 - 1) * 2).clip(-1, 1)

    uptrend = stack
    out["murphy_align_norm"] = uptrend.astype(float) * 0.8

    ret = close.pct_change()
    vol_chg = out["volume"].pct_change()
    wy = np.where(
        (ret > 0) & (vol_chg > 0), 1.0,
        np.where((ret > 0) & (vol_chg <= 0), -0.3,
                 np.where((ret <= 0) & (vol_chg > 0), -0.8, 0.4)),
    )
    out["wyckoff_norm"] = wy

    rsi = out["rsi"] if "rsi" in out.columns else pd.Series(50.0, index=out.index)
    out["rsi_action_norm"] = np.where(
        (rsi > 70) & uptrend, 0.6,
        np.where(rsi < 30, 0.5, 0.0),
    )
    checklist = (
        (out["weinstein_stage_norm"] >= STAGE_ADVANCING / 4.0 - 0.01)
        & uptrend
        & (out["wyckoff_norm"] >= 0)
        & (out["adx_norm"] >= ADX_WEAK_TREND / 50.0)
    )
    out["checklist_pass_norm"] = checklist.astype(float) * 0.7 + 0.15
    out["graham_mos_row_norm"] = ((1 - close / ema200) * 1.5).clip(-1, 1)
    return out


def enrich_training_frame(df: pd.DataFrame, symbol: str, fund: dict) -> pd.DataFrame:
    """
    Add all playbook ML columns to a per-symbol training frame.
    Call after base indicators (rsi, ema*, etc.) exist on df.
    """
    out = _vectorized_technical_playbook(df)
    fund_snap = fundamental_playbook_ml_snapshot(symbol)
    for k, v in fund_snap.items():
        out[k] = v
    return out


def playbook_ml_features_for_symbol(symbol: str) -> dict[str, float]:
    """Latest feature dict for inference (technical from DB/yfinance + fundamental snapshot)."""
    import yfinance as yf

    from app.services.india_market import normalize_nse_symbol

    sym = normalize_nse_symbol(symbol)
    feats: dict[str, float] = {}

    try:
        feats.update(graham_ml_features(sym))
    except Exception:
        for k in GRAHAM_ML_FEATURE_NAMES:
            feats[k] = 0.0

    feats.update(fundamental_playbook_ml_snapshot(sym))

    try:
        hist = yf.Ticker(sym).history(period="2y", interval="1d")
        if not hist.empty:
            pdf = hist.reset_index()
            pdf.columns = [c.lower() for c in pdf.columns]
            pdf = pdf.rename(columns={"datetime": "date"} if "datetime" in pdf.columns else {})
            from ta.trend import EMAIndicator

            close = pdf["close"]
            pdf["ema20"] = EMAIndicator(close=close, window=20).ema_indicator()
            pdf["ema50"] = EMAIndicator(close=close, window=50).ema_indicator()
            pdf["ema200"] = EMAIndicator(close=close, window=200).ema_indicator()
            from ta.momentum import RSIIndicator

            pdf["rsi"] = RSIIndicator(close=close, window=14).rsi()
            idx = len(pdf) - 1
            feats.update(technical_playbook_row(pdf, idx))
            feats["graham_mos_row_norm"] = graham_mos_row_norm(pdf, idx)
    except Exception as exc:
        logger.warning("playbook technical snapshot failed %s: %s", sym, exc)
        for k in TECHNICAL_PLAYBOOK_ML_FEATURES:
            feats.setdefault(k, 0.0)
        feats.setdefault("graham_mos_row_norm", feats.get("graham_mos_norm", 0.0))

    return feats


def playbook_direction_prior(symbol: str) -> dict[str, Any]:
    """
    7-day direction prior blending Graham + full playbook (for ML overlay).
    """
    from app.services.intelligent_investor import graham_direction_prior

    graham = graham_direction_prior(symbol)
    try:
        from app.services.fundamental_playbook import compute_fundamental_playbook
        from app.services.technical_playbook import compute_technical_playbook

        fund = compute_fundamental_playbook(symbol)
        tech = compute_technical_playbook(symbol)
    except Exception:
        return graham

    bull = graham["bullish_prob"]
    bear = graham["bearish_prob"]

    fa = (fund.get("fa_score") or {}).get("total") or 25
    if fa >= 35:
        bull += 0.08
    elif fa < 25:
        bear += 0.08

    fv = fund.get("playbook_verdict")
    if fv == "UNDERVALUED":
        bull += 0.1
    elif fv == "OVERVALUED":
        bear += 0.1

    stage = (tech.get("weinstein_stage") or {}).get("stage")
    if stage == STAGE_ADVANCING:
        bull += 0.12
    elif stage == STAGE_DECLINING:
        bear += 0.12

    sig = tech.get("playbook_signal", "NEUTRAL")
    if sig in ("STRONG_BUY", "BUY"):
        bull += 0.1
    elif sig in ("STRONG_SELL", "SELL"):
        bear += 0.1

    if (tech.get("pre_trade_checklist") or {}).get("trade_allowed"):
        bull += 0.05

    neut = max(0.05, 1.0 - bull - bear)
    total = bull + bear + neut
    return {
        "bullish_prob": round(bull / total, 3),
        "bearish_prob": round(bear / total, 3),
        "neutral_prob": round(neut / total, 3),
        "graham_verdict": graham.get("graham_verdict"),
        "playbook_fundamental_verdict": fv,
        "weinstein_stage": stage,
        "playbook_technical_signal": sig,
        "source": "playbook_prior",
    }
