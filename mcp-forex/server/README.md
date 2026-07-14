# MCP Forex Trading Server

Sistema de trading automatizado para Forex. Un MCP server expone 27 tools que un agente LLM (Claude) consume para analizar mercados y ejecutar operaciones en MetaTrader 5 via XM broker.

## Arquitectura

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  🤖 AGENTE (Claude)  │────▶│  MCP Server (EC2)    │────▶│  MT5 Bridge (VPS)   │
│  Kiro Web            │     │  27 tools            │     │  Flask + MT5        │
│  Decide qué hacer    │◀────│  PostgreSQL          │◀────│  XM Broker (demo)   │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

## Tools (27 total)

### 🔬 Analysis Tools (4) — TradingView TA

| Tool | Descripción | Inputs |
|------|-------------|--------|
| `forex_analysis` | Análisis técnico completo de un par en un timeframe | `symbol`, `timeframe` |
| `forex_multi_timeframe` | Análisis top-down D1→H4→H1 con score de alineación | `symbol` |
| `forex_market_scan` | Escanea pares y rankea oportunidades | `pairs?`, `min_adx?` |
| `get_session_info` | Sesión activa, pares óptimos, volatilidad | — |

### 💰 Trading Tools (7) — MT5 Bridge

| Tool | Descripción | Inputs |
|------|-------------|--------|
| `open_position` | Abrir posición con safety checks + R:R validation | `symbol`, `side`, `lot_size`, `sl_pips`, `tp_pips`, `comment?` |
| `close_position` | Cerrar posición por ticket | `ticket`, `close_reason?` |
| `modify_position` | Modificar SL/TP (breakeven, trailing) | `ticket`, `new_sl?`, `new_tp?` |
| `close_all_positions` | Cerrar todas (o por símbolo) | `symbol?`, `reason?` |
| `get_open_positions` | Posiciones abiertas con PnL live y edad | — |
| `get_account_info` | Balance, equity, margin, leverage | — |
| `get_symbol_info` | Spread, pip value, lot sizes, bid/ask | `symbol` |

### 📈 Smart Tools (4) — Lógica de Negocio

| Tool | Descripción | Inputs |
|------|-------------|--------|
| `calculate_lot_size` | Position sizing por riesgo (% balance / SL) | `symbol`, `sl_pips`, `risk_pct?` |
| `get_daily_target_status` | Progreso hacia el 1% diario | — |
| `should_trade_now` | Validación integral (6 checks) | — |
| `get_optimal_sl_tp` | SL/TP dinámicos basados en ATR | `symbol`, `side`, `strategy?` |

### 📝 Database Tools (9) — PostgreSQL

| Tool | Descripción | Inputs |
|------|-------------|--------|
| `get_trading_settings` | Leer settings por categoría | `category?` |
| `update_trading_setting` | Actualizar un setting en caliente | `key`, `value` |
| `register_trade` | Registrar trade nuevo | `ticket`, `symbol`, `side`, ... |
| `update_trade` | Cerrar trade con exit data | `trade_id`, `exit_price`, `pnl_pips`, `pnl_usd`, `close_reason` |
| `get_trade_history` | Historial con stats | `period?`, `symbol?` |
| `get_daily_pnl` | PnL del día | `date?` |
| `get_performance_stats` | Win rate, PF, drawdown | `period?` |
| `log_hourly_decision` | Auditoría del agente | `trades_opened`, `trades_closed`, ... |
| `get_daily_target_progress` | Progreso hora a hora | — |

### ⚙️ System Tools (3) — Salud y Configuración

| Tool | Descripción | Inputs |
|------|-------------|--------|
| `get_safety_rules` | Todas las reglas + estado actual | — |
| `health_check` | Estado de MCP, DB, TradingView, Bridge | — |
| `get_economic_calendar` | Eventos económicos próximos | `hours_ahead?`, `impact?` |

## Setup Local (Desarrollo)

```bash
cd mcp-forex/server

# PostgreSQL
docker compose up -d postgres

# Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Config
cp .env.example .env
# Editar .env con tus valores

# Run
python server.py
```

## Infraestructura

| Componente | Ubicación | URL |
|-----------|-----------|-----|
| MCP Server | EC2 Linux (us-east-1) | `https://mcp-trading.awslearn.cloud/mcp` |
| MT5 Bridge | EC2 Windows (us-east-1) | `http://mt5-bridge.awslearn.cloud:5000` |
| PostgreSQL | Docker (mismo EC2 Linux) | `localhost:5433` |
| Broker | XM Global (demo) | MT5 Server: XMGlobal-MT5 6 |

## Settings (trading_settings)

Configurables en caliente via `update_trading_setting`:

| Categoría | Settings |
|-----------|----------|
| **risk** | max_daily_loss_pct, max_risk_per_trade_pct, max_consecutive_losses, min_rr_ratio, max_drawdown_pct |
| **sizing** | default_lot_size, max_lot_size, max_open_positions |
| **session** | trading_start_utc, trading_end_utc, news_buffer_minutes, max_trade_duration_minutes |
| **pairs** | allowed_pairs |
| **target** | daily_target_pct, reduce_lot_at_pct |
| **filters** | min_adx_entry, min_alignment_score, max_spread_pips |
| **system** | kill_switch, mode, min_balance_usd |

## MT5 Bridge Endpoints

| Method | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/health` | Estado MT5 |
| GET | `/account` | Balance, equity |
| GET | `/positions` | Posiciones abiertas |
| GET | `/symbol/<pair>` | Info del par |
| GET | `/tick/<pair>` | Bid/Ask actual |
| GET | `/candles/<pair>?timeframe=H1&count=100` | Velas OHLCV |
| GET | `/indicator/atr/<pair>?period=14&timeframe=H1` | ATR real |
| GET | `/indicator/spread/<pair>` | Spread real-time |
| POST | `/order/open` | Abrir posición |
| POST | `/order/close` | Cerrar posición |
| POST | `/order/modify` | Modificar SL/TP |
