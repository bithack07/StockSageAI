"""Pipeline 4 — Fundamentals Ingestion (yfinance + DCF)."""
import json
import logging

import yfinance as yf
from celery import shared_task

from app.db import get_db

logger = logging.getLogger(__name__)


def _dcf_model(fcf: float, growth: float = 0.12, terminal_g: float = 0.05,
               wacc: float = 0.10, years: int = 5) -> float:
    if not fcf or fcf <= 0:
        return 0.0
    pv = 0.0
    for yr in range(1, years + 1):
        pv += fcf * ((1 + growth) ** yr) / ((1 + wacc) ** yr)
    terminal_value = fcf * ((1 + growth) ** years) * (1 + terminal_g) / (wacc - terminal_g)
    pv += terminal_value / ((1 + wacc) ** years)
    return round(pv, 2)


def _safe_float(val) -> float | None:
    try:
        v = float(val)
        return None if (v != v) else round(v, 4)  # NaN check
    except (TypeError, ValueError):
        return None


def _compute_ratios(info: dict, income_q, balance_q, cashflow_q) -> dict:
    ratios = {}
    try:
        ebit = None
        total_assets = None
        current_liabilities = None
        total_debt = None
        equity = None

        if balance_q is not None and not balance_q.empty:
            for col in balance_q.columns:
                col_data = balance_q[col]
                if "Total Assets" in balance_q.index:
                    total_assets = _safe_float(col_data.get("Total Assets"))
                if "Current Liabilities" in balance_q.index:
                    current_liabilities = _safe_float(col_data.get("Current Liabilities"))
                if "Total Debt" in balance_q.index:
                    total_debt = _safe_float(col_data.get("Total Debt"))
                if "Stockholders Equity" in balance_q.index:
                    equity = _safe_float(col_data.get("Stockholders Equity"))
                break

        if income_q is not None and not income_q.empty:
            for col in income_q.columns:
                col_data = income_q[col]
                if "EBIT" in income_q.index:
                    ebit = _safe_float(col_data.get("EBIT"))
                break

        if ebit and total_assets and current_liabilities:
            capital_employed = total_assets - current_liabilities
            ratios["roce"] = round(ebit / capital_employed, 4) if capital_employed else None

        if total_debt and equity and equity != 0:
            ratios["debt_equity"] = round(total_debt / equity, 4)

    except Exception as e:
        logger.debug(f"Ratio computation partial error: {e}")

    return ratios


@shared_task(name="pipelines.fundamentals.ingest_fundamentals", bind=True, max_retries=3)
def ingest_fundamentals(self, symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}

        income_q = None
        balance_q = None
        cashflow_q = None
        try:
            income_q = ticker.quarterly_financials
            balance_q = ticker.quarterly_balance_sheet
            cashflow_q = ticker.quarterly_cashflow
        except Exception:
            pass

        ratios = _compute_ratios(info, income_q, balance_q, cashflow_q)

        eps = _safe_float(info.get("trailingEps"))
        bvps = _safe_float(info.get("bookValue"))
        pe = _safe_float(info.get("trailingPE"))
        pb = _safe_float(info.get("priceToBook"))
        try:
            from app.services.intelligent_investor import graham_number, margin_of_safety_pct, pe_times_pb

            gnum = graham_number(eps, bvps)
            ratios["graham_number"] = gnum
            ratios["pe_times_pb"] = pe_times_pb(pe, pb)
            price = _safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
            ratios["margin_of_safety_pct"] = margin_of_safety_pct(gnum, price)
        except Exception:
            pass

        fcf = None
        try:
            if cashflow_q is not None and not cashflow_q.empty:
                if "Free Cash Flow" in cashflow_q.index:
                    fcf = float(cashflow_q.loc["Free Cash Flow"].mean())
        except Exception:
            pass

        wacc = 0.10
        dcf_value = _dcf_model(fcf or 0, wacc=wacc) if fcf else None

        row = {
            "symbol": symbol,
            "pe_ratio": _safe_float(info.get("trailingPE")),
            "pb_ratio": _safe_float(info.get("priceToBook")),
            "ev_ebitda": _safe_float(info.get("enterpriseToEbitda")),
            "roe": _safe_float(info.get("returnOnEquity")),
            "roce": ratios.get("roce"),
            "debt_equity": ratios.get("debt_equity") or _safe_float(info.get("debtToEquity")),
            "fcf": int(fcf) if fcf else None,
            "dcf_intrinsic": dcf_value,
            "market_cap": int(info.get("marketCap") or 0) or None,
            "promoter_pct": None,
            "pledge_pct": None,
            "ratios_json": json.dumps({
                **ratios,
                "eps": _safe_float(info.get("trailingEps")),
                "revenue_growth": _safe_float(info.get("revenueGrowth")),
                "profit_margins": _safe_float(info.get("profitMargins")),
                "gross_margins": _safe_float(info.get("grossMargins")),
                "52w_high": _safe_float(info.get("fiftyTwoWeekHigh")),
                "52w_low": _safe_float(info.get("fiftyTwoWeekLow")),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
            }),
        }

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO fundamentals
                   (symbol, pe_ratio, pb_ratio, ev_ebitda, roe, roce, debt_equity,
                    fcf, dcf_intrinsic, market_cap, promoter_pct, pledge_pct, ratios_json)
                   VALUES (%(symbol)s, %(pe_ratio)s, %(pb_ratio)s, %(ev_ebitda)s, %(roe)s,
                           %(roce)s, %(debt_equity)s, %(fcf)s, %(dcf_intrinsic)s,
                           %(market_cap)s, %(promoter_pct)s, %(pledge_pct)s, %(ratios_json)s)
                   ON CONFLICT (symbol) DO UPDATE
                   SET pe_ratio=EXCLUDED.pe_ratio, pb_ratio=EXCLUDED.pb_ratio,
                       ev_ebitda=EXCLUDED.ev_ebitda, roe=EXCLUDED.roe, roce=EXCLUDED.roce,
                       debt_equity=EXCLUDED.debt_equity, fcf=EXCLUDED.fcf,
                       dcf_intrinsic=EXCLUDED.dcf_intrinsic, market_cap=EXCLUDED.market_cap,
                       ratios_json=EXCLUDED.ratios_json, updated_at=NOW()""",
                row,
            )

        logger.info(f"Fundamentals ingested for {symbol}")
        return {"symbol": symbol, "pe": row["pe_ratio"], "dcf": dcf_value}

    except Exception as exc:
        logger.error(f"ingest_fundamentals failed for {symbol}: {exc}")
        raise self.retry(exc=exc, countdown=120)
