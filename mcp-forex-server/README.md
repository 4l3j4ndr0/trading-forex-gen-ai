# MCP Forex Trading Server

Sistema de trading automatizado para Forex. Un MCP server expone 32 tools que un agente LLM (Claude) consume para analizar mercados y ejecutar operaciones en MetaTrader 5 via un broker (XM).

## Arquitectura

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  🤖 AGENTE (Claude)  │────▶│  MCP Server          │────▶│  MT5 Bridge (VPS)   │
│  Kiro Web / API      │     │  32 tools            │     │  Flask + MT5        │
│  Decide qué hacer    │◀────│  PostgreSQL (RDS)    │◀────│  XM Broker          │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

## Producción

| Componente | URL |
|-----------|-----|
| MCP Server | `https://mcp-trading.awslearn.cloud/mcp` |
| MT5 Bridge | `http://mt5-bridge.awslearn.cloud:5000` |
| PostgreSQL | `psql.ingenis.com.co:5432/forex_trading_db` |

## Tools (32 total)

### 🔬 Analysis Tools (4) — TradingView TA

| Tool | Descripción |
|------|-------------|
| `forex_analysis` | Análisis técnico completo (RSI, MACD, ADX, EMAs, Bollinger) de un par en un timeframe |
| `forex_multi_timeframe` | Análisis top-down D1→H4→H1 con score de alineación (-3 a +3) |
| `forex_market_scan` | Escanea múltiples pares y rankea oportunidades por ADX y alineación |
| `get_session_info` | Sesión activa (London/NY/Tokyo), volatilidad, pares óptimos |

### 📊 Market Data Tools (6) — Indicadores y Estructura

| Tool | Descripción |
|------|-------------|
| `get_candles` | Velas OHLCV crudas del broker (hasta 500) |
| `get_indicator_atr` | ATR real del broker por timeframe |
| `get_spread_live` | Spread actual en vivo (bid/ask/pips) |
| `get_market_data` | **Combo**: velas + RSI(14) + EMA(10/20/50) + MACD + Bollinger + ATR + spread |
| `get_fibonacci_levels` | Retrocesos (23.6%-78.6%) + extensiones (127.2%-200%) con swing detection |
| `get_market_structure` | **SMC**: trend, BOS/CHoCH, Order Blocks, Fair Value Gaps, liquidity zones, bias |

### 📰 News Tools (1) — Noticias y Sentimiento

| Tool | Descripción |
|------|-------------|
| `get_news_for_pair` | Noticias recientes por par con título, descripción, sentimiento, impacto y bias |

### 💰 Trading Tools (7) — MT5 Bridge

| Tool | Descripción |
|------|-------------|
| `open_position` | Abre posición con safety checks (kill switch, horario, max positions, R:R, daily loss) |
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
| `should_trade_now` | Validación integral: kill switch, horario, daily loss, max positions, rachas |
| `get_optimal_sl_tp` | SL/TP dinámicos basados en ATR con estrategias conservative/balanced/aggressive |

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

### ⚙️ System Tools (3) — Salud y Seguridad

| Tool | Descripción |
|------|-------------|
| `get_safety_rules` | Todas las reglas activas + estado actual (posiciones, PnL, rachas) |
| `health_check` | Estado de MCP, BD, TradingView y MT5 Bridge |
| `get_economic_calendar` | Eventos económicos próximos (placeholder) |

## Configuración

`.env` del server:

```env
DATABASE_URL=postgresql://...        # Misma BD que el backend
MT5_BRIDGE_URL=http://mt5-bridge.awslearn.cloud:5000
MT5_BRIDGE_API_KEY=...               # Auth del bridge
USER_ID=uuid-del-usuario             # Quién opera (de Cognito)
```

## Seguridad

El MCP está protegido con API Key via nginx:

```json
{
  "mcpServers": {
    "forex-trading": {
      "url": "https://mcp-trading.awslearn.cloud/mcp",
      "headers": {
        "X-Api-Key": "<TOKEN>"
      }
    }
  }
}
```

Sin el header `X-Api-Key` correcto, nginx retorna 401.

## Deploy

```bash
cd mcp-forex-server
docker build -t mcp-forex-server .
docker run -d --name mcp-forex --restart unless-stopped --env-file .env -p 8000:8000 mcp-forex-server
```

## Flujo del Agente

```
1. should_trade_now()          → ¿Puedo operar?
2. get_safety_rules()          → ¿Qué reglas debo respetar?
3. get_open_positions()        → ¿Hay trades para gestionar?
4. get_daily_target_status()   → ¿Ya llegué al 1%?
5. get_news_for_pair()         → ¿Hay noticias que afecten?
6. forex_market_scan()         → ¿Qué pares tienen oportunidad?
7. get_market_structure()      → ¿Cuál es la estructura SMC?
8. get_market_data()           → Indicadores técnicos
9. get_fibonacci_levels()      → Niveles clave de S/R
10. forex_multi_timeframe()    → ¿Hay alineación D1+H4+H1?
11. calculate_lot_size()       → Position sizing
12. open_position()            → Ejecutar
13. log_hourly_decision()      → Registrar para auditoría
```
