-- Hourly decision logs (auditoría del agente)
CREATE TABLE hourly_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    utc_hour SMALLINT,
    session VARCHAR(20),
    balance_usd DECIMAL(12, 2),
    equity_usd DECIMAL(12, 2),
    open_positions SMALLINT,
    trades_opened SMALLINT DEFAULT 0,
    trades_closed SMALLINT DEFAULT 0,
    trades_skipped SMALLINT DEFAULT 0,
    pnl_this_hour DECIMAL(12, 4),
    cumulative_pnl_today DECIMAL(12, 4),
    symbols_analyzed JSONB,
    market_context TEXT,
    decision_summary TEXT,
    target_progress_pct DECIMAL(6, 2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_hourly_logs_timestamp ON hourly_logs(timestamp);
CREATE INDEX idx_hourly_logs_date ON hourly_logs(CAST(timestamp AT TIME ZONE 'UTC' AS DATE));

-- Daily summary (resumen al final del día)
CREATE TABLE daily_summary (
    date DATE PRIMARY KEY,
    balance_start DECIMAL(12, 2),
    balance_end DECIMAL(12, 2),
    target_usd DECIMAL(12, 2),
    realized_pnl DECIMAL(12, 4),
    trades_total SMALLINT,
    trades_won SMALLINT,
    trades_lost SMALLINT,
    win_rate DECIMAL(5, 2),
    best_trade_usd DECIMAL(12, 4),
    worst_trade_usd DECIMAL(12, 4),
    max_drawdown_usd DECIMAL(12, 4),
    target_reached BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
