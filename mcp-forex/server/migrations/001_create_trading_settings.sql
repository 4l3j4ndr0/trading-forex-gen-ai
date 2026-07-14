-- Trading settings (configurable sin redeploy)
CREATE TABLE trading_settings (
    key VARCHAR(50) PRIMARY KEY,
    value VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(30) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Risk Management
INSERT INTO trading_settings (key, value, description, category) VALUES
('max_daily_loss_pct', '1.0', 'Max pérdida diaria como % del balance', 'risk'),
('max_risk_per_trade_pct', '1.0', 'Max riesgo por trade como % del balance', 'risk'),
('max_consecutive_losses', '5', 'Pérdidas consecutivas antes de pausa', 'risk'),
('min_rr_ratio', '1.5', 'Ratio riesgo:beneficio mínimo para entrar', 'risk'),
('max_drawdown_pct', '5.0', 'Drawdown máximo antes de kill switch', 'risk');

-- Position Sizing
INSERT INTO trading_settings (key, value, description, category) VALUES
('default_lot_size', '0.05', 'Lot size por defecto', 'sizing'),
('max_lot_size', '0.50', 'Lot size máximo permitido', 'sizing'),
('max_open_positions', '3', 'Máximo de posiciones simultáneas', 'sizing');

-- Session & Timing
INSERT INTO trading_settings (key, value, description, category) VALUES
('trading_start_utc', '07:00', 'Hora inicio de operación (UTC)', 'session'),
('trading_end_utc', '21:00', 'Hora fin de operación (UTC)', 'session'),
('news_buffer_minutes', '30', 'Minutos antes/después de news sin operar', 'session'),
('max_trade_duration_minutes', '240', 'Duración máxima de un trade', 'session');

-- Pairs
INSERT INTO trading_settings (key, value, description, category) VALUES
('allowed_pairs', 'EURUSD,GBPUSD,USDJPY,AUDUSD,USDCAD,EURGBP', 'Pares permitidos', 'pairs');

-- Target
INSERT INTO trading_settings (key, value, description, category) VALUES
('daily_target_pct', '1.0', 'Target diario como % del balance', 'target'),
('reduce_lot_at_pct', '80', 'Reducir lot cuando se alcance este % del target', 'target');

-- Analysis Filters
INSERT INTO trading_settings (key, value, description, category) VALUES
('min_adx_entry', '25', 'ADX mínimo para considerar entrada', 'filters'),
('min_alignment_score', '2', 'Score mínimo de alineación de timeframes', 'filters'),
('max_spread_pips', '3.0', 'Spread máximo aceptable en pips', 'filters');

-- System
INSERT INTO trading_settings (key, value, description, category) VALUES
('kill_switch', 'false', 'Emergencia: bloquea todas las operaciones', 'system'),
('mode', 'demo', 'Modo de operación: demo / live', 'system'),
('min_balance_usd', '500', 'Balance mínimo para operar', 'system');
