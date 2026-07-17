# SP500 MCP Server

Servidor MCP (Model Context Protocol) dedicado al trading automatizado del S&P 500 (US500Cash) via MetaTrader 5. Diseñado para Smart Money Concepts con enfoque en Killzones de Nueva York.

## Arquitectura

```
                    ┌─────────────────────┐
                    │   AI Agent (Claude)  │
                    └──────────┬──────────┘
                               │ SSE
                    ┌──────────▼──────────┐
                    │  SP500 MCP Server   │
                    │  (FastMCP - Python) │
                    │  Port 8001          │
                    └──┬──────────────┬───┘
                       │              │
          ┌────────────▼───┐   ┌──────▼──────────┐
          │  MT5 Bridge    │   │  PostgreSQL      │
          │  (Flask - VPS) │   │  sp500_settings  │
          │  US500Cash#    │   │  sp500_trades    │
          └────────────────┘   │  sp500_logs      │
                               └─────────────────┘
```

## Diferencias vs Forex MCP

| Aspecto | Forex MCP | SP500 MCP |
|---------|-----------|-----------|
| Unidad | Pips (0.0001) | Puntos ($1/pt/lot) |
| Horario | 24/5, sesiones Tokyo/London/NY | Solo Killzones NY |
| Timeframe trigger | M15 | M5 |
| Liquidez clave | Session overlaps | PDH/PDL, Asia/London sweeps |
| Simbolo | EURUSD, GBPUSD, etc. | US500Cash |
| Min Lot (XM) | 0.01 | 0.10 |
| Lot Step | 0.01 | 0.10 |
| Config | trading_settings | sp500_settings |

## Tools (15)

### Session (1)
| Tool | Descripcion |
|------|-------------|
| `sp500_session_guardian` | Valida Killzones AM/PM. Solo permite trades en ventanas activas. |

### Liquidity (2)
| Tool | Descripcion |
|------|-------------|
| `sp500_get_liquidity_levels` | PDH/PDL, Asia H/L, London H/L, sweeps detectados, bias |
| `sp500_get_key_levels` | Swing H/L semanales, numeros redondos, zona Premium/Discount |

### Structure (2)
| Tool | Descripcion |
|------|-------------|
| `sp500_market_structure` | SMC en M5/M15/H1: BOS, CHoCH, FVG, Order Blocks |
| `sp500_multi_timeframe` | Alineacion H1+M15+M5, score -3 a +3 |

### Risk (2)
| Tool | Descripcion |
|------|-------------|
| `sp500_calculate_risk` | Position sizing: balance * risk% / (SL_points * point_value) |
| `sp500_get_optimal_sl_tp` | SL/TP basado en ATR M5(14), R:R minimo 1.5:1 |

### News (1)
| Tool | Descripcion |
|------|-------------|
| `sp500_macro_filter` | Solo eventos USD (Fed, CPI, NFP, PPI). Ignora Forex. |

### Trading (5)
| Tool | Descripcion |
|------|-------------|
| `sp500_open_position` | Abrir posicion en US500Cash |
| `sp500_close_position` | Cerrar por ticket |
| `sp500_modify_position` | Modificar SL/TP (trailing, breakeven) |
| `sp500_get_positions` | Posiciones abiertas de US500Cash |
| `sp500_get_account` | Balance, equity, margin |

### Database (2)
| Tool | Descripcion |
|------|-------------|
| `sp500_register_trade` | Registrar trade en BD |
| `sp500_update_trade` | Actualizar trade cerrado (PnL, reason) |
| `sp500_get_performance` | Stats: win rate, profit factor, PnL |
| `sp500_log_decision` | Log de decision del agente por ciclo |

## Configuracion

La configuracion de trading se lee de la tabla `sp500_settings` (gestionada via frontend). El `.env` solo contiene conexiones:

```env
PORT=8001
MT5_BRIDGE_URL=http://mt5-bridge.awslearn.cloud:5000
MT5_BRIDGE_API_KEY=your_key
DATABASE_URL=postgresql://user:pass@host:5432/forex_trading_db
USER_ID=uuid-del-usuario
SYMBOL=US500Cash
```

### Settings en BD (sp500_settings)

| Campo | Default | Descripcion |
|-------|---------|-------------|
| symbol | US500Cash | Simbolo MT5 (sin suffix) |
| point_value | 1.00 | $/punto/lote |
| min_lot | 0.10 | Lote minimo XM |
| max_lot | 5.00 | Lote maximo |
| max_risk_per_trade_pct | 1.00 | % riesgo por trade |
| daily_target_points | 30.0 | Objetivo diario en puntos |
| kill_switch | false | Pausar trading |

> **Nota DST:** Las Killzones se definen en tiempo local NY (ET) dentro del codigo,
> NO como UTC estatico. `sp500_session_guardian` usa `pytz` con `America/New_York`
> para manejar DST automaticamente:
> - Verano (EDT, UTC-4): AM Killzone = 13:30-15:30 UTC
> - Invierno (EST, UTC-5): AM Killzone = 14:30-16:30 UTC
> No necesitas cambiar nada manualmente en noviembre/marzo.

## Ejecucion

### Local
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python server.py
```

### Docker
```bash
docker build -t sp500-mcp .
docker run -p 8001:8001 --env-file .env sp500-mcp
```

## Estrategia del Agente (resumen)

**Filosofia: Trailing Stop, NO Hedging.**
El SP500 es hiper-direccional post-sweep. Una vez que rompe un nivel, tiende a continuar.
El Hedging funciona en Forex (lateralizaciones frecuentes), pero en indices la mejor
gestion es: entrada precisa, trailing agresivo, y cierre rapido si la estructura se invalida.

### Gestion de Posicion
1. Entrada: Solo en Killzones, post-sweep + CHoCH confirmado
2. SL inicial: Detras del swing/OB que genero el CHoCH
3. +1R alcanzado: Mover SL a Break Even
4. +1.5R alcanzado: Trailing stop a +0.5R
5. Target: Next liquidity level o +2R (lo que llegue primero)
6. Invalidacion: Si estructura se rompe en contra en M5, cierre inmediato

### Ciclo de Ejecucion
1. `sp500_session_guardian()` — Bloquea fuera de Killzones
2. `sp500_get_liquidity_levels()` — Que niveles fueron barridos en la apertura
3. `sp500_market_structure('M5')` — CHoCH post-sweep (confirmacion reversal)
4. `sp500_get_key_levels()` — Precio en Discount/Premium
5. Si confluencia (sweep + CHoCH + POI + discount/premium):
   - `sp500_calculate_risk(sl_points)` — Lote basado en SL
   - `sp500_open_position(side, lots, sl, tp)` — Entrada
6. Gestion activa: `sp500_modify_position()` para trailing
7. `sp500_log_decision()` — Auditoria del ciclo

### Ejemplo de ciclo exitoso
```
1. sp500_session_guardian() → AM Killzone activa
2. sp500_get_liquidity_levels() → PDL swept at 7504, bias: SWEPT_LOWS
3. sp500_market_structure('M5') → CHoCH BULLISH at 7508
4. sp500_get_key_levels() → Precio en DISCOUNT zone
5. sp500_calculate_risk(sl_points=15) → 0.60 lots
6. sp500_open_position('BUY', 0.60, 15, 30) → Entry 7510, SL 7495, TP 7540
7. sp500_log_decision("BUY 0.60 | PDL swept + CHoCH M5 + Discount zone")
```
