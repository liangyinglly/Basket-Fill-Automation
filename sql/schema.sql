PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS basket_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    basket_id TEXT,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_basket_runs_status ON basket_runs(status);

CREATE TABLE IF NOT EXISTS basket_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    line_id TEXT NOT NULL,
    requested_name TEXT NOT NULL,
    quantity REAL NOT NULL,
    unit TEXT NOT NULL,
    normalized_name TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (run_id) REFERENCES basket_runs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_basket_requests_run_id ON basket_requests(run_id);

CREATE TABLE IF NOT EXISTS basket_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL,
    retailer_name TEXT NOT NULL,
    retailer_product_id TEXT NOT NULL,
    product_title TEXT NOT NULL,
    price_cents INTEGER,
    confidence REAL NOT NULL,
    rationale TEXT,
    selected INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (request_id) REFERENCES basket_requests(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_basket_matches_request_id ON basket_matches(request_id);

CREATE TABLE IF NOT EXISTS search_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    retailer_name TEXT NOT NULL,
    query TEXT NOT NULL,
    response_json TEXT NOT NULL,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (retailer_name, query)
);

CREATE INDEX IF NOT EXISTS idx_search_cache_expires_at ON search_cache(expires_at);
