"""Canonical NSE/BSE symbols — one ticker per company, clear labels for users."""
from __future__ import annotations

from app.services.india_market import BSE_SUFFIX, NSE_SUFFIX

# Company-name / informal tickers → Yahoo Finance NSE base symbol
_YAHOO_BASE_ALIASES: dict[str, str] = {
    "INFOSYS": "INFY",
    "HINDUNILEVER": "HINDUNILVR",
    "HINDUSTANUNILEVER": "HINDUNILVR",
    "ICICI": "ICICIBANK",
    "SBI": "SBIN",
    "STATEBANK": "SBIN",
    "STATEBANKOFINDIA": "SBIN",
    "BAJAJAUTO": "BAJAJ-AUTO",
    "TATAMOTOR": "TMPV",
    "TATAMOTORS": "TMPV",
    "TATASTEELS": "TATASTEEL",
    "HDFC": "HDFCBANK",
}


def base_ticker(symbol: str) -> str:
    """INFY.NS → INFY, ^NSEI → ^NSEI"""
    s = symbol.upper().strip()
    if s.endswith(NSE_SUFFIX):
        return s[: -len(NSE_SUFFIX)]
    if s.endswith(BSE_SUFFIX):
        return s[: -len(BSE_SUFFIX)]
    return s


def exchange_from_symbol(symbol: str) -> str:
    s = symbol.upper()
    if s.endswith(BSE_SUFFIX):
        return "BSE"
    if s.endswith(NSE_SUFFIX) or (not s.startswith("^") and "." not in s):
        return "NSE"
    return "OTHER"


def _normalize_base(base: str) -> str:
    """Map informal names (INFOSYS) to Yahoo tickers (INFY)."""
    b = base.upper().strip()
    return _YAHOO_BASE_ALIASES.get(b, b)


def canonical_symbol(symbol: str, prefer: str = "NSE") -> str:
    """
    Single stored form for Indian equities (default NSE .NS).
    INFY, INFY.NS, infy → INFY.NS
    INFOSYS, INFOSYS.NS → INFY.NS
    """
    s = symbol.upper().strip()
    if not s:
        return s
    if s.startswith("^"):
        return s
    if s.endswith(NSE_SUFFIX):
        return f"{_normalize_base(base_ticker(s))}{NSE_SUFFIX}"
    if s.endswith(BSE_SUFFIX):
        return f"{_normalize_base(base_ticker(s))}{BSE_SUFFIX}"
    base = _normalize_base(s)
    if prefer.upper() == "BSE":
        return f"{base}{BSE_SUFFIX}"
    return f"{base}{NSE_SUFFIX}"


def symbols_equivalent(a: str, b: str) -> bool:
    return canonical_symbol(a) == canonical_symbol(b)


def symbol_display(symbol: str, company_name: str | None = None) -> dict:
    """User-facing labels — avoids INFY vs INFY.NS confusion."""
    canon = canonical_symbol(symbol)
    base = base_ticker(canon)
    exchange = exchange_from_symbol(canon)
    name = (company_name or base).strip()
    return {
        "canonical_symbol": canon,
        "base_ticker": base,
        "exchange": exchange,
        "company_name": name,
        "short_label": f"{base} ({exchange})",
        "label": f"{name} · {base} ({exchange})",
        "hint": f"Same stock on {exchange} — stored as {canon}",
    }


def dedupe_search_results(results: list[dict]) -> list[dict]:
    """Merge INFY + INFY.NS into one row; prefer NSE with a real company name."""
    by_base: dict[str, dict] = {}

    for raw in results:
        sym = (raw.get("symbol") or "").strip()
        if not sym:
            continue
        canon = canonical_symbol(sym)
        base = base_ticker(canon)
        name = raw.get("longname") or raw.get("name") or raw.get("shortname") or base
        enriched = {
            **raw,
            **symbol_display(canon, str(name)),
            "symbol": canon,
        }

        if base not in by_base:
            by_base[base] = enriched
            continue

        prev = by_base[base]
        # Prefer NSE over BSE/ambiguous
        if enriched["exchange"] == "NSE" and prev.get("exchange") != "NSE":
            by_base[base] = enriched
            continue
        # Prefer longer company name (not equal to ticker)
        prev_name = prev.get("company_name") or ""
        new_name = enriched.get("company_name") or ""
        if len(new_name) > len(prev_name) and new_name.upper() != base:
            by_base[base] = enriched

    return list(by_base.values())


def match_variants(symbol: str) -> list[str]:
    """DB lookup aliases for analyses / ohlcv (canonical first)."""
    canon = canonical_symbol(symbol)
    base = base_ticker(canon)
    variants = [canon]
    if f"{base}{NSE_SUFFIX}" not in variants:
        variants.append(f"{base}{NSE_SUFFIX}")
    if f"{base}{BSE_SUFFIX}" not in variants:
        variants.append(f"{base}{BSE_SUFFIX}")
    if base not in variants:
        variants.append(base)
    raw = symbol.upper().strip()
    if raw not in variants:
        variants.append(raw)
    for alt, target in _YAHOO_BASE_ALIASES.items():
        if target != base:
            continue
        for candidate in (alt, f"{alt}{NSE_SUFFIX}", f"{alt}{BSE_SUFFIX}"):
            if candidate not in variants:
                variants.append(candidate)
    return list(dict.fromkeys(variants))
