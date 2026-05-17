"""Pipeline 5 — ML Inference (direction model + Prophet + LSTM + playbook overlay)."""
import logging
import os

import numpy as np

from app.db import get_db
from app.pipelines.lstm_inference import get_lstm_scores
from app.services.intelligent_investor import GRAHAM_ML_FEATURE_NAMES, graham_ml_features
from app.services.ml_labels import direction_from_xgb_class
from app.services.ml_playbook_features import (
    ML_BASE_FEATURES,
    ML_FULL_FEATURE_NAMES,
    PLAYBOOK_ML_FEATURE_NAMES,
    playbook_direction_prior,
    playbook_ml_features_for_symbol,
)

logger = logging.getLogger(__name__)

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")

_xgb_model = None
_prophet_models: dict = {}

# Legacy models (pre-playbook retrain)
FEATURES_LEGACY = list(ML_BASE_FEATURES)
FEATURES_WITH_GRAHAM = FEATURES_LEGACY + GRAHAM_ML_FEATURE_NAMES
FEATURES = list(ML_FULL_FEATURE_NAMES)


def _load_xgb():
    global _xgb_model
    if _xgb_model is None:
        path = os.path.join(MODELS_DIR, "xgb_model.joblib")
        if os.path.exists(path):
            import joblib
            _xgb_model = joblib.load(path)
            logger.info("XGBoost model loaded")
        else:
            logger.warning("xgb_model.joblib not found — using playbook + LSTM fallback")
    return _xgb_model


def _load_prophet(symbol: str):
    if symbol not in _prophet_models:
        path = os.path.join(MODELS_DIR, "prophet_models", f"{symbol}.pkl")
        if os.path.exists(path):
            import joblib
            _prophet_models[symbol] = joblib.load(path)
    return _prophet_models.get(symbol)


def _blend_probs(base: dict, prior: dict, weight: float = 0.35) -> dict:
    """Blend model probs with playbook prior (Graham + Weinstein + Lynch + …)."""
    w = weight
    bull = (1 - w) * base.get("bullish_prob", 0.33) + w * prior.get("bullish_prob", 0.33)
    bear = (1 - w) * base.get("bearish_prob", 0.33) + w * prior.get("bearish_prob", 0.33)
    neut = max(0.0, 1.0 - bull - bear)
    return {
        "bullish_prob": round(bull, 3),
        "bearish_prob": round(bear, 3),
        "neutral_prob": round(neut, 3),
        "source": f"{base.get('source', 'model')}+playbook",
        "playbook_prior": prior,
    }


def _feature_names_for_model(xgb) -> list[str]:
    n = getattr(xgb, "n_features_in_", len(FEATURES_LEGACY))
    if n == len(FEATURES):
        return FEATURES
    if n == len(FEATURES_WITH_GRAHAM):
        return FEATURES_WITH_GRAHAM
    return FEATURES_LEGACY


def _build_feature_vector(row: tuple, symbol: str) -> np.ndarray:
    base = [float(v) if v is not None else 0.0 for v in row]
    xgb = _load_xgb()
    names = _feature_names_for_model(xgb) if xgb is not None else FEATURES

    if len(names) == len(FEATURES_LEGACY):
        return np.array([base], dtype=np.float32)

    try:
        pb = playbook_ml_features_for_symbol(symbol)
    except Exception as exc:
        logger.warning("playbook features fallback for %s: %s", symbol, exc)
        pb = {}

    extra = []
    for name in names[len(FEATURES_LEGACY):]:
        extra.append(float(pb.get(name, 0.0)))

    return np.array([base + extra], dtype=np.float32)


def get_ml_scores(symbol: str) -> dict:
    """Return direction-model probs, LSTM 7-day outlook, Prophet, and playbook overlay."""
    try:
        playbook_prior = playbook_direction_prior(symbol)
        playbook_feats = playbook_ml_features_for_symbol(symbol)

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT tf.rsi, tf.macd, tf.bb_upper, tf.bb_lower, tf.atr,
                          tf.ema20, tf.ema50, tf.ema200,
                          s.composite_score, f.pe_ratio, f.roce, f.debt_equity
                   FROM technical_features tf
                   LEFT JOIN sentiment s ON s.symbol = tf.symbol AND s.date = tf.date
                   LEFT JOIN fundamentals f ON f.symbol = tf.symbol
                   WHERE tf.symbol = %s AND tf.timeframe = '1d'
                   ORDER BY tf.date DESC LIMIT 1""",
                (symbol,),
            )
            row = cur.fetchone()

        xgb_result = {
            "bullish_prob": playbook_prior["bullish_prob"],
            "bearish_prob": playbook_prior["bearish_prob"],
            "neutral_prob": playbook_prior["neutral_prob"],
            "source": "playbook_prior",
        }

        if row:
            feature_arr = _build_feature_vector(row, symbol)
            xgb = _load_xgb()
            if xgb is not None:
                try:
                    proba = xgb.predict_proba(feature_arr)[0]
                    prob_map: dict[int, float] = {}
                    for cls_id, p in zip(xgb.classes_, proba.tolist()):
                        prob_map[direction_from_xgb_class(int(cls_id))] = float(p)
                    model_result = {
                        "bullish_prob": round(prob_map.get(1, 0.0), 3),
                        "neutral_prob": round(prob_map.get(0, 0.0), 3),
                        "bearish_prob": round(prob_map.get(-1, 0.0), 3),
                        "source": "xgboost",
                    }
                    # Stronger playbook blend when model was trained with full features
                    w = 0.45 if len(_feature_names_for_model(xgb)) == len(FEATURES) else 0.35
                    xgb_result = _blend_probs(model_result, playbook_prior, weight=w)
                except Exception as e:
                    logger.warning("XGBoost inference error: %s — using playbook prior", e)

        prophet_result = {}
        m = _load_prophet(symbol)
        if m is not None:
            try:
                future = m.make_future_dataframe(periods=30)
                forecast = m.predict(future)
                last = forecast.iloc[-1]
                prophet_result = {
                    "forecast_30d": round(float(last["yhat"]), 2),
                    "lower_80": round(float(last["yhat_lower"]), 2),
                    "upper_80": round(float(last["yhat_upper"]), 2),
                }
            except Exception as e:
                logger.warning("Prophet inference error: %s", e)

        lstm_result = get_lstm_scores(symbol)

        if xgb_result.get("source", "").startswith("playbook_prior") and lstm_result.get("source") == "lstm":
            xgb_result = _blend_probs(
                {
                    "bullish_prob": lstm_result["up_prob"],
                    "bearish_prob": lstm_result["down_prob"],
                    "neutral_prob": max(0.0, 1.0 - lstm_result["up_prob"] - lstm_result["down_prob"]),
                    "source": "lstm",
                },
                playbook_prior,
                weight=0.45,
            )

        return {
            **xgb_result,
            "lstm": lstm_result,
            "prophet": prophet_result,
            "playbook_features": playbook_feats,
            "playbook_feature_count": len(PLAYBOOK_ML_FEATURE_NAMES) + len(GRAHAM_ML_FEATURE_NAMES),
            "ml_framework": "Stock Analysis Playbook + Intelligent Investor",
        }

    except Exception as e:
        logger.error("get_ml_scores failed for %s: %s", symbol, e)
        prior = playbook_direction_prior(symbol)
        return {
            **prior,
            "source": "playbook_prior",
            "lstm": get_lstm_scores(symbol),
            "prophet": {},
        }
