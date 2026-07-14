# Database Schema — Backend (AdonisJS + PostgreSQL)

## Visión General

El backend expone endpoints REST al frontend para que el usuario configure:
- Conexión a su broker (MT5 Bridge)
- Parámetros de riesgo y sizing
- Pares permitidos y horarios
- Target diario
- Filtros de análisis

El MCP server lee estos settings de la misma DB para operar.

## Diagrama de Relaciones

```
┌────────────┐       ┌──────────────────┐       ┌─────────────────┐
│   users    │──1:1──│  user_settings   │       │     pairs       │
└────────────┘       └──────────────────┘       └─────────────────┘
      │                                                │
      │ 1:1                                            │
      ▼                                                │
┌────────────────────┐                                 │
│  broker_configs    │                                 │
│  (MT5 credentials) │                                 │
└────────────────────┘                                 │
      │                                                │
      │ 1:N                                            │ N:1
      ▼                                                ▼
┌────────────────────┐       ┌─────────────────────────────────────┐
│  trading_settings  │       │              trades                 │
│  (risk, sizing...) │       │  (historial de operaciones)          │
└────────────────────┘       └─────────────────────────────────────┘
                                           │
                                           │ N:1
                                           ▼
                             ┌─────────────────────────────────────┐
                             │          hourly_logs                 │
                             │  (auditoría del agente por hora)     │
                             └─────────────────────────────────────┘

                             ┌─────────────────────────────────────┐
                             │        daily_summaries               │
                             │  (resumen diario de rendimiento)     │
                             └─────────────────────────────────────┘
```

## Tablas

---

### 1. `users` (existente — sin cambios)

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | UUID PK | |
| cognito_sub | VARCHAR(255) | Auth sub de Cognito |
| email | VARCHAR(254) | |
| full_name | VARCHAR(255) | |
| account_currency | VARCHAR(3) | USD default |
| is_active | BOOLEAN | |
| created_at | TIMESTAMPTZ | |

---

### 2. `broker_configs` (NUEVA)

Almacena las credenciales de conexión al broker del usuario.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | UUID PK | |
| user_id | UUID FK→users | Unique |
| broker_name | VARCHAR(50) | "XM", "ICMarkets", "Pepperstone" |
| mt5_login | INTEGER | Número de cuenta MT5 |
| mt5_password_encrypted | TEXT | Password encriptado (AES) |
| mt5_server | VARCHAR(100) | "XMGlobal-MT5 6" |
| bridge_url | VARCHAR(255) | "http://mt5-bridge.awslearn.cloud:5000" |
| bridge_api_key_encrypted | TEXT | API key del bridge encriptada |
| symbol_suffix | VARCHAR(10) | "#" para XM demo |
| account_type | VARCHAR(10) | "demo" / "live" |
| is_active | BOOLEAN | |
| last_connected_at | TIMESTAMPTZ | Última conexión exitosa |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

---

### 3. `trading_settings` (NUEVA — reemplaza user_settings)

Configuración del sistema de trading por usuario. El MCP las lee antes de cada ciclo.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | UUID PK | |
| user_id | UUID FK→users | Unique |
| **Risk** | | |
| max_risk_per_trade_pct | DECIMAL(4,2) | 1.0 (%) |
| max_daily_loss_pct | DECIMAL(4,2) | 1.0 (%) |
| max_drawdown_pct | DECIMAL(4,2) | 5.0 (%) |
| max_consecutive_losses | INTEGER | 5 |
| min_rr_ratio | DECIMAL(4,2) | 1.5 |
| **Sizing** | | |
| default_lot_size | DECIMAL(6,2) | 0.05 |
| max_lot_size | DECIMAL(6,2) | 0.50 |
| max_open_positions | INTEGER | 3 |
| **Session** | | |
| trading_start_utc | VARCHAR(5) | "07:00" |
| trading_end_utc | VARCHAR(5) | "21:00" |
| news_buffer_minutes | INTEGER | 30 |
| max_trade_duration_minutes | INTEGER | 240 |
| **Target** | | |
| daily_target_pct | DECIMAL(4,2) | 1.0 |
| reduce_lot_at_pct | INTEGER | 80 |
| **Filters** | | |
| min_adx_entry | INTEGER | 25 |
| min_alignment_score | INTEGER | 2 |
| max_spread_pips | DECIMAL(4,1) | 3.0 |
| **Pairs** | | |
| allowed_pairs | JSONB | ["EURUSD","GBPUSD",...] |
| **System** | | |
| kill_switch | BOOLEAN | false |
| auto_trading_enabled | BOOLEAN | true |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

---

### 4. `pairs` (existente — agregar campos)

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | SERIAL PK | |
| symbol | VARCHAR(10) | "EURUSD" |
| base_currency | VARCHAR(3) | "EUR" |
| quote_currency | VARCHAR(3) | "USD" |
| pip_size | DECIMAL(10,6) | 0.0001 (o 0.01 para JPY) |
| pip_value_usd | DECIMAL(10,4) | 10.0 |
| spread_avg | DECIMAL(5,2) | 1.5 |
| category | VARCHAR(10) | "major" / "cross" / "exotic" |
| sessions | JSONB | ["london","new_york"] |
| is_active | BOOLEAN | |
| created_at | TIMESTAMPTZ | |

---

### 5. `trades` (refactorizada)

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | UUID PK | |
| user_id | UUID FK→users | |
| pair_id | INTEGER FK→pairs | |
| ticket | BIGINT | MT5 ticket number |
| side | VARCHAR(4) | "BUY" / "SELL" |
| lot_size | DECIMAL(8,2) | |
| entry_price | DECIMAL(12,6) | |
| exit_price | DECIMAL(12,6) | |
| sl_price | DECIMAL(12,6) | |
| tp_price | DECIMAL(12,6) | |
| sl_pips | DECIMAL(8,2) | |
| tp_pips | DECIMAL(8,2) | |
| pnl_pips | DECIMAL(8,2) | |
| pnl_usd | DECIMAL(12,4) | |
| risk_usd | DECIMAL(12,4) | |
| rr_ratio | DECIMAL(6,2) | Target R:R |
| rr_achieved | DECIMAL(6,2) | R:R real logrado |
| status | VARCHAR(15) | "open" / "closed" / "cancelled" |
| close_reason | VARCHAR(30) | "tp_hit","sl_hit","expired","manual","target_reached" |
| comment | TEXT | AI reasoning |
| swap | DECIMAL(8,2) | |
| commission | DECIMAL(8,2) | |
| opened_at | TIMESTAMPTZ | |
| closed_at | TIMESTAMPTZ | |
| holding_minutes | DECIMAL(8,1) | |
| hourly_log_id | UUID FK→hourly_logs | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**Índices:** user_id+status, user_id+closed_at, pair_id+status

---

### 6. `hourly_logs` (NUEVA)

Auditoría de cada ciclo del agente.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | UUID PK | |
| user_id | UUID FK→users | |
| timestamp | TIMESTAMPTZ | |
| utc_hour | SMALLINT | |
| session | VARCHAR(20) | "london","new_york","overlap" |
| balance_usd | DECIMAL(12,2) | |
| equity_usd | DECIMAL(12,2) | |
| open_positions | SMALLINT | |
| trades_opened | SMALLINT | |
| trades_closed | SMALLINT | |
| trades_skipped | SMALLINT | |
| pnl_this_hour | DECIMAL(12,4) | |
| cumulative_pnl_today | DECIMAL(12,4) | |
| symbols_analyzed | JSONB | |
| market_context | TEXT | |
| decision_summary | TEXT | |
| target_progress_pct | DECIMAL(6,2) | |
| created_at | TIMESTAMPTZ | |

**Índices:** user_id+timestamp

---

### 7. `daily_summaries` (NUEVA)

Resumen de rendimiento diario.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | UUID PK | |
| user_id | UUID FK→users | |
| date | DATE | |
| balance_start | DECIMAL(12,2) | |
| balance_end | DECIMAL(12,2) | |
| target_usd | DECIMAL(12,2) | |
| realized_pnl | DECIMAL(12,4) | |
| trades_total | SMALLINT | |
| trades_won | SMALLINT | |
| trades_lost | SMALLINT | |
| win_rate | DECIMAL(5,2) | |
| best_trade_usd | DECIMAL(12,4) | |
| worst_trade_usd | DECIMAL(12,4) | |
| max_drawdown_usd | DECIMAL(12,4) | |
| target_reached | BOOLEAN | |
| created_at | TIMESTAMPTZ | |

**Índices:** user_id+date (unique)

---

## Endpoints API (Backend → Frontend)

### Broker Config
```
GET    /api/v1/broker          → Get broker config
POST   /api/v1/broker          → Create/update broker config
POST   /api/v1/broker/test     → Test connection to bridge
DELETE /api/v1/broker          → Remove broker config
```

### Trading Settings
```
GET    /api/v1/settings/trading    → Get all trading settings
PUT    /api/v1/settings/trading    → Update trading settings
POST   /api/v1/settings/trading/reset → Reset to defaults
```

### Trades
```
GET    /api/v1/trades              → List trades (filterable)
GET    /api/v1/trades/:id          → Get trade detail
GET    /api/v1/trades/open         → Current open positions
GET    /api/v1/trades/stats        → Performance statistics
```

### Daily Summary
```
GET    /api/v1/daily               → List daily summaries
GET    /api/v1/daily/today         → Today's progress
GET    /api/v1/daily/:date         → Specific day
```

### Hourly Logs
```
GET    /api/v1/logs/hourly         → List hourly decisions
GET    /api/v1/logs/hourly/:id     → Detail of one cycle
```

### System
```
GET    /api/v1/system/health       → Health check (bridge + MCP)
POST   /api/v1/system/kill-switch  → Toggle kill switch
GET    /api/v1/system/status       → Overall system status
```

---

## Migraciones a Crear

| # | Archivo | Acción |
|---|---------|--------|
| 0013 | create_broker_configs_table | NUEVA tabla |
| 0014 | create_trading_settings_table | NUEVA tabla (reemplaza user_settings para trading) |
| 0015 | refactor_trades_table | Agregar: ticket, rr_achieved, swap, commission, hourly_log_id |
| 0016 | create_hourly_logs_table | NUEVA tabla |
| 0017 | create_daily_summaries_table | NUEVA tabla |

## Notas

- Las credenciales del broker se guardan **encriptadas** (AES con APP_KEY)
- El MCP server se conecta a la misma DB PostgreSQL para leer settings
- El frontend nunca ve passwords en texto plano — solo confirmación de conexión
- `kill_switch` se puede activar desde el front y el MCP lo respeta inmediatamente
