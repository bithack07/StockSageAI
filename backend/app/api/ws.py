"""WebSocket endpoint — /ws/analyze/{symbol} (authenticated)."""
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import text

from app.agents.analysis_log import send_step
from app.agents.orchestrator import stream_analysis
from app.auth.ws_auth import UNAUTHORIZED_CLOSE, validate_ws_token
from app.config import settings
from app.db.connection import AsyncSessionLocal
from app.pipelines.data_refresh import _ohlcv_count, ensure_symbol_data
from app.pipelines.market_data import ingest_ohlcv
from app.pipelines.technical_features import compute_technical_features
from app.pipelines.sentiment_pipeline import run_sentiment_pipeline
from app.pipelines.fundamentals import ingest_fundamentals
from app.services.analysis_freshness import analysis_age_minutes, is_analysis_fresh
from app.services.symbols import canonical_symbol, match_variants

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


def _safe_error_message(exc: Exception) -> str:
    if settings.debug:
        return str(exc)
    return "Analysis failed. Please try again later."


def _parse_json_field(val):
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            return {}
    return {}


async def _fetch_latest_row(symbol: str):
    variants = match_variants(symbol)
    keys = [f"v{i}" for i in range(len(variants))]
    in_clause = ", ".join(f":{k}" for k in keys)
    params = {k: v for k, v in zip(keys, variants)}
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text(
                "SELECT id, symbol, created_at, fundamental_json, technical_json, sentiment_json, prediction_json "
                f"FROM analyses WHERE symbol IN ({in_clause}) ORDER BY created_at DESC LIMIT 1"
            ),
            params,
        )
        return result.fetchone()


async def _replay_cached_analysis(websocket: WebSocket, row, symbol: str) -> None:
    created_at = str(row[2])
    age = analysis_age_minutes(created_at)
    age_label = f"{age} min ago" if age is not None and age < 120 else (
        f"{age // 60}h ago" if age is not None else "recently"
    )
    await send_step(
        websocket,
        phase="cache",
        status="done",
        message=f"Using saved analysis ({age_label})",
        detail="No agent run — open Refresh only when you need a new verdict.",
    )
    for agent, idx in (("fundamental", 3), ("technical", 4), ("sentiment", 5)):
        payload = _parse_json_field(row[idx])
        if payload:
            await websocket.send_json({"type": "agent_complete", "agent": agent, "output_json": payload})
    prediction = _parse_json_field(row[6])
    if prediction:
        await websocket.send_json({
            "type": "prediction_complete",
            **prediction,
            "analysis_source": "cached",
            "analyzed_at": created_at,
        })


@router.websocket("/ws/analyze/{symbol}")
async def analyze_websocket(websocket: WebSocket, symbol: str):
    token = websocket.query_params.get("token")
    user_id = validate_ws_token(token)
    if not user_id:
        await websocket.close(code=UNAUTHORIZED_CLOSE, reason="Authentication required")
        return

    force = websocket.query_params.get("force", "").lower() in ("1", "true", "yes")

    await websocket.accept()
    symbol = canonical_symbol(symbol)
    logger.info("WebSocket opened for %s (user=%s, force=%s)", symbol, user_id, force)

    try:
        if not force:
            row = await _fetch_latest_row(symbol)
            if row and is_analysis_fresh(row[2]) and _parse_json_field(row[6]):
                await _replay_cached_analysis(websocket, row, symbol)
                return

        await send_step(
            websocket, phase="data", status="done",
            message=f"Connected — preparing analysis for {symbol}",
        )

        await send_step(
            websocket, phase="data", status="running",
            message="Checking cached price history and indicators…",
        )

        had_cache = _ohlcv_count(symbol) > 0
        if had_cache:
            await send_step(
                websocket, phase="data", status="done",
                message="Price history loaded from database",
                detail="OHLCV cache only — AI analysis below is running fresh for this visit.",
            )
        else:
            await send_step(
                websocket, phase="data", status="running",
                message="No cached data — downloading OHLCV, fundamentals, and news (may take up to a minute)…",
            )

        try:
            ingest_ohlcv.delay(symbol)
            compute_technical_features.delay(symbol)
            ingest_fundamentals.delay(symbol)
            run_sentiment_pipeline.delay(symbol)
            await send_step(
                websocket, phase="data", status="info",
                message="Background refresh queued for latest prices and news",
            )
        except Exception as e:
            logger.debug("Celery enqueue skipped for %s: %s", symbol, e)

        if not await ensure_symbol_data(symbol):
            await send_step(
                websocket, phase="data", status="error",
                message=f"Could not load market data for {symbol}",
                detail="Check the symbol (e.g. RELIANCE.NS) and try again.",
            )
            await websocket.send_json({
                "type": "error",
                "code": 503,
                "message": f"Could not load market data for {symbol}. Check the symbol and try again.",
            })
            return

        if not had_cache:
            await send_step(
                websocket, phase="data", status="done",
                message="Download complete — price history and features ready",
            )

        await send_step(
            websocket, phase="data", status="done",
            message="Starting fresh multi-agent analysis…",
            detail="Not replaying a previous saved prediction.",
        )

        await stream_analysis(symbol, websocket)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for %s", symbol)
    except Exception as e:
        logger.exception("WebSocket error for %s", symbol)
        try:
            await send_step(
                websocket, phase="data", status="error",
                message="Analysis failed",
                detail=_safe_error_message(e),
            )
            await websocket.send_json({
                "type": "error",
                "code": 500,
                "message": _safe_error_message(e),
            })
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
