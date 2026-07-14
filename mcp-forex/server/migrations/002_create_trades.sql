-- Trades table
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket BIGINT,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(4) NOT NULL,
    lot_size DECIMAL(10, 4) NOT NULL,
    entry_price DECIMAL(12, 6) NOT NULL,
    exit_price DECIMAL(12, 6),
    sl_price DECIMAL(12, 6),
    tp_price DECIMAL(12, 6),
    sl_pips DECIMAL(8, 2),
    tp_pips DECIMAL(8, 2),
    pnl_pips DECIMAL(8, 2),
    pnl_usd DECIMAL(12, 4),
    risk_usd DECIMAL(12, 4),
    rr_ratio DECIMAL(6, 2),
    status VARCHAR(20) DEFAULT 'open',
    close_reason VARCHAR(30),
    comment TEXT,
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    holding_minutes DECIMAL(8, 1),
    hourly_log_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_opened_at ON trades(opened_at);
CREATE INDEX idx_trades_closed_at ON trades(closed_at);
