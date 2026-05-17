-- Local SQLite schema for offline cache (Tauri desktop)
CREATE TABLE IF NOT EXISTS local_quotes (
    symbol TEXT PRIMARY KEY,
    price REAL,
    change_pct REAL,
    fetched_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS local_analyses (
    id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    prediction_json TEXT
);

CREATE TABLE IF NOT EXISTS local_watchlist (
    symbol TEXT PRIMARY KEY,
    added_at TEXT DEFAULT (datetime('now'))
);
