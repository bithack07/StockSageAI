-- StockSage AI — PostgreSQL Schema (Supabase compatible)

-- Users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- OHLCV (TimescaleDB hypertable for fast time-series queries)
CREATE TABLE IF NOT EXISTS ohlcv (
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    open NUMERIC(12,4),
    high NUMERIC(12,4),
    low NUMERIC(12,4),
    close NUMERIC(12,4),
    volume BIGINT,
    PRIMARY KEY (symbol, date)
);
-- Run if TimescaleDB is available: SELECT create_hypertable('ohlcv', 'date');

-- Technical features (pre-computed indicators)
CREATE TABLE IF NOT EXISTS technical_features (
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    timeframe TEXT NOT NULL DEFAULT '1d',
    rsi NUMERIC(6,2),
    macd NUMERIC(10,4),
    macd_signal NUMERIC(10,4),
    bb_upper NUMERIC(12,4),
    bb_lower NUMERIC(12,4),
    atr NUMERIC(10,4),
    ema20 NUMERIC(12,4),
    ema50 NUMERIC(12,4),
    ema200 NUMERIC(12,4),
    stoch_k NUMERIC(8,4),
    stoch_d NUMERIC(8,4),
    vwap NUMERIC(12,4),
    patterns_json JSONB,
    sr_zones_json JSONB,
    PRIMARY KEY (symbol, date, timeframe)
);

-- Fundamentals
CREATE TABLE IF NOT EXISTS fundamentals (
    symbol TEXT PRIMARY KEY,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    pe_ratio NUMERIC(8,2),
    pb_ratio NUMERIC(8,2),
    ev_ebitda NUMERIC(8,2),
    roe NUMERIC(8,4),
    roce NUMERIC(8,4),
    debt_equity NUMERIC(8,4),
    fcf BIGINT,
    dcf_intrinsic NUMERIC(12,2),
    market_cap BIGINT,
    promoter_pct NUMERIC(5,2),
    pledge_pct NUMERIC(5,2),
    ratios_json JSONB
);

-- Sentiment
CREATE TABLE IF NOT EXISTS sentiment (
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    composite_score NUMERIC(5,4),
    article_count INT,
    top_news_json JSONB,
    event_flags_json JSONB,
    PRIMARY KEY (symbol, date)
);

-- Portfolios and holdings
CREATE TABLE IF NOT EXISTS portfolios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL DEFAULT 'My Portfolio'
);

CREATE TABLE IF NOT EXISTS holdings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    quantity NUMERIC(12,4),
    avg_buy_price NUMERIC(12,4),
    buy_date DATE
);

-- Watchlist
CREATE TABLE IF NOT EXISTS watchlist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, symbol)
);

-- Alerts
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    symbol TEXT,
    condition TEXT,
    threshold NUMERIC(12,4),
    is_active BOOLEAN DEFAULT TRUE,
    triggered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Analysis history
CREATE TABLE IF NOT EXISTS analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    symbol TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    fundamental_json JSONB,
    technical_json JSONB,
    sentiment_json JSONB,
    prediction_json JSONB,
    chroma_doc_id TEXT
);

-- Tracked tickers (for background pipeline scheduling)
CREATE TABLE IF NOT EXISTS tracked_tickers (
    symbol TEXT PRIMARY KEY,
    company_name TEXT,
    exchange TEXT DEFAULT 'NSE',
    added_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol ON ohlcv(symbol);
CREATE INDEX IF NOT EXISTS idx_tech_symbol_date ON technical_features(symbol, date DESC);
CREATE INDEX IF NOT EXISTS idx_analyses_user ON analyses(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sentiment_symbol_date ON sentiment(symbol, date DESC);
CREATE INDEX IF NOT EXISTS idx_holdings_portfolio ON holdings(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_alerts_user_active ON alerts(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_watchlist_user ON watchlist(user_id);

-- Value investor profile (India: net worth in INR, FD benchmark rate)
CREATE TABLE IF NOT EXISTS user_investor_profile (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    net_worth_inr NUMERIC(14,2),
    annual_fd_rate_pct NUMERIC(5,2) DEFAULT 7.0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Investment thesis per holding (owner's notes)
CREATE TABLE IF NOT EXISTS holding_thesis (
    holding_id UUID PRIMARY KEY REFERENCES holdings(id) ON DELETE CASCADE,
    thesis_text TEXT,
    moat_notes TEXT,
    management_notes TEXT,
    ten_year_thesis TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Owner checklist per user + NSE symbol
CREATE TABLE IF NOT EXISTS symbol_owner_checklist (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    moat_rating INT CHECK (moat_rating BETWEEN 1 AND 5),
    management_rating INT CHECK (management_rating BETWEEN 1 AND 5),
    circle_of_competence BOOLEAN DEFAULT FALSE,
    understand_business BOOLEAN DEFAULT FALSE,
    comfortable_10y BOOLEAN DEFAULT FALSE,
    notes TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, symbol)
);
