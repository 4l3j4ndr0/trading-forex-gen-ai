# Tools — Database (Histórico y Tracking)

## Engine: PostgreSQL

- **Servidor:** Contenedor Docker `postgres:16` en el mismo EC2 (o RDS si escala)
- **Conexión:** `asyncpg` o `psycopg2` via variable `DATABASE_URL`
- **Migraciones:** Scripts SQL versionados en `migrations/`

## Variables de Entorno

```env
DATABASE_URL=postgresql://forex_user:forex_pass@localhost:5432/forex_trading
```

## Schema de Base de Datos

### Tabla: `trades`
```sql
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket BIGINT,                              -- MT5 ticket number
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(4) NOT NULL,                   -- BUY / SELL
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
    status VARCHAR(20) DEFAULT 'open',          -- open / closed / cancelled
    close_reason VARCHAR(30),                   -- tp_hit, sl_hit, expired, manual, target_reached
    comment TEXT,                               -- AI reasoning
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    holding_minutes DECIMAL(8, 1),
    hourly_log_id UUID REFERENCES hourly_logs(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_opened_at ON trades(opened_at);
CREATE INDEX idx_trades_closed_at ON trades(closed_at);
```

### Tabla: `hourly_logs`
```sql
CREATE TABLE hourly_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    utc_hour SMALLINT,
    session VARCHAR(20),                        -- london, new_york, overlap
    balance_usd DECIMAL(12, 2),
    equity_usd DECIMAL(12, 2),
    open_positions SMALLINT,
    trades_opened SMALLINT DEFAULT 0,
    trades_closed SMALLINT DEFAULT 0,
    trades_skipped SMALLINT DEFAULT 0,
    pnl_this_hour DECIMAL(12, 4),
    cumulative_pnl_today DECIMAL(12, 4),
    symbols_analyzed JSONB,                     -- Array de pares analizados
    market_context TEXT,                        -- AI summary
    decision_summary TEXT,                      -- What AI decided and why
    target_progress_pct DECIMAL(6, 2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_hourly_logs_timestamp ON hourly_logs(timestamp);
CREATE INDEX idx_hourly_logs_date ON hourly_logs((timestamp::date));
```

### Tabla: `daily_summary`
```sql
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
```

### Tabla: `economic_events` (cache del calendario)
```sql
CREATE TABLE economic_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_time TIMESTAMPTZ NOT NULL,
    currency VARCHAR(5) NOT NULL,
    event_name VARCHAR(200) NOT NULL,
    impact VARCHAR(10) NOT NULL,                -- high, medium, low
    forecast VARCHAR(30),
    previous VARCHAR(30),
    actual VARCHAR(30),
    fetched_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_events_time ON economic_events(event_time);
CREATE INDEX idx_events_impact ON economic_events(impact);
```

### Tabla: `trading_settings`
```sql
CREATE TABLE trading_settings (
    key VARCHAR(50) PRIMARY KEY,
    value VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(30) NOT NULL,              -- risk, sizing, session, pairs, system
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Valores iniciales
INSERT INTO trading_settings (key, value, description, category) VALUES
-- Risk Management
('max_daily_loss_pct', '1.0', 'Max pérdida diaria como % del balance', 'risk'),
('max_risk_per_trade_pct', '1.0', 'Max riesgo por trade como % del balance', 'risk'),
('max_consecutive_losses', '5', 'Pérdidas consecutivas antes de pausa', 'risk'),
('min_rr_ratio', '1.5', 'Ratio riesgo:beneficio mínimo para entrar', 'risk'),
('max_drawdown_pct', '5.0', 'Drawdown máximo antes de kill switch', 'risk'),

-- Position Sizing
('default_lot_size', '0.05', 'Lot size por defecto si no se calcula', 'sizing'),
('max_lot_size', '0.50', 'Lot size máximo permitido', 'sizing'),
('max_open_positions', '3', 'Máximo de posiciones simultáneas', 'sizing'),

-- Session & Timing
('trading_start_utc', '07:00', 'Hora inicio de operación (UTC)', 'session'),
('trading_end_utc', '21:00', 'Hora fin de operación (UTC)', 'session'),
('news_buffer_minutes', '30', 'Minutos antes/después de news sin operar', 'session'),
('max_trade_duration_minutes', '240', 'Duración máxima de un trade en minutos', 'session'),

-- Pairs
('allowed_pairs', 'EURUSD,GBPUSD,USDJPY,AUDUSD,USDCAD,EURGBP', 'Pares permitidos', 'pairs'),

-- Target
('daily_target_pct', '1.0', 'Target diario como % del balance', 'target'),
('reduce_lot_at_pct', '80', 'Reducir lot cuando se alcance este % del target', 'target'),

-- Analysis Filters
('min_adx_entry', '25', 'ADX mínimo para considerar entrada', 'filters'),
('min_alignment_score', '2', 'Score mínimo de alineación de timeframes', 'filters'),
('max_spread_pips', '3.0', 'Spread máximo aceptable en pips', 'filters'),

-- System
('kill_switch', 'false', 'Emergencia: bloquea todas las operaciones', 'system'),
('mode', 'demo', 'Modo de operación: demo / live', 'system'),
('min_balance_usd', '500', 'Balance mínimo para operar', 'system');
```

---

## Tool 1: `register_trade`

**Propósito:** Registrar un trade nuevo en la base de datos.

**Inputs:**
| Param | Tipo | Descripción |
|-------|------|-------------|
| `ticket` | int | MT5 ticket |
| `symbol` | str | Par |
| `side` | str | BUY/SELL |
| `lot_size` | float | Lotes |
| `entry_price` | float | Precio de entrada |
| `sl_price` | float | Stop Loss |
| `tp_price` | float | Take Profit |
| `sl_pips` | float | SL en pips |
| `tp_pips` | float | TP en pips |
| `risk_usd` | float | Riesgo en USD |
| `comment` | str | Razón del trade |

**Output:**
```json
{
  "trade_id": "uuid-xxx",
  "registered": true
}
```

---

## Tool 2: `update_trade`

**Propósito:** Actualizar un trade cuando se cierra.

**Inputs:**
| Param | Tipo | Descripción |
|-------|------|-------------|
| `trade_id` | str | UUID del trade |
| `exit_price` | float | Precio de cierre |
| `pnl_pips` | float | PnL en pips |
| `pnl_usd` | float | PnL en USD |
| `close_reason` | str | Razón del cierre |

**Output:**
```json
{
  "updated": true,
  "holding_minutes": 45.2
}
```

---

## Tool 3: `get_trade_history`

**Propósito:** Historial de trades cerrados con filtros.

**Inputs:**
| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `period` | str | "today" | "today", "yesterday", "7d", "30d", "all" |
| `symbol` | str | null | Filtrar por par |

**Output:**
```json
{
  "period": "today",
  "count": 4,
  "trades": [
    {
      "trade_id": "uuid-1",
      "symbol": "EURUSD",
      "side": "BUY",
      "pnl_pips": 25.3,
      "pnl_usd": 12.65,
      "rr_achieved": 1.8,
      "holding_minutes": 38,
      "close_reason": "tp_hit"
    }
  ],
  "stats": {
    "total_pnl_usd": 45.30,
    "total_pnl_pips": 82.5,
    "win_rate": 75.0,
    "avg_rr": 1.65,
    "profit_factor": 3.2
  }
}
```

---

## Tool 4: `get_daily_pnl`

**Propósito:** PnL del día actual (realizado + no realizado).

**Inputs:**
| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `date` | str | null | Fecha específica. Si null = hoy |

**Output:**
```json
{
  "date": "2026-07-13",
  "realized_pnl": 65.30,
  "unrealized_pnl": 12.50,
  "total_pnl": 77.80,
  "trades_closed": 4,
  "trades_open": 1,
  "best_trade": 35.00,
  "worst_trade": -12.50
}
```

---

## Tool 5: `get_performance_stats`

**Propósito:** Métricas de rendimiento agregadas.

**Inputs:**
| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `period` | str | "30d" | "7d", "30d", "90d", "all" |

**Output:**
```json
{
  "period": "30d",
  "total_trades": 85,
  "win_rate": 62.4,
  "profit_factor": 2.1,
  "avg_pnl_per_trade": 8.50,
  "avg_winner": 22.30,
  "avg_loser": -14.80,
  "avg_rr_achieved": 1.51,
  "max_consecutive_wins": 7,
  "max_consecutive_losses": 3,
  "max_drawdown_usd": -85.00,
  "max_drawdown_pct": 0.85,
  "best_day_usd": 145.00,
  "worst_day_usd": -62.00,
  "sharpe_ratio": 1.8,
  "days_target_reached": 18,
  "days_total": 22,
  "consistency_pct": 81.8
}
```

---

## Tool 6: `log_hourly_decision`

**Propósito:** Registrar qué decidió el agente en este ciclo (auditoría).

**Inputs:**
| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `trades_opened` | int | 0 | Trades abiertos este ciclo |
| `trades_closed` | int | 0 | Trades cerrados |
| `trades_skipped` | int | 0 | Oportunidades descartadas |
| `pnl_this_hour` | float | null | PnL realizado esta hora |
| `symbols_analyzed` | str | null | JSON de pares analizados |
| `market_context` | str | null | Resumen del mercado |
| `decision_summary` | str | null | Qué decidió y por qué |

**Output:**
```json
{
  "logged": true,
  "log_id": "uuid-xxx",
  "timestamp": "2026-07-13T20:00:00Z"
}
```

---

## Tool 7: `get_daily_target_progress`

**Propósito:** Progreso hora a hora hacia el target diario.

**Inputs:** Ninguno

**Output:**
```json
{
  "date": "2026-07-13",
  "target_usd": 100.00,
  "progress": [
    {"hour": 7, "pnl_cumulative": 0, "trades": 0},
    {"hour": 8, "pnl_cumulative": 15.30, "trades": 1},
    {"hour": 9, "pnl_cumulative": 15.30, "trades": 0},
    {"hour": 10, "pnl_cumulative": 42.80, "trades": 1},
    {"hour": 11, "pnl_cumulative": 42.80, "trades": 0},
    {"hour": 12, "pnl_cumulative": 65.30, "trades": 2}
  ],
  "current_pct": 65.3,
  "hours_remaining": 9,
  "avg_pnl_per_hour": 10.88
}
```

---

## Tool 8: `get_trading_settings`

**Propósito:** Obtener todos los settings de operación (o filtrados por categoría).

**Inputs:**
| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `category` | str | null | Filtrar: "risk", "sizing", "session", "pairs", "target", "filters", "system". Si null = todos |

**Output:**
```json
{
  "settings": {
    "risk": {
      "max_daily_loss_pct": 1.0,
      "max_risk_per_trade_pct": 1.0,
      "max_consecutive_losses": 5,
      "min_rr_ratio": 1.5,
      "max_drawdown_pct": 5.0
    },
    "sizing": {
      "default_lot_size": 0.05,
      "max_lot_size": 0.50,
      "max_open_positions": 3
    },
    "session": {
      "trading_start_utc": "07:00",
      "trading_end_utc": "21:00",
      "news_buffer_minutes": 30,
      "max_trade_duration_minutes": 240
    },
    "pairs": {
      "allowed_pairs": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "EURGBP"]
    },
    "target": {
      "daily_target_pct": 1.0,
      "reduce_lot_at_pct": 80
    },
    "filters": {
      "min_adx_entry": 25,
      "min_alignment_score": 2,
      "max_spread_pips": 3.0
    },
    "system": {
      "kill_switch": false,
      "mode": "demo",
      "min_balance_usd": 500
    }
  }
}
```

---

## Tool 9: `update_trading_setting`

**Propósito:** Actualizar un setting específico.

**Inputs:**
| Param | Tipo | Descripción |
|-------|------|-------------|
| `key` | str | Key del setting (ej: "max_lot_size", "kill_switch") |
| `value` | str | Nuevo valor |

**Output:**
```json
{
  "updated": true,
  "key": "max_lot_size",
  "old_value": "0.50",
  "new_value": "0.30",
  "category": "sizing"
}
```

**Nota:** El agente puede usar este tool para activar el kill switch si detecta condiciones peligrosas. También permite ajustar parámetros sin redeploy.
