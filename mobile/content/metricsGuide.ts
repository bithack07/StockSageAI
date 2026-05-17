/** In-app glossary — every major label/metric shown in StockSage AI (India markets). */

export interface GuideItem {
  term: string;
  explanation: string;
  example?: string;
}

export interface GuideSection {
  id: string;
  title: string;
  intro?: string;
  items: GuideItem[];
}

export const METRICS_GUIDE_SECTIONS: GuideSection[] = [
  {
    id: 'indices',
    title: 'Market indices (Dashboard)',
    intro: 'Live benchmarks for the Indian market. Prices are in INR. Change % is vs the previous close.',
    items: [
      { term: 'Nifty 50', explanation: 'National Stock Exchange index of 50 large Indian companies. Often used as the benchmark for Indian equity returns.', example: 'Symbol: ^NSEI' },
      { term: 'Nifty Bank', explanation: 'Index of major banking stocks. Reflects rate cycles, credit growth, and financial sector sentiment.' },
      { term: 'Nifty IT', explanation: 'Information technology sector index (TCS, Infosys, etc.). Sensitive to USD/INR and US client demand.' },
      { term: 'Nifty Pharma', explanation: 'Pharmaceutical sector index. Driven by US FDA approvals, exports, and domestic healthcare demand.' },
      { term: 'Nifty Auto', explanation: 'Automobile manufacturers index. Tracks passenger and commercial vehicle demand in India.' },
      { term: 'Nifty FMCG', explanation: 'Fast-moving consumer goods index (HUL, ITC, etc.). Often defensive, steadier earnings.' },
      { term: 'Sensex', explanation: 'BSE S&P Bombay Stock Exchange Sensitive Index — 30 large, established companies on the BSE.' },
      { term: 'RSI (on index card)', explanation: 'Relative Strength Index (14-day). Above 70 = often considered overbought; below 30 = oversold. Not a buy/sell signal on its own.', example: 'RSI 55 = neutral momentum' },
      { term: 'Change %', explanation: 'Percentage move from the previous trading session close. Green = up, red = down.' },
    ],
  },
  {
    id: 'market-status',
    title: 'Market status badge',
    items: [
      { term: 'OPEN', explanation: 'NSE regular session (approx. 9:15 AM – 3:30 PM IST, Mon–Fri, excluding holidays).' },
      { term: 'PREOPEN', explanation: 'Pre-open auction window before the regular session (approx. 9:00 – 9:15 AM IST).' },
      { term: 'CLOSED', explanation: 'Outside trading hours, weekend, or exchange holiday. Prices may show last close.' },
    ],
  },
  {
    id: 'stock-quote',
    title: 'Stock price & chart',
    items: [
      { term: 'Symbol (.NS / .BO)', explanation: 'NSE-listed stocks use .NS (e.g. RELIANCE.NS). BSE uses .BO. StockSage defaults to NSE.' },
      { term: 'INFY vs INFY.NS', explanation: 'Same company — stored as INFY.NS. Search and watchlist merge duplicates.' },
      { term: 'Watchlist pre-analysis', explanation: 'AI runs in the background when you add favorites; preview shows on the watchlist.' },
      { term: 'Last price (₹)', explanation: 'Latest traded price in Indian rupees from market data (yfinance / exchange feed).' },
      { term: 'Change %', explanation: 'Day’s percentage change vs previous close.' },
      { term: 'Candlestick chart', explanation: 'Each candle = one day (or selected interval). Green = close higher than open; red = close lower. Shows open, high, low, close (OHLC).' },
    ],
  },
  {
    id: 'how-analysis-works',
    title: 'How StockSage performs analysis',
    intro: 'End-to-end pipeline when you open a stock — from raw market data to a single prediction card.',
    items: [
      {
        term: '1 · Prepare market data',
        explanation:
          'Checks the database for OHLCV, fundamentals, sentiment, and technical features. Missing data is downloaded and pipelines compute indicators.',
      },
      {
        term: '2 · Four parallel agents',
        explanation:
          'Fundamental, Technical, Sentiment, and ML run together via LangGraph. Each returns a small JSON verdict from stored data.',
      },
      {
        term: '3 · Lead analyst',
        explanation:
          'Gemini (or Groq / rules) merges all outputs into direction, conviction, targets, and rationale.',
      },
      {
        term: '4 · Live stream & save',
        explanation:
          'WebSocket step_log updates the Activity log; results are saved to analysis history.',
      },
    ],
  },
  {
    id: 'activity-log',
    title: 'Activity log (analysis progress)',
    intro: 'When you open a stock, the live log shows each step of the pipeline in plain English.',
    items: [
      { term: 'Market data phase', explanation: 'Connects, checks your database for OHLCV and indicators, and downloads missing data if needed.' },
      { term: 'Specialist agents phase', explanation: 'Fundamental, technical, sentiment, and ML run in parallel. ◐ = in progress, ✓ = done.' },
      { term: 'Final prediction phase', explanation: 'Lead analyst (orchestrator) merges all agent outputs into one BULLISH / BEARISH / NEUTRAL view.' },
      { term: 'Saving results', explanation: 'Stores the run so you can reload it later from analysis history.' },
    ],
  },
  {
    id: 'ai-agents',
    title: 'AI agents (analysis stream)',
    intro: 'Specialist models summarise different angles. Outputs are combined into one prediction.',
    items: [
      { term: 'Fundamental agent', explanation: 'Reviews valuation (P/E, P/B), profitability (ROE, ROCE), debt, cash flow, and peers. Verdicts like UNDERVALUED / FAIRLY_VALUED / OVERVALUED.', example: 'Uses data from your database + Groq LLM' },
      { term: 'Technical agent', explanation: 'Reads indicators (RSI, MACD, moving averages, support/resistance) and trend signals like BUY / SELL / NEUTRAL.' },
      { term: 'Sentiment agent', explanation: 'Scores recent news and headlines (FinBERT + news APIs). Labels such as POSITIVE / NEGATIVE / NEUTRAL.' },
      { term: 'ML agent', explanation: 'Machine learning scores from trained models on historical Nifty 50 data — direction probability, LSTM 7-day outlook, optional Prophet forecast.' },
    ],
  },
  {
    id: 'ai-prediction',
    title: 'AI prediction card',
    items: [
      { term: 'BULLISH / BEARISH / NEUTRAL', explanation: 'Overall tilt of the combined analysis for the chosen horizon — not a guaranteed outcome.' },
      { term: 'Conviction (HIGH / MEDIUM / LOW)', explanation: 'How strongly the agents agree. LOW often means mixed signals.' },
      { term: 'Confidence %', explanation: 'Model’s stated confidence in the synthesis (0–100). Higher is not the same as “will profit”.' },
      { term: 'Target price range (₹)', explanation: 'Estimated low–high price band from agents/ML. Treat as scenario, not a promise.' },
      { term: 'Horizon (days)', explanation: 'Typical holding period the analysis assumes (e.g. 7, 14, or 30 days).' },
      { term: 'Rationale', explanation: 'Plain-English summary of why the direction was chosen.' },
      { term: 'Key signals', explanation: 'Bullet points from fundamental, technical, sentiment, and ML inputs.' },
      { term: 'Do not trade if…', explanation: 'Condition that would invalidate the thesis (e.g. break below support). Helps discipline, not a hard rule.' },
    ],
  },
  {
    id: 'ml-models',
    title: 'ML model outputs',
    items: [
      { term: 'Direction model (bullish / bearish / neutral %)', explanation: 'Classifies next move using technical + fundamental features (HistGradientBoosting on Nifty 50 history).' },
      { term: 'LSTM up / down %', explanation: 'Neural network on 30 days of price/volume/indicator patterns; 7-day up probability.' },
      { term: 'Prophet forecast', explanation: 'Time-series forecast of price trend (when model file exists for that symbol).' },
      { term: 'Dir … · LSTM … (mobile tile)', explanation: 'Shortcut: direction model bullish % and LSTM direction on one line.' },
    ],
  },
  {
    id: 'owner-investing',
    title: 'Owner investing · India',
    intro: 'Long-term, Buffett-style checklist for NSE/BSE stocks. All values are estimates — verify with annual reports and BSE/NSE filings.',
    items: [
      { term: 'Intrinsic value band (Low / Mid / High)', explanation: 'Estimated fair value per share in INR from DCF (when FCF available) and earnings × sector fair P/E.', example: 'Mid ₹2,500 = centre of the band' },
      { term: 'Margin of safety (MoS %)', explanation: 'How far current price is below fair value mid. Higher MoS = cheaper vs model (not risk-free).' },
      { term: 'UNDERVALUED / OVERVALUED', explanation: 'Price sits below the low band or above the high band of the model.' },
      { term: 'Quality score (0–100) & grade', explanation: 'Composite of ROE, ROE stability, debt/equity, promoter/insider holding, and growth proxies.' },
      { term: 'vs Nifty 50 & FD (1Y)', explanation: 'Compares stock’s 1-year return to Nifty 50 and an indicative fixed-deposit rate (default ~7% p.a., editable in profile).' },
      { term: 'Owner checklist', explanation: 'Your self-assessment: understand the business, circle of competence, 10-year comfort, moat & management ratings (1–5).' },
      { term: 'Net worth (INR)', explanation: 'Your total investable wealth — used to show each holding as % of net worth (position sizing).' },
      { term: 'Investment thesis', explanation: 'Your written notes: why you bought, moat, management, 10-year view. Saved per holding and versioned on update.' },
      { term: 'Sector allocation %', explanation: 'Share of portfolio value in each sector (IT, Financials, FMCG, etc.). Warnings if one sector or stock is too concentrated.' },
      { term: 'Earnings & AR reminders', explanation: 'Upcoming result dates and annual-report season reminders for watchlist symbols (India FY often ends March).' },
    ],
  },
  {
    id: 'portfolio',
    title: 'Portfolio',
    items: [
      { term: 'Invested', explanation: 'Total amount you paid (quantity × average buy price) for all holdings.' },
      { term: 'Current value', explanation: 'Holdings valued at latest market price.' },
      { term: 'P&L / P&L %', explanation: 'Profit or loss = current value − invested. Percentage is vs invested amount.' },
      { term: 'Avg buy price', explanation: 'Your average cost per share in INR.' },
      { term: 'Quantity', explanation: 'Number of shares held.' },
    ],
  },
  {
    id: 'alerts',
    title: 'Alerts',
    items: [
      { term: 'Price above / below', explanation: 'Notify when last price crosses your threshold (INR).' },
      { term: 'RSI above / below', explanation: 'Notify when 14-day RSI crosses your level (e.g. 70 overbought, 30 oversold).' },
    ],
  },
  {
    id: 'legal',
    title: 'Important notice',
    items: [
      {
        term: 'Not investment advice',
        explanation:
          'StockSage AI provides AI-generated research and tools for informational use. It is not investment advice or a recommendation from a SEBI-registered adviser. Past performance does not guarantee future results. You are responsible for your own decisions.',
      },
    ],
  },
];

export function getSection(id: string): GuideSection | undefined {
  return METRICS_GUIDE_SECTIONS.find((s) => s.id === id);
}
