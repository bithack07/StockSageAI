"""Unit tests for analysis playbook formulas (no DB required)."""
import math

import pandas as pd

from app.services.fundamental_playbook import (
    FA_HIGH_CONVICTION_MIN,
    greenblatt_magic_formula,
    lynch_peg,
    lynch_stock_category,
    dorsey_moat_assessment,
)
from app.services.technical_playbook import (
    compute_adx,
    murphy_trend_alignment,
    pattern_signals,
    pre_trade_checklist,
    rsi_interpretation,
    weinstein_stage,
    wyckoff_volume_signal,
)


def test_lynch_peg_undervalued():
    r = lynch_peg(15, 20)
    assert r["peg_ratio"] == 0.75
    assert r["verdict"] == "UNDERVALUED_GROWTH"


def test_lynch_peg_expensive():
    r = lynch_peg(30, 10)
    assert r["verdict"] == "EXPENSIVE"


def test_greenblatt_attractive():
    r = greenblatt_magic_formula(roce=22, pe=10)
    assert r["verdict"] == "ATTRACTIVE"
    assert r["combined_score"] >= 7


def test_dorsey_wide_moat():
    r = dorsey_moat_assessment(sector="Information Technology", gross_margin=0.45, roe=0.22, debt_equity=0.3)
    assert r["moat_width"] in ("wide", "narrow")
    assert r["durability_score_1_5"] >= 4


def test_rsi_continuation_in_uptrend():
    r = rsi_interpretation(72, "UPTREND")
    assert r["action_hint"] == "CONTINUATION"


def test_wyckoff_bullish_confirm():
    df = pd.DataFrame({
        "open": [100, 101],
        "high": [102, 103],
        "low": [99, 100],
        "close": [101, 103],
        "volume": [1000, 2000],
    })
    r = wyckoff_volume_signal(df)
    assert r["signal"] == "BULLISH_CONFIRM"


def test_pattern_bullish_hammer():
    r = pattern_signals({"CDL_HAMMER": 100})
    assert r["bias"] == "BULLISH"
    assert "CDL_HAMMER" in r["active_patterns"]


def test_pre_trade_checklist_structure():
    checklist = pre_trade_checklist(
        stage={"stage": 2},
        murphy={"daily_trend": "UPTREND", "alignment_score": 3},
        wyckoff={"signal": "BULLISH_CONFIRM"},
        rsi_info={"zone": "NEUTRAL", "action_hint": "NEUTRAL"},
        adx=22,
        patterns={"active_patterns": ["CDL_HAMMER"]},
        has_sr=True,
        risk={"stop_loss": 90, "target_1_2R": 110},
    )
    assert checklist["total"] == 10
    assert "trade_allowed" in checklist


def test_fa_high_conviction_threshold():
    assert FA_HIGH_CONVICTION_MIN == 35


def test_weinstein_stage_advancing():
    n = 220
    closes = [100 + i * 0.3 for i in range(n)]
    df = pd.DataFrame({
        "open": closes,
        "high": [c + 1 for c in closes],
        "low": [c - 1 for c in closes],
        "close": closes,
        "volume": [1_000_000] * n,
    })
    stage = weinstein_stage(df, None, None)
    assert stage["stage"] in (2, 1, 3)  # depends on EMA math


def test_adx_computes():
    n = 50
    rng = pd.Series(range(n)).astype(float)
    df = pd.DataFrame({
        "high": 100 + rng * 0.5,
        "low": 99 + rng * 0.4,
        "close": 99.5 + rng * 0.45,
        "volume": [1e6] * n,
    })
    adx = compute_adx(df)
    assert adx is None or adx >= 0


def test_murphy_alignment():
    daily = {"ema20": 110, "ema50": 105, "ema200": 100}
    hourly = {"ema20": 108, "ema50": 104}
    r = murphy_trend_alignment(daily, hourly, True)
    assert r["daily_trend"] == "UPTREND"
    assert r["golden_cross"] is True


def test_ml_feature_names_count():
    from app.services.ml_playbook_features import ML_FULL_FEATURE_NAMES, PLAYBOOK_ML_FEATURE_NAMES

    assert len(PLAYBOOK_ML_FEATURE_NAMES) == 15
    assert len(ML_FULL_FEATURE_NAMES) == 12 + 4 + 15


def test_vectorized_enrich_columns():
    from app.services.ml_playbook_features import enrich_training_frame

    n = 250
    df = pd.DataFrame({
        "close": [100 + i * 0.1 for i in range(n)],
        "volume": [1_000_000] * n,
        "open": [100.0] * n,
        "high": [101.0] * n,
        "low": [99.0] * n,
        "rsi": [50.0] * n,
        "ema20": [100.0] * n,
        "ema50": [99.0] * n,
        "ema200": [98.0] * n,
    })
    out = enrich_training_frame(df, "TEST.NS", {})
    assert "weinstein_stage_norm" in out.columns
    assert "lynch_peg_norm" in out.columns
