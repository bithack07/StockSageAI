"""
Resolve symbol lists for ML training (Nifty 50 / 500 / full NSE equity universe).

Used by ml_training/train_all.py and kaggle_train.py.
"""
from __future__ import annotations

import io
import logging
import re
from pathlib import Path
from typing import Optional

import pandas as pd

from app.services.india_market import NSE_SUFFIX
from app.services.symbols import canonical_symbol

logger = logging.getLogger(__name__)

# Nifty 50 — keep in sync with market_data / train_all
NIFTY_50_SYMBOLS: list[str] = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "HINDUNILVR.NS",
    "ICICIBANK.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "LT.NS", "SBIN.NS",
    "BAJFINANCE.NS", "ASIANPAINT.NS", "AXISBANK.NS", "MARUTI.NS", "TITAN.NS",
    "NESTLEIND.NS", "HCLTECH.NS", "WIPRO.NS", "SUNPHARMA.NS", "ULTRACEMCO.NS",
    "BAJAJFINSV.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "TECHM.NS",
    "TMPV.NS", "INDUSINDBK.NS", "DIVISLAB.NS", "CIPLA.NS", "JSWSTEEL.NS",
    "HINDALCO.NS", "BPCL.NS", "COALINDIA.NS", "DRREDDY.NS", "ADANIPORTS.NS",
    "BRITANNIA.NS", "EICHERMOT.NS", "GRASIM.NS", "HEROMOTOCO.NS", "M&M.NS",
    "TATASTEEL.NS", "TATACONSUM.NS", "UPL.NS", "VEDL.NS", "SHREECEM.NS",
    "APOLLOHOSP.NS", "BAJAJ-AUTO.NS", "SBILIFE.NS", "HDFCLIFE.NS", "ADANIENT.NS",
]

_UNIVERSE_CHOICES = ("nifty50", "nifty500", "nse_all")

_NSE_CSV_URLS = (
    "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv",
    "https://archives.nseindia.com/content/equities/EQUITY_L.csv",
)

_NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; StockSageAI/1.0; +https://github.com/bithack07/StockSageAI)"
    ),
    "Accept": "text/csv,application/json,text/plain,*/*",
}


def _to_nse_symbols(bases: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in bases:
        s = str(raw).strip().upper()
        if not s or s in ("SYMBOL", "NAN"):
            continue
        if not re.match(r"^[A-Z0-9][A-Z0-9\-&]*$", s):
            continue
        canon = canonical_symbol(s if s.endswith(NSE_SUFFIX) else f"{s}{NSE_SUFFIX}")
        if canon not in seen:
            seen.add(canon)
            out.append(canon)
    return sorted(out)


def _load_symbols_file(path: str | Path) -> list[str]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Symbols file not found: {p}")
    lines = []
    if p.suffix.lower() == ".csv":
        df = pd.read_csv(p)
        col = next((c for c in df.columns if c.lower() in ("symbol", "ticker", "symbols")), df.columns[0])
        lines = df[col].astype(str).tolist()
    else:
        lines = [ln.strip() for ln in p.read_text().splitlines() if ln.strip() and not ln.startswith("#")]
    return _to_nse_symbols(lines)


def fetch_nse_equity_symbols() -> list[str]:
    """All NSE equity symbols from official EQUITY_L.csv (with fallbacks)."""
    import requests

    for url in _NSE_CSV_URLS:
        try:
            resp = requests.get(url, headers=_NSE_HEADERS, timeout=45)
            resp.raise_for_status()
            df = pd.read_csv(io.BytesIO(resp.content))
            col = next((c for c in df.columns if str(c).upper() == "SYMBOL"), df.columns[0])
            symbols = _to_nse_symbols(df[col].astype(str).tolist())
            if len(symbols) >= 100:
                logger.info("Loaded %d NSE symbols from %s", len(symbols), url)
                return symbols
        except Exception as exc:
            logger.warning("NSE symbol list failed (%s): %s", url, exc)

    # Fallback: Nifty 500 then 50
    n500 = fetch_nifty500_symbols()
    if len(n500) >= 100:
        logger.warning("NSE CSV unavailable; using Nifty 500 fallback (%d symbols)", len(n500))
        return n500
    logger.warning("NSE CSV unavailable; using Nifty 50 fallback")
    return list(NIFTY_50_SYMBOLS)


def fetch_nifty500_symbols() -> list[str]:
    """Nifty 500 constituents via Wikipedia (no NSE login required)."""
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/NIFTY_500", match="Symbol")
    except Exception:
        try:
            tables = pd.read_html("https://en.wikipedia.org/wiki/NIFTY_500")
        except Exception as exc:
            logger.warning("Nifty 500 Wikipedia fetch failed: %s", exc)
            return list(NIFTY_50_SYMBOLS)

    for table in tables:
        cols = {str(c).lower(): c for c in table.columns}
        sym_col = cols.get("symbol") or cols.get("ticker")
        if sym_col is None:
            continue
        bases = table[sym_col].astype(str).str.replace(r"\[.*\]", "", regex=True).str.strip()
        symbols = _to_nse_symbols(bases.tolist())
        if len(symbols) >= 100:
            logger.info("Loaded %d Nifty 500 symbols from Wikipedia", len(symbols))
            return symbols

    logger.warning("Nifty 500 table not parsed; using Nifty 50")
    return list(NIFTY_50_SYMBOLS)


def resolve_training_symbols(
    universe: str = "nse_all",
    *,
    symbols_file: Optional[str] = None,
    extra_symbols: Optional[list[str]] = None,
    max_symbols: Optional[int] = None,
) -> list[str]:
    """
    Resolve training tickers.

    universe:
      - nifty50   — Nifty 50 only
      - nifty500  — Nifty 500 (Wikipedia)
      - nse_all   — all NSE equities from EQUITY_L.csv (default for broad training)
    """
    u = (universe or "nse_all").lower().strip()
    if u not in _UNIVERSE_CHOICES:
        raise ValueError(f"universe must be one of {_UNIVERSE_CHOICES}, got {universe!r}")

    if symbols_file:
        symbols = _load_symbols_file(symbols_file)
    elif u == "nifty50":
        symbols = list(NIFTY_50_SYMBOLS)
    elif u == "nifty500":
        symbols = fetch_nifty500_symbols()
    else:
        symbols = fetch_nse_equity_symbols()

    if extra_symbols:
        symbols = _to_nse_symbols(symbols + list(extra_symbols))

    if max_symbols is not None and max_symbols > 0:
        symbols = symbols[: max_symbols]

    logger.info("Training universe=%s → %d symbols", u, len(symbols))
    return symbols


def prophet_symbol_subset(symbols: list[str], max_models: int) -> list[str]:
    """Cap per-symbol Prophet training (one .pkl per ticker)."""
    if max_models <= 0:
        return []
    if len(symbols) <= max_models:
        return symbols
    # Prefer Nifty 50 names first, then remainder in stable order
    nifty = [s for s in NIFTY_50_SYMBOLS if s in symbols]
    rest = [s for s in symbols if s not in set(nifty)]
    combined = nifty + rest
    return combined[:max_models]
