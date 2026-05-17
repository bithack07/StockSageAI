"""Constants and helpers for Indian equities (NSE/BSE)."""

# Typical India 1-year FD / RBI policy reference (user can override in profile)
DEFAULT_FD_RATE_PCT = 7.0
NIFTY_50_SYMBOL = "^NSEI"
NSE_SUFFIX = ".NS"
BSE_SUFFIX = ".BO"

# Nifty 50 sector map (fallback when yfinance sector missing)
NIFTY_SECTOR_MAP: dict[str, str] = {
    "RELIANCE": "Energy",
    "TCS": "IT",
    "HDFCBANK": "Financials",
    "INFY": "IT",
    "ICICIBANK": "Financials",
    "HINDUNILVR": "FMCG",
    "ITC": "FMCG",
    "SBIN": "Financials",
    "BHARTIARTL": "Telecom",
    "KOTAKBANK": "Financials",
    "LT": "Industrials",
    "AXISBANK": "Financials",
    "ASIANPAINT": "Consumer",
    "MARUTI": "Auto",
    "TITAN": "Consumer",
    "BAJFINANCE": "Financials",
    "HCLTECH": "IT",
    "WIPRO": "IT",
    "SUNPHARMA": "Pharma",
    "TMPV": "Auto",
    "TATAMOTORS": "Auto",
    "TATASTEEL": "Metals",
    "ADANIENT": "Conglomerate",
    "ADANIPORTS": "Infrastructure",
}


def normalize_nse_symbol(symbol: str) -> str:
    from app.services.symbols import canonical_symbol
    return canonical_symbol(symbol, prefer="NSE")


def base_ticker(symbol: str) -> str:
    from app.services.symbols import base_ticker as _base
    return _base(symbol)
