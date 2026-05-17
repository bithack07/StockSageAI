"""
Prophet per-ticker training.
Run on Kaggle Notebook (free T4 GPU, 30 hrs/week) or locally.
Usage: python train_prophet.py --symbols RELIANCE.NS TCS.NS INFY.NS
"""
import argparse
import logging
import os
import pickle
import sys

import pandas as pd
from prophet import Prophet

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_india_holidays():
    """Return Indian market holidays for Prophet."""
    holidays = pd.DataFrame({
        "holiday": [
            "Republic Day", "Holi", "Good Friday", "Eid al-Fitr",
            "Independence Day", "Gandhi Jayanti", "Diwali", "Christmas",
        ],
        "ds": pd.to_datetime([
            "2024-01-26", "2024-03-25", "2024-03-29", "2024-04-10",
            "2024-08-15", "2024-10-02", "2024-11-01", "2024-12-25",
        ]),
        "lower_window": 0,
        "upper_window": 1,
    })
    return holidays


def load_ohlcv_from_db(symbol: str) -> pd.DataFrame:
    """Load OHLCV from PostgreSQL. Requires DB credentials in env."""
    try:
        import psycopg2
        conn = psycopg2.connect(os.environ["DATABASE_URL"].replace("+asyncpg", ""))
        df = pd.read_sql(
            "SELECT date, close FROM ohlcv WHERE symbol=%s ORDER BY date",
            conn, params=(symbol,),
        )
        conn.close()
        return df.rename(columns={"date": "ds", "close": "y"})
    except Exception:
        # Fallback: download via yfinance
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5y", interval="1d")
        hist = hist.reset_index()
        hist.columns = [c.lower() for c in hist.columns]
        return hist[["date", "close"]].rename(columns={"date": "ds", "close": "y"})


def train_prophet(symbol: str, output_dir: str = "../backend/app/models/prophet_models") -> str:
    logger.info(f"Training Prophet for {symbol}...")
    os.makedirs(output_dir, exist_ok=True)

    df = load_ohlcv_from_db(symbol)
    df["ds"] = pd.to_datetime(df["ds"])
    df = df.dropna().sort_values("ds")

    if len(df) < 30:
        logger.warning(f"Not enough data for {symbol}: {len(df)} rows")
        return ""

    m = Prophet(
        holidays=get_india_holidays(),
        daily_seasonality=False,
        weekly_seasonality=True,
        yearly_seasonality=True,
        changepoint_prior_scale=0.05,
        seasonality_mode="multiplicative",
    )
    m.fit(df)

    # Filename must match ml_inference: prophet_models/{symbol}.pkl
    path = os.path.join(output_dir, f"{symbol}.pkl")
    with open(path, "wb") as f:
        pickle.dump(m, f)

    logger.info(f"Saved Prophet model for {symbol} → {path}")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", default=["RELIANCE.NS", "TCS.NS", "INFY.NS"])
    parser.add_argument("--output-dir", default="../backend/app/models/prophet_models")
    args = parser.parse_args()

    for sym in args.symbols:
        try:
            train_prophet(sym, args.output_dir)
        except Exception as e:
            logger.error(f"Failed for {sym}: {e}")
