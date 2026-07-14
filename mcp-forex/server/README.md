# MCP Forex Trading Server

Sistema de trading automatizado para Forex. Un MCP server expone 25 tools que un agente LLM (Claude) consume para analizar mercados y ejecutar operaciones en MetaTrader 5 via un broker (XM).

## Arquitectura

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  🤖 AGENTE (Claude)  │────▶│  MCP Server          │────▶│  MT5 Bridge (VPS)   │
│  Kiro Web / API      │     │  25 tools            │     │  Flask + MT5        │
│  Decide qué hacer    │◀────│  PostgreSQL (RDS)    │◀────│  XM Broker          │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

## Tools (25 total)

### 🔬 Analysis Tools (4) — TradingView TA

| Tool | Descripción |
|------|-------------|
| `forex_analysis` | Análisis técnico completo (RSI, MACD, ADX, EMAs, Bollinger) de un par en un timeframe |
| `forex_multi_timeframe` | Análisis top-down D1→H4→H1 con score de alineación (-3 a +3) |
| `forex_market_scan` | Escanea múltiples pares y rankea oportunidades por ADX y alineación |
| `get_session_info` | Sesión activa (London/NY/Tokyo), volatilidad, pares óptimos |

### 💰 Trading Tools (7) — MT5 Bridge

| Tool | Descripción |
|------|-------------|
| `open_position` | Abre posición con safety checks completos (kill switch, horario, max positions, R:R, daily loss) |
| `close_position` | Cierra posición por ticket MT5, calcula PnL y registra en BD |
| `modify_position` | Modifica SL/TP de una posición abierta (breakeven, trailing) |
| `close_all_positions` | Cierra todas las posiciones abiertas (o filtradas por par) |
| `get_open_positions` | Lista posiciones abiertas con PnL live, edad, y flag de expiración |
| `get_account_info` | Balance, equity, margin, leverage del broker en tiempo real |
| `get_symbol_info` | Spread, pip value, lot sizes, bid/ask de un par |

### 📈 Smart Tools (4) — Lógica de Negocio

| Tool | Descripción |
|------|-------------|
| `calculate_lot_size` | Position sizing dinámico: (balance × risk%) / (SL pips × pip value) |
| `get_daily_target_status` | Progreso hacia el target diario (1%), recomendación CONTINUE/STOP |
| `should_trade_now` | Validación integral: kill switch, horario, daily loss, max positions, pérdidas consecutivas |
| `get_optimal_sl_tp` | SL/TP dinámicos basados en ATR proxy, con estrategias conservative/balanced/aggressive |

### 📝 Database Tools (7) — PostgreSQL

| Tool | Descripción |
|------|-------------|
| `register_trade` | Registra un trade abierto en la BD con todos los datos |
| `update_trade` | Cierra un trade con exit price, PnL, razón de cierre |
| `get_trade_history` | Historial de trades cerrados con filtros (period, symbol) y stats |
| `get_daily_pnl` | PnL realizado del día (best/worst trade, trades abiertos) |
| `get_performance_stats` | Win rate, profit factor, max drawdown, rachas consecutivas |
| `log_hourly_decision` | Auditoría: qué decidió el agente en cada ciclo horario |
| `get_daily_target_progress` | Progreso hora a hora hacia el target con balance real |

### ⚙️ System Tools (3) — Salud y Configuración

| Tool | Descripción |
|------|-------------|
| `get_safety_rules` | Todas las reglas activas + estado actual (posiciones, PnL, rachas) |
| `health_check` | Estado de MCP, BD, TradingView y MT5 Bridge |
| `get_economic_calendar` | Eventos económicos próximos (placeholder — listo para scraper) |

## Configuración

El MCP recibe por `.env`:

```env
DATABASE_URL=postgresql://...        # Misma BD que el backend
MT5_BRIDGE_URL=http://mt5-bridge.awslearn.cloud:5000
MT5_BRIDGE_API_KEY=...               # Auth del bridge
USER_ID=uuid-del-usuario             # Quién opera (de Cognito)
```

## Setup Local

```bash
cd mcp-forex/server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Llenar con valores
python server.py
```

## Flujo del Agente

```
1. should_trade_now()          → ¿Puedo operar?
2. get_open_positions()        → ¿Hay trades para cerrar?
3. get_daily_target_status()   → ¿Ya llegué al 1%?
4. forex_market_scan()         → ¿Qué pares tienen oportunidad?
5. forex_multi_timeframe()     → ¿Hay alineación D1+H4+H1?
6. get_optimal_sl_tp()         → ¿Dónde pongo SL/TP?
7. calculate_lot_size()        → ¿Cuánto arriesgo?
8. open_position()             → Ejecutar
9. log_hourly_decision()       → Registrar para auditoría
```

## Infraestructura

| Componente | URL |
|-----------|-----|
| MCP Server | `https://mcp-trading.awslearn.cloud/mcp` (deploy pendiente) |
| MT5 Bridge | `http://mt5-bridge.awslearn.cloud:5000` |
| PostgreSQL | `psql.ingenis.com.co:5432/forex_trading_db` |
| Frontend | `http://localhost:9000` |
| Backend API | `http://localhost:3333` |
