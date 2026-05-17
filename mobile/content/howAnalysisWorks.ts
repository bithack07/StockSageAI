/** Plain-language description of the StockSage multi-agent analysis pipeline. */

export interface PipelineStep {
  step: number;
  title: string;
  summary: string;
  detail?: string;
}

export const ANALYSIS_PIPELINE_INTRO =
  'StockSage does not guess from price alone. It prepares data, runs four parallel specialists, then a lead analyst merges their outputs into one actionable summary for Indian equities (NSE/BSE).';

export const ANALYSIS_PIPELINE_STEPS: PipelineStep[] = [
  {
    step: 1,
    title: 'Prepare market data',
    summary: 'Load or refresh price history, fundamentals, news sentiment, and technical indicators for your symbol.',
    detail:
      'OHLCV candles are stored in the database. If data is missing, StockSage downloads it, then computes RSI, MACD, moving averages, and support/resistance.',
  },
  {
    step: 2,
    title: 'Run four specialist agents (in parallel)',
    summary: 'Each agent reads the same dataset but answers a different question.',
    detail: 'All four run at the same time. Watch the Activity log for ◐ running and ✓ done.',
  },
  {
    step: 3,
    title: 'Fundamental agent',
    summary: 'Valuation & quality: P/E, ROE, debt, cash flow, DCF, and peers → UNDERVALUED / FAIR / OVERVALUED.',
  },
  {
    step: 4,
    title: 'Technical agent',
    summary: '15m, 1H, and daily charts — trend, momentum, support/resistance → BUY / NEUTRAL / SELL style signal.',
  },
  {
    step: 5,
    title: 'Sentiment agent',
    summary: 'Recent news and composite sentiment — mood and event flags.',
  },
  {
    step: 6,
    title: 'ML agent',
    summary: 'Direction model, LSTM 7-day probability, Prophet forecast (when available).',
  },
  {
    step: 7,
    title: 'Lead analyst (orchestrator)',
    summary: 'Merges all outputs into direction, conviction, confidence, targets, and plain-English rationale.',
    detail: 'Gemini → Groq → rule-based fallback if APIs are off.',
  },
  {
    step: 8,
    title: 'Save & display',
    summary: 'Run stored for history; prediction card and agent tiles update on screen.',
  },
];
