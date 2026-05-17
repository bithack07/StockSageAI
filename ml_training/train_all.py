#!/usr/bin/env python3
"""
Train XGBoost, Prophet, and LSTM for all Nifty 50 symbols.
Outputs:
  backend/app/models/xgb_model.joblib
  backend/app/models/lstm_weights.pt
  backend/app/models/prophet_models/{SYMBOL}.pkl

Usage:
  cd StockSageAI/backend && source venv/bin/activate
  pip install xgboost prophet scikit-learn joblib
  python ../ml_training/train_all.py
"""
from __future__ import annotations

import argparse
import logging
import os
import pickle
import sys
import time
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.model_selection import TimeSeriesSplit
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import EMAIndicator, MACD
from ta.volatility import AverageTrueRange, BollingerBands
warnings.filterwarnings("ignore")

def _get_classifier():
    try:
        from xgboost import XGBClassifier
        return "xgboost", lambda **kw: XGBClassifier(**kw)
    except Exception as e:
        logger.warning("XGBoost unavailable (%s); using HistGradientBoosting", e)
        from sklearn.ensemble import HistGradientBoostingClassifier
        return "sklearn", lambda **kw: HistGradientBoostingClassifier(
            max_iter=kw.get("n_estimators", 300),
            max_depth=kw.get("max_depth", 5),
            learning_rate=kw.get("learning_rate", 0.05),
            random_state=kw.get("random_state", 42),
        )
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("train_all")

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
MODELS_DIR = BACKEND / "app" / "models"
PROPHET_DIR = MODELS_DIR / "prophet_models"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.intelligent_investor import GRAHAM_ML_FEATURE_NAMES, graham_ml_features
from app.services.ml_playbook_features import (
    LSTM_FEATURE_COLS,
    ML_FULL_FEATURE_NAMES,
    enrich_training_frame,
)
from app.services.ml_labels import encode_direction_targets
from app.services.training_universe import (
    NIFTY_50_SYMBOLS,
    prophet_symbol_subset,
    resolve_training_symbols,
)

# Must match app/pipelines/ml_inference.py
FEATURES = list(ML_FULL_FEATURE_NAMES)

HORIZON_DAYS = 7
RETURN_THRESHOLD = 0.02

# yfinance rate-limits aggressive scraping (~2 calls/symbol: history + info + graham)
DEFAULT_YF_SLEEP_S = float(os.environ.get("STOCKSAGE_YF_SLEEP", "0.35"))


def _yf_retry(func, label: str = "yfinance"):
    """Retry on Yahoo rate limits with exponential backoff."""
    last_err: Exception | None = None
    for attempt in range(5):
        try:
            return func()
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            if "too many requests" in msg or "rate limit" in msg:
                wait = DEFAULT_YF_SLEEP_S * (2 ** attempt)
                logger.warning("%s rate limited (attempt %d), sleeping %.1fs", label, attempt + 1, wait)
                time.sleep(wait)
            else:
                raise
    assert last_err is not None
    raise last_err


def _sanitize_feature_matrix(X: np.ndarray) -> np.ndarray:
    """XGBoost rejects inf / huge values in QuantileDMatrix."""
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    return np.clip(X, -1e4, 1e4).astype(np.float32)


def _fundamentals_for_symbol(symbol: str) -> dict:
    """Static fundamentals from yfinance (applied to all rows for that symbol)."""
    try:
        info = _yf_retry(lambda: yf.Ticker(symbol).info or {}, symbol)
        return {
            "pe_ratio": float(info.get("trailingPE") or info.get("forwardPE") or 0) or 0.0,
            "roce": float(info.get("returnOnEquity") or 0) or 0.0,
            "debt_equity": float(info.get("debtToEquity") or 0) or 0.0,
        }
    except Exception:
        return {"pe_ratio": 0.0, "roce": 0.0, "debt_equity": 0.0}


def build_symbol_frame(symbol: str, period: str = "5y") -> pd.DataFrame:
    hist = _yf_retry(
        lambda: yf.Ticker(symbol).history(period=period, interval="1d"),
        symbol,
    )
    if hist.empty or len(hist) < 220:
        return pd.DataFrame()

    df = hist.reset_index()
    df.columns = [c.lower() for c in df.columns]
    if "date" not in df.columns and "datetime" in df.columns:
        df = df.rename(columns={"datetime": "date"})

    close = df["close"]
    high = df["high"]
    low = df["low"]

    volume = df["volume"] if "volume" in df.columns else pd.Series(0.0, index=df.index)
    out = pd.DataFrame({"date": df["date"], "close": close, "volume": volume})
    out["rsi"] = RSIIndicator(close=close, window=14).rsi()
    macd_ind = MACD(close=close)
    out["macd"] = macd_ind.macd()
    bb = BollingerBands(close=close, window=20, window_dev=2)
    out["bb_upper"] = bb.bollinger_hband()
    out["bb_lower"] = bb.bollinger_lband()
    out["atr"] = AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range()
    out["ema20"] = EMAIndicator(close=close, window=20).ema_indicator()
    out["ema50"] = EMAIndicator(close=close, window=50).ema_indicator()
    out["ema200"] = EMAIndicator(close=close, window=200).ema_indicator()
    out["composite_score"] = 0.0

    fund = _fundamentals_for_symbol(symbol)
    for k, v in fund.items():
        out[k] = v

    try:
        graham = graham_ml_features(symbol)
        for k in GRAHAM_ML_FEATURE_NAMES:
            out[k] = graham[k]
    except Exception as e:
        logger.warning("  %s: Graham features default — %s", symbol, e)
        for k in GRAHAM_ML_FEATURE_NAMES:
            out[k] = 0.0

    out = enrich_training_frame(out, symbol, fund)

    future_ret = out["close"].shift(-HORIZON_DAYS) / out["close"] - 1
    out["target"] = np.where(
        future_ret > RETURN_THRESHOLD, 1,
        np.where(future_ret < -RETURN_THRESHOLD, -1, 0),
    )
    out["symbol"] = symbol
    out = out.dropna(subset=FEATURES + ["target"])
    for col in FEATURES:
        if col in out.columns:
            out[col] = (
                pd.to_numeric(out[col], errors="coerce")
                .replace([np.inf, -np.inf], np.nan)
                .fillna(0.0)
            )
    return out


def train_xgboost(symbols: list[str], skip_cv: bool = False, yf_sleep_s: float = DEFAULT_YF_SLEEP_S) -> str:
    logger.info("=== XGBoost: building dataset ===")
    if yf_sleep_s > 0:
        logger.info("yfinance throttle: %.2fs pause between symbols (avoid rate limits)", yf_sleep_s)
    frames = []
    for i, sym in enumerate(symbols):
        if yf_sleep_s > 0 and i > 0:
            time.sleep(yf_sleep_s)
        try:
            df = build_symbol_frame(sym)
            if not df.empty:
                frames.append(df)
                logger.info("  %s: %d rows", sym, len(df))
            else:
                logger.warning("  %s: skipped (insufficient data)", sym)
        except Exception as e:
            logger.warning("  %s: failed — %s", sym, e)

    if not frames:
        raise RuntimeError("No training data for XGBoost")

    data = pd.concat(frames, ignore_index=True)
    logger.info(
        "Total rows: %d from %d / %d symbols | target dist:\n%s",
        len(data),
        len(frames),
        len(symbols),
        data["target"].value_counts(),
    )

    X = _sanitize_feature_matrix(data[FEATURES].values.astype(np.float32))
    y = encode_direction_targets(data["target"].values.astype(np.int32))

    backend_name, Cls = _get_classifier()
    kw = dict(n_estimators=300, max_depth=5, learning_rate=0.05, random_state=42)

    if not skip_cv:
        tscv = TimeSeriesSplit(n_splits=3)
        for fold, (tr, va) in enumerate(tscv.split(X)):
            m = Cls(**kw)
            m.fit(X[tr], y[tr])
            logger.info("  CV fold %d accuracy: %.3f", fold + 1, m.score(X[va], y[va]))

    model = Cls(**kw)
    model.fit(X, y)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    path = MODELS_DIR / "xgb_model.joblib"
    joblib.dump(model, path)
    logger.info("Saved direction model (%s) → %s", backend_name, path)
    return str(path)


def train_prophet_models(symbols: list[str], yf_sleep_s: float = DEFAULT_YF_SLEEP_S) -> int:
    from prophet import Prophet

    PROPHET_DIR.mkdir(parents=True, exist_ok=True)
    ok = 0
    holidays = pd.DataFrame({
        "holiday": ["Republic Day", "Independence Day", "Diwali", "Christmas"],
        "ds": pd.to_datetime(["2024-01-26", "2024-08-15", "2024-11-01", "2024-12-25"]),
        "lower_window": 0,
        "upper_window": 1,
    })

    logger.info("=== Prophet: training per symbol ===")
    for i, sym in enumerate(symbols):
        if yf_sleep_s > 0 and i > 0:
            time.sleep(yf_sleep_s)
        try:
            hist = _yf_retry(
                lambda: yf.Ticker(sym).history(period="5y", interval="1d"),
                sym,
            )
            if hist.empty or len(hist) < 60:
                logger.warning("  %s: skipped", sym)
                continue
            pdf = hist.reset_index()
            pdf.columns = [c.lower() for c in pdf.columns]
            col = "date" if "date" in pdf.columns else "datetime"
            frame = pdf[[col, "close"]].rename(columns={col: "ds", "close": "y"})
            frame["ds"] = pd.to_datetime(frame["ds"], utc=True).dt.tz_localize(None)
            frame = frame.dropna().sort_values("ds")

            m = Prophet(
                holidays=holidays,
                daily_seasonality=False,
                weekly_seasonality=True,
                yearly_seasonality=True,
                changepoint_prior_scale=0.05,
            )
            m.fit(frame)
            out_path = PROPHET_DIR / f"{sym}.pkl"
            with open(out_path, "wb") as f:
                pickle.dump(m, f)
            ok += 1
            logger.info("  %s → %s", sym, out_path.name)
        except Exception as e:
            logger.warning("  %s prophet failed: %s", sym, e)
    logger.info("Prophet models saved: %d / %d", ok, len(symbols))
    return ok


def train_lstm(symbols: list[str], epochs: int = 25, yf_sleep_s: float = DEFAULT_YF_SLEEP_S) -> str:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset

    logger.info("=== LSTM: building sequences (with playbook channels) ===")
    SEQ_LEN = 30
    FEATURE_COLS = list(LSTM_FEATURE_COLS)

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

    all_X, all_y = [], []
    for i, sym in enumerate(symbols):
        if yf_sleep_s > 0 and i > 0:
            time.sleep(yf_sleep_s)
        try:
            hist = _yf_retry(
                lambda: yf.Ticker(sym).history(period="5y", interval="1d"),
                sym,
            )
            if hist.empty or len(hist) < SEQ_LEN + HORIZON_DAYS + 50:
                continue
            df = hist.reset_index()
            df.columns = [c.lower() for c in df.columns]
            df["close_norm"] = df["close"].pct_change()
            df["volume_norm"] = (df["volume"] - df["volume"].rolling(20).mean()) / (df["volume"].rolling(20).std() + 1e-8)
            df["rsi_norm"] = RSIIndicator(close=df["close"], window=14).rsi()
            df["macd_norm"] = MACD(close=df["close"]).macd()
            bb = BollingerBands(close=df["close"], window=20, window_dev=2)
            df["bb_pos"] = bb.bollinger_pband()
            df["ema20"] = EMAIndicator(close=df["close"], window=20).ema_indicator()
            df["ema50"] = EMAIndicator(close=df["close"], window=50).ema_indicator()
            df["ema200"] = EMAIndicator(close=df["close"], window=200).ema_indicator()
            df = enrich_training_frame(df, sym, _fundamentals_for_symbol(sym))
            for c in FEATURE_COLS:
                if c not in df.columns:
                    df[c] = 0.0
                std = df[c].std()
                if std and std > 0:
                    df[c] = (df[c] - df[c].mean()) / std
            df["target"] = (df["close"].shift(-HORIZON_DAYS) > df["close"]).astype(int)
            df = df.dropna()
            X, y = [], []
            for i in range(SEQ_LEN, len(df)):
                X.append(df[FEATURE_COLS].iloc[i - SEQ_LEN : i].values)
                y.append(int(df["target"].iloc[i]))
            if X:
                all_X.append(np.array(X, dtype=np.float32))
                all_y.append(np.array(y, dtype=np.int64))
                logger.info("  %s: %d sequences", sym, len(X))
        except Exception as e:
            logger.warning("  %s lstm data failed: %s", sym, e)

    if not all_X:
        raise RuntimeError("No LSTM training data")

    X_all = np.clip(
        np.nan_to_num(np.concatenate(all_X), nan=0.0, posinf=0.0, neginf=0.0),
        -1e4,
        1e4,
    )
    y_all = np.concatenate(all_y)
    split = int(0.85 * len(X_all))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("LSTM device: %s | samples: %d", device, len(X_all))

    X_train = torch.tensor(X_all[:split].astype(np.float32), dtype=torch.float32)
    y_train = torch.tensor(y_all[:split].astype(np.int64), dtype=torch.long)
    X_val = torch.tensor(X_all[split:].astype(np.float32), dtype=torch.float32)
    y_val = torch.tensor(y_all[split:].astype(np.int64), dtype=torch.long)
    train_ds = TensorDataset(X_train, y_train)
    val_ds = TensorDataset(X_val, y_val)
    train_dl = DataLoader(train_ds, batch_size=64, shuffle=True)
    val_dl = DataLoader(val_ds, batch_size=64)

    model = StockLSTM(len(FEATURE_COLS)).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    crit = nn.CrossEntropyLoss()
    best_acc = 0.0

    for epoch in range(epochs):
        model.train()
        for xb, yb in train_dl:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            crit(model(xb), yb).backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
        model.eval()
        correct = 0
        with torch.no_grad():
            for xb, yb in val_dl:
                xb, yb = xb.to(device), yb.to(device)
                correct += (model(xb).argmax(1) == yb).sum().item()
        acc = correct / len(val_ds)
        if acc > best_acc:
            best_acc = acc
            MODELS_DIR.mkdir(parents=True, exist_ok=True)
            torch.save(model.state_dict(), MODELS_DIR / "lstm_weights.pt")
        if (epoch + 1) % 5 == 0:
            logger.info("  epoch %d/%d val_acc=%.3f", epoch + 1, epochs, acc)

    path = MODELS_DIR / "lstm_weights.pt"
    logger.info("Saved LSTM → %s (best val_acc=%.3f)", path, best_acc)
    return str(path)


def main():
    parser = argparse.ArgumentParser(description="Train all StockSage ML models")
    parser.add_argument(
        "--universe",
        choices=("nifty50", "nifty500", "nse_all"),
        default="nse_all",
        help="Symbol universe (default: all NSE equities)",
    )
    parser.add_argument(
        "--symbols-file",
        default=None,
        help="Optional text/CSV file of tickers (overrides --universe)",
    )
    parser.add_argument(
        "--symbols",
        nargs="*",
        default=None,
        help="Explicit symbol list (overrides universe when provided)",
    )
    parser.add_argument(
        "--max-symbols",
        type=int,
        default=None,
        help="Cap symbol count (debug / Kaggle time limits)",
    )
    parser.add_argument("--skip-xgb", action="store_true")
    parser.add_argument("--skip-prophet", action="store_true")
    parser.add_argument(
        "--prophet-max",
        type=int,
        default=200,
        help="Max per-symbol Prophet models (0 = skip Prophet). Auto-capped for large universes.",
    )
    parser.add_argument("--skip-lstm", action="store_true")
    parser.add_argument("--lstm-epochs", type=int, default=25)
    parser.add_argument("--skip-cv", action="store_true", help="Skip XGBoost cross-validation")
    parser.add_argument(
        "--yf-sleep",
        type=float,
        default=DEFAULT_YF_SLEEP_S,
        help="Seconds to wait between symbols when fetching yfinance (default 0.35)",
    )
    args = parser.parse_args()

    if args.symbols:
        from app.services.training_universe import _to_nse_symbols
        symbols = _to_nse_symbols(args.symbols)
    else:
        symbols = resolve_training_symbols(
            args.universe,
            symbols_file=args.symbols_file,
            max_symbols=args.max_symbols,
        )

    logger.info("Training for %d symbols → %s", len(symbols), MODELS_DIR)

    if not args.skip_xgb:
        train_xgboost(symbols, skip_cv=args.skip_cv, yf_sleep_s=args.yf_sleep)
    if not args.skip_prophet:
        prophet_syms = prophet_symbol_subset(symbols, args.prophet_max)
        if not prophet_syms:
            logger.info("Prophet skipped (--prophet-max 0)")
        else:
            if len(prophet_syms) < len(symbols):
                logger.info(
                    "Prophet: training %d / %d symbols (use --prophet-max 0 to skip)",
                    len(prophet_syms),
                    len(symbols),
                )
            train_prophet_models(prophet_syms, yf_sleep_s=args.yf_sleep)
    if not args.skip_lstm:
        train_lstm(symbols, epochs=args.lstm_epochs, yf_sleep_s=args.yf_sleep)

    logger.info("=== Training complete ===")


if __name__ == "__main__":
    main()
