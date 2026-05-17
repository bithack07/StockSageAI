"""LSTM inference — must match ml_training/train_all.py train_lstm()."""
import logging
import os
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD
from ta.volatility import BollingerBands

from app.services.ml_playbook_features import LSTM_FEATURE_COLS, enrich_training_frame

logger = logging.getLogger(__name__)

SEQ_LEN = 30
HORIZON_DAYS = 7
FEATURE_COLS = list(LSTM_FEATURE_COLS)
MIN_HISTORY = SEQ_LEN + 55


def _history_from_db(symbol: str) -> Optional[pd.DataFrame]:
    try:
        from app.db import get_db

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT date, open, high, low, close, volume
                   FROM ohlcv WHERE symbol = %s ORDER BY date ASC""",
                (symbol,),
            )
            rows = cur.fetchall()
        if len(rows) < MIN_HISTORY:
            return None
        df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
        df["date"] = pd.to_datetime(df["date"])
        for col in ("open", "high", "low", "close", "volume"):
            df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)
        return df.dropna(subset=["close"])
    except Exception as e:
        logger.debug("LSTM DB history unavailable for %s: %s", symbol, e)
        return None


def _history_from_yfinance(symbol: str) -> pd.DataFrame:
    hist = yf.Ticker(symbol).history(period="5y", interval="1d")
    if hist.empty:
        return pd.DataFrame()
    df = hist.reset_index()
    df.columns = [c.lower() for c in df.columns]
    col = "date" if "date" in df.columns else "datetime"
    return df.rename(columns={col: "date"})[["date", "open", "high", "low", "close", "volume"]]


def build_feature_frame(df: pd.DataFrame, symbol: str = "") -> pd.DataFrame:
    """Normalize features the same way as train_all.train_lstm (incl. playbook channels)."""
    out = df.copy()
    out["close_norm"] = out["close"].pct_change()
    vol_std = out["volume"].rolling(20).std() + 1e-8
    out["volume_norm"] = (out["volume"] - out["volume"].rolling(20).mean()) / vol_std
    out["rsi_norm"] = RSIIndicator(close=out["close"], window=14).rsi()
    out["macd_norm"] = MACD(close=out["close"]).macd()
    bb = BollingerBands(close=out["close"], window=20, window_dev=2)
    out["bb_pos"] = bb.bollinger_pband()
    out["ema20"] = EMAIndicator(close=out["close"], window=20).ema_indicator()
    out["ema50"] = EMAIndicator(close=out["close"], window=50).ema_indicator()
    out["ema200"] = EMAIndicator(close=out["close"], window=200).ema_indicator()
    out["rsi"] = RSIIndicator(close=out["close"], window=14).rsi()

    if symbol:
        out = enrich_training_frame(out, symbol, {})

    for col in FEATURE_COLS:
        if col not in out.columns:
            out[col] = 0.0
        std = out[col].std()
        if std and std > 0:
            out[col] = (out[col] - out[col].mean()) / std
    return out.dropna()


def build_sequence(symbol: str) -> Optional[np.ndarray]:
    df = _history_from_db(symbol)
    if df is None or df.empty:
        df = _history_from_yfinance(symbol)
    if df.empty or len(df) < MIN_HISTORY:
        return None
    frame = build_feature_frame(df, symbol=symbol)
    if len(frame) < SEQ_LEN:
        return None
    seq = frame[FEATURE_COLS].iloc[-SEQ_LEN:].values.astype(np.float32)
    return np.nan_to_num(seq, nan=0.0, posinf=0.0, neginf=0.0)


_lstm_model = None
_lstm_n_features: Optional[int] = None


def _get_model():
    global _lstm_model, _lstm_n_features
    if _lstm_model is not None:
        return _lstm_model

    models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
    path = os.path.join(models_dir, "lstm_weights.pt")
    if not os.path.exists(path):
        return None

    import torch
    import torch.nn as nn

    class StockLSTM(nn.Module):
        def __init__(self, n_features, hidden=128, n_layers=2, dropout=0.3):
            super().__init__()
            self.lstm = nn.LSTM(
                n_features, hidden, n_layers, batch_first=True,
                dropout=dropout, bidirectional=True,
            )
            self.head = nn.Sequential(
                nn.Linear(hidden * 2, 64), nn.ReLU(), nn.Dropout(dropout),
                nn.Linear(64, 2),
            )

        def forward(self, x):
            out, _ = self.lstm(x)
            return self.head(out[:, -1, :])

    load_kw = {"map_location": "cpu"}
    try:
        state = torch.load(path, weights_only=True, **load_kw)
    except TypeError:
        state = torch.load(path, **load_kw)

    # Infer input size from checkpoint (supports legacy 5-dim and new playbook LSTM)
    w = state.get("lstm.weight_ih_l0")
    n_in = w.shape[1] if w is not None else len(FEATURE_COLS)
    _lstm_n_features = n_in

    model = StockLSTM(n_in)
    model.load_state_dict(state)
    model.eval()
    _lstm_model = model
    logger.info("LSTM model loaded from %s (n_features=%d)", path, n_in)
    return _lstm_model


def get_lstm_scores(symbol: str) -> dict:
    """7-day direction probabilities from trained LSTM."""
    fallback = {
        "up_prob": 0.5,
        "down_prob": 0.5,
        "direction": "NEUTRAL",
        "horizon_days": HORIZON_DAYS,
        "source": "fallback",
    }
    try:
        model = _get_model()
        if model is None:
            return fallback

        seq = build_sequence(symbol)
        if seq is None:
            logger.warning("Insufficient history for LSTM: %s", symbol)
            fallback["source"] = "no_data"
            return fallback

        # Legacy model: use first n_in columns only
        if _lstm_n_features and seq.shape[1] > _lstm_n_features:
            seq = seq[:, :_lstm_n_features]
        elif _lstm_n_features and seq.shape[1] < _lstm_n_features:
            pad = np.zeros((seq.shape[0], _lstm_n_features - seq.shape[1]), dtype=np.float32)
            seq = np.hstack([seq, pad])

        import torch

        x = torch.tensor(seq[np.newaxis, ...], dtype=torch.float32)
        with torch.no_grad():
            logits = model(x)
            probs = torch.softmax(logits, dim=1)[0].tolist()
        down_prob, up_prob = round(probs[0], 3), round(probs[1], 3)
        direction = "BULLISH" if up_prob > 0.55 else "BEARISH" if up_prob < 0.45 else "NEUTRAL"
        return {
            "up_prob": up_prob,
            "down_prob": down_prob,
            "direction": direction,
            "horizon_days": HORIZON_DAYS,
            "source": "lstm",
            "n_features": _lstm_n_features,
        }
    except Exception as e:
        logger.warning("LSTM inference failed for %s: %s", symbol, e)
        fallback["source"] = "error"
        return fallback
