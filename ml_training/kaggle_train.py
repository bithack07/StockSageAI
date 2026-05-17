#!/usr/bin/env python3
"""
Train StockSage models on Kaggle (free GPU optional for LSTM).

Setup on Kaggle:
  1. New Notebook → Settings → Internet ON, GPU optional (for LSTM).
  2. Add dataset: search "NSE" or "Indian stock" OHLCV, OR rely on yfinance (no dataset required).
  3. Upload backend/ + ml_training/ OR clone (repo must be public on Kaggle, or use a PAT):
       import os; os.environ["GIT_TERMINAL_PROMPT"] = "0"
       !git clone --depth 1 https://github.com/bithack07/StockSageAI.git
  4. Run:
       %cd StockSageAI/backend
       !pip install -q xgboost prophet ta yfinance scikit-learn joblib torch
       !python ../ml_training/kaggle_train.py --output /kaggle/working/models

  5. Download /kaggle/working/models/* and copy to backend/app/models/

Recommended Kaggle datasets (search on kaggle.com/datasets):
  - "NSE India Stock Market Historical Data" / Nifty 50 daily OHLCV
  - "Indian Stock Market Dataset" (symbol, date, open, high, low, close, volume)
  - "World Stock Prices Daily Updating" (filter .NS tickers)

If using a CSV dataset, pass: --csv /kaggle/input/YOUR_DATASET/prices.csv
  CSV columns: symbol, date, open, high, low, close, volume
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Paths: Kaggle vs local
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# Reuse main trainer
from train_all import (  # noqa: E402
    HORIZON_DAYS,
    NIFTY_50_SYMBOLS,
    train_lstm,
    train_prophet_models,
    train_xgboost,
)

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("kaggle_train")


def patch_models_dir(output: Path):
    import train_all as ta
    import app.pipelines.ml_inference as mi

    out = str(output.resolve())
    ta.MODELS_DIR = output
    ta.PROPHET_DIR = output / "prophet_models"
    mi.MODELS_DIR = out
    output.mkdir(parents=True, exist_ok=True)
    (output / "prophet_models").mkdir(parents=True, exist_ok=True)
    logger.info("Models will be saved to %s", output)


def main():
    parser = argparse.ArgumentParser(description="StockSage Kaggle trainer (playbook features)")
    parser.add_argument(
        "--output",
        default=os.environ.get("STOCKSAGE_MODELS_DIR", str(BACKEND / "app" / "models")),
        help="Output directory (use /kaggle/working/models on Kaggle)",
    )
    parser.add_argument("--symbols", nargs="*", default=NIFTY_50_SYMBOLS)
    parser.add_argument("--skip-xgb", action="store_true")
    parser.add_argument("--skip-prophet", action="store_true")
    parser.add_argument("--skip-lstm", action="store_true")
    parser.add_argument("--lstm-epochs", type=int, default=25)
    parser.add_argument("--skip-cv", action="store_true")
    parser.add_argument(
        "--csv",
        default=None,
        help="Optional OHLCV CSV (symbol,date,open,high,low,close,volume) — else yfinance",
    )
    args = parser.parse_args()

    output = Path(args.output)
    patch_models_dir(output)

    if args.csv:
        logger.info(
            "CSV mode noted (%s). For full pipeline, ingest CSV into ohlcv table or extend build_symbol_frame.",
            args.csv,
        )
        logger.info("Default: using yfinance for symbols (Internet required).")

    symbols = args.symbols
    logger.info(
        "Training %d symbols with playbook ML features (%d XGB cols). Horizon=%dd",
        len(symbols),
        len(__import__("app.services.ml_playbook_features", fromlist=["ML_FULL_FEATURE_NAMES"]).ML_FULL_FEATURE_NAMES),
        HORIZON_DAYS,
    )

    if not args.skip_xgb:
        train_xgboost(symbols, skip_cv=args.skip_cv)
    if not args.skip_prophet:
        train_prophet_models(symbols)
    if not args.skip_lstm:
        train_lstm(symbols, epochs=args.lstm_epochs)

    logger.info("Done. Upload these files to backend/app/models/:")
    logger.info("  - xgb_model.joblib")
    logger.info("  - lstm_weights.pt")
    logger.info("  - prophet_models/*.pkl")


if __name__ == "__main__":
    main()
