# Tools — System (Salud y Configuración)

---

## Tool 1: `get_safety_rules`

**Propósito:** Mostrar todas las reglas de seguridad activas del sistema.

**Inputs:** Ninguno

**Output:**
```json
{
  "rules": {
    "max_open_positions": 3,
    "max_lot_size": 0.50,
    "max_risk_per_trade_pct": 1.0,
    "max_daily_loss_usd": 100.0,
    "max_daily_loss_pct": 1.0,
    "max_consecutive_losses": 5,
    "min_rr_ratio": 1.5,
    "min_adx_for_entry": 25,
    "allowed_pairs": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "EURGBP"],
    "trading_hours_utc": "07:00-21:00",
    "no_trade_before_news_minutes": 30,
    "kill_switch": false
  },
  "current_state": {
    "open_positions": 1,
    "daily_pnl": 65.30,
    "consecutive_losses": 0,
    "daily_loss_remaining": 165.30,
    "can_trade": true
  }
}
```

---

## Tool 2: `health_check`

**Propósito:** Verificar que todos los componentes están funcionando.

**Inputs:** Ninguno

**Output:**
```json
{
  "status": "healthy",
  "timestamp": "2026-07-13T20:00:00Z",
  "components": {
    "mcp_server": {
      "status": "ok",
      "uptime_hours": 48.5
    },
    "mt5_bridge": {
      "status": "ok",
      "latency_ms": 45,
      "mt5_connected": true,
      "broker": "XM",
      "account_type": "demo"
    },
    "database": {
      "status": "ok",
      "trades_total": 156,
      "size_mb": 2.3
    },
    "tradingview": {
      "status": "ok",
      "last_analysis": "2026-07-13T19:55:00Z"
    }
  },
  "warnings": []
}
```

**Lógica interna:**
1. Ping al MT5 Bridge (GET /health)
2. Verificar DB accesible (SELECT 1)
3. Verificar TradingView TA (análisis rápido)
4. Medir latencia de cada componente

---

## Tool 3: `get_economic_calendar`

**Propósito:** Eventos económicos de alto impacto próximos.

**Inputs:**
| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `hours_ahead` | int | 4 | Ventana de tiempo a revisar |
| `impact` | str | "high" | "high", "medium", "all" |

**Output:**
```json
{
  "timestamp": "2026-07-13T20:00:00Z",
  "events_ahead": [
    {
      "time": "2026-07-14T12:30:00Z",
      "currency": "USD",
      "event": "CPI m/m",
      "impact": "high",
      "forecast": "0.3%",
      "previous": "0.2%",
      "hours_until": 16.5,
      "affects_pairs": ["EURUSD", "GBPUSD", "USDJPY"]
    }
  ],
  "next_high_impact": {
    "event": "CPI m/m",
    "in_hours": 16.5,
    "safe_to_trade": true
  },
  "blocked_pairs": [],
  "note": "No high-impact events in next 4 hours. Safe to trade all pairs."
}
```

**Fuentes posibles:**
- Forex Factory (scraping)
- MQL5 economic calendar
- Investing.com calendar API

**Reglas:**
- Si evento high-impact en < 30 min → bloquear pares afectados
- Si evento high-impact en < 2 horas → warning
- NFP, FOMC, BCE, BOE → bloquear ALL pairs 30 min antes/después
