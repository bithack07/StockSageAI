/** Plain-language description of the StockSage multi-agent analysis pipeline. */

export interface PipelineStep {
  step: number;
  title: string;
  summary: string;
  detail?: string;
}

export const ANALYSIS_PIPELINE_STEPS: PipelineStep[] = [
  {
    step: 1,
    title: 'Prepare market data',
    summary: 'Load or refresh price history, fundamentals, news sentiment, and technical indicators for your symbol.',
    detail:
      'OHLCV candles are stored in the database (from yfinance / exchange feeds). If data is missing, StockSage downloads it, then computes RSI, MACD, moving averages, and support/resistance. Background jobs can refresh prices and news while you wait.',
  },
  {
    step: 2,
    title: 'Run four specialist agents (in parallel)',
    summary: 'Each agent reads the same dataset but answers a different question — like a research desk with four analysts.',
    detail:
      'All four run at the same time to keep latency low. You will see each one start (◐) and finish (✓) in the Activity log.',
  },
  {
    step: 3,
    title: 'Fundamental agent',
    summary: 'Valuation & quality: P/E, P/B, ROE, ROCE, debt, cash flow, DCF, and peer comparison.',
    detail:
      'Outputs a verdict such as UNDERVALUED, FAIRLY_VALUED, or OVERVALUED, plus red flags. Uses structured data from your DB; when configured, a Groq LLM (Llama) interprets the numbers.',
  },
  {
    step: 4,
    title: 'Technical agent',
    summary: 'Price action on 15-minute, 1-hour, and daily charts — trend, momentum, patterns, support/resistance.',
    detail:
      'Produces a signal (e.g. BUY, NEUTRAL, STRONG_SELL) from RSI, MACD, stochastic, and multi-timeframe alignment.',
  },
  {
    step: 5,
    title: 'Sentiment agent',
    summary: 'Recent news headlines and composite sentiment score for the stock.',
    detail:
      'News is scored (FinBERT pipeline + stored sentiment rows). The agent summarises mood and flags high-impact events (earnings, regulatory, etc.).',
  },
  {
    step: 6,
    title: 'ML agent',
    summary: 'Machine learning models trained on Nifty 50 history — not a black box; scores are shown explicitly.',
    detail:
      'Direction classifier (HistGradientBoosting on technical + fundamental features), LSTM 7-day up/down probability, and Prophet forecast when a model file exists for the symbol.',
  },
  {
    step: 7,
    title: 'Lead analyst (orchestrator)',
    summary: 'Combines all agent JSON outputs into one view: direction, conviction, confidence, target range, and rationale.',
    detail:
      'Orchestrated with LangGraph. Prefers Google Gemini for synthesis; falls back to Groq, then a transparent rule-based merge if APIs are unavailable. Mixed signals → lower conviction.',
  },
  {
    step: 8,
    title: 'Save & display',
    summary: 'The full run is stored so you can revisit it; the prediction card and agent tiles update on screen.',
    detail:
      'Results are saved per symbol in the analyses table. The Activity log shows each phase in real time over a secure WebSocket.',
  },
];

export const ANALYSIS_PIPELINE_INTRO =
  'StockSage does not guess from price alone. It prepares data, runs four parallel specialists, then a lead analyst merges their outputs into one actionable summary for Indian equities (NSE/BSE).';
