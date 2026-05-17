"""LangGraph StateGraph — orchestrates all agents in parallel then synthesises."""
import asyncio
import json
import logging
from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.agents.analysis_log import agent_result_summary, send_step
from app.agents.fundamental import run_fundamental_agent
from app.agents.technical import run_technical_agent
from app.agents.sentiment import run_sentiment_agent
from app.agents.prediction import run_orchestrator_synthesis
from app.config import settings
from app.pipelines.ml_inference import get_ml_scores

logger = logging.getLogger(__name__)

_AGENT_START_MESSAGES = {
    "fundamental": "Reviewing P/E, ROE, debt, cash flow, and peer comparison…",
    "technical": "Reading RSI, MACD, trends, and support/resistance on 15m, 1H, and daily charts…",
    "sentiment": "Scoring recent news headlines and market mood…",
    "ml": "Running direction model, LSTM (7-day), and Prophet forecast…",
}


class AnalysisState(TypedDict):
    symbol: str
    fundamental_output: dict
    technical_output: dict
    sentiment_output: dict
    ml_scores: dict
    prediction: dict
    messages: list


async def _run_ml_scores(state: AnalysisState, websocket) -> AnalysisState:
    symbol = state["symbol"]
    await send_step(
        websocket, phase="agents", agent="ml", status="running",
        message=_AGENT_START_MESSAGES["ml"],
    )
    scores = await asyncio.get_event_loop().run_in_executor(None, get_ml_scores, symbol)
    await send_step(
        websocket, phase="agents", agent="ml", status="done",
        message=agent_result_summary("ml", scores),
    )
    return {"ml_scores": scores}


async def _run_agent_logged(
    websocket,
    agent_key: str,
    state: AnalysisState,
    runner,
) -> dict:
    """Run one specialist agent and emit start/done step logs."""
    await send_step(
        websocket, phase="agents", agent=agent_key, status="running",
        message=_AGENT_START_MESSAGES[agent_key],
    )
    output_key = {
        "fundamental": "fundamental_output",
        "technical": "technical_output",
        "sentiment": "sentiment_output",
    }[agent_key]

    try:
        result = await runner(dict(state))
    except Exception as exc:
        logger.error("%s agent failed for %s: %s", agent_key, state["symbol"], exc)
        await send_step(
            websocket, phase="agents", agent=agent_key, status="error",
            message=f"{agent_key.title()} agent failed",
            detail=str(exc) if settings.debug else None,
        )
        return {}

    output = result.get(output_key) or {}
    if not output or (agent_key == "technical" and not output.get("signal")):
        await send_step(
            websocket, phase="agents", agent=agent_key, status="error",
            message=f"{agent_key.title()} agent returned no output",
            detail=output.get("error") or output.get("llm_error") if isinstance(output, dict) else None,
        )
        return {}

    await send_step(
        websocket, phase="agents", agent=agent_key, status="done",
        message=agent_result_summary(agent_key, output),
    )
    return {output_key: output}


async def _run_parallel_agents(state: AnalysisState, websocket) -> AnalysisState:
    """Run fundamental, technical, sentiment, and ML agents concurrently."""
    await send_step(
        websocket, phase="agents", status="info",
        message="Launching 4 specialist agents in parallel (fundamental, technical, sentiment, ML)…",
    )

    results = await asyncio.gather(
        _run_agent_logged(websocket, "fundamental", state, run_fundamental_agent),
        _run_agent_logged(websocket, "technical", state, run_technical_agent),
        _run_agent_logged(websocket, "sentiment", state, run_sentiment_agent),
        _run_ml_scores(dict(state), websocket),
        return_exceptions=True,
    )

    for result in results:
        if isinstance(result, Exception):
            logger.error("Agent error: %s", result)
            continue
        if isinstance(result, dict):
            state.update(result)

    completed = sum(
        1 for k in ("fundamental_output", "technical_output", "sentiment_output", "ml_scores")
        if state.get(k)
    )
    await send_step(
        websocket, phase="agents", status="done",
        message=f"All agents finished ({completed}/4 returned results)",
    )
    return state


def build_analysis_graph(websocket) -> StateGraph:
    graph = StateGraph(AnalysisState)

    async def parallel_node(state: AnalysisState) -> AnalysisState:
        return await _run_parallel_agents(state, websocket)

    async def orchestrator_node(state: AnalysisState) -> AnalysisState:
        await send_step(
            websocket, phase="synthesis", agent="orchestrator", status="running",
            message="Lead analyst combining fundamental, technical, sentiment, and ML signals…",
        )
        result = await run_orchestrator_synthesis(dict(state))
        prediction = result.get("prediction", {})
        if prediction:
            direction = prediction.get("direction", "—")
            conviction = prediction.get("conviction", "")
            conf = prediction.get("confidence_pct", "")
            detail = f"{conviction} conviction · {conf}% confidence" if conviction else None
            await send_step(
                websocket, phase="synthesis", agent="orchestrator", status="done",
                message=f"Final view: {direction}",
                detail=detail,
            )
        state.update(result)
        return state

    graph.add_node("parallel_agents", parallel_node)
    graph.add_node("orchestrator", orchestrator_node)
    graph.set_entry_point("parallel_agents")
    graph.add_edge("parallel_agents", "orchestrator")
    graph.add_edge("orchestrator", END)
    return graph.compile()


async def stream_analysis(symbol: str, websocket):
    """Stream agent analysis over WebSocket with user-friendly step logs."""
    import uuid
    from app.db import get_db
    from app.services.symbols import canonical_symbol

    symbol = canonical_symbol(symbol)

    await send_step(
        websocket, phase="agents", status="info",
        message=f"Starting multi-agent analysis for {symbol}",
        detail="New run — results will replace any prior saved analysis for this symbol.",
    )

    graph = build_analysis_graph(websocket)
    state: AnalysisState = {
        "symbol": symbol,
        "fundamental_output": {},
        "technical_output": {},
        "sentiment_output": {},
        "ml_scores": {},
        "prediction": {},
        "messages": [],
    }

    try:
        async for event in graph.astream(state):
            node = list(event.keys())[0] if event else None
            node_data = event.get(node, {}) if node else {}

            if node == "parallel_agents":
                for agent_name in ("fundamental_output", "technical_output", "sentiment_output", "ml_scores"):
                    if agent_name in node_data:
                        agent = agent_name.replace("_output", "").replace("_scores", "")
                        await websocket.send_json({
                            "type": "agent_complete",
                            "agent": agent,
                            "output_json": node_data[agent_name],
                        })
                state.update(node_data)
            elif node == "orchestrator":
                if node_data.get("prediction"):
                    await websocket.send_json({
                        "type": "prediction_complete",
                        **node_data["prediction"],
                    })
                    state.update(node_data)

        try:
            analysis_id = str(uuid.uuid4())
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute(
                    """INSERT INTO analyses (id, symbol, fundamental_json, technical_json, sentiment_json, prediction_json)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (
                        analysis_id, symbol,
                        json.dumps(state.get("fundamental_output", {})),
                        json.dumps(state.get("technical_output", {})),
                        json.dumps(state.get("sentiment_output", {})),
                        json.dumps(state.get("prediction", {})),
                    ),
                )
            await send_step(
                websocket, phase="save", status="done",
                message="Analysis saved — you can revisit it from history",
                detail=f"ID {analysis_id[:8]}…",
            )
            await websocket.send_json({"type": "analysis_saved", "analysis_id": analysis_id, "silent": True})
        except Exception as db_err:
            logger.error("Failed to save analysis: %s", db_err)
            await send_step(
                websocket, phase="save", status="error",
                message="Could not save analysis to database",
                detail=str(db_err),
            )

    except Exception as e:
        logger.error("stream_analysis error for %s: %s", symbol, e)
        await send_step(
            websocket, phase="agents", status="error",
            message="Analysis stopped due to an error",
            detail=str(e),
        )
        await websocket.send_json({"type": "error", "code": 500, "message": str(e)})
