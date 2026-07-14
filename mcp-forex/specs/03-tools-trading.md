# Tools — Trading (MT5 Bridge)

## Conexión

El MCP server se comunica con el MT5 Bridge via HTTP REST.

```
MCP Server (EC2 Linux) ──HTTPS──► MT5 Bridge (VPS Windows:5000)
```

**Auth:** Header `X-Bridge-Api-Key` en cada request.

---

## Tool 1: `open_position`

**Propósito:** Abrir una posición en el mercado forex via MT5.

**Inputs:**
| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `symbol` | str | required | "EURUSD", "GBPUSD", etc |
| `side` | str | required | "BUY" o "SELL" |
| `lot_size` | float | required | Tamaño del lote (0.01 min) |
| `sl_pips` | float | required | Stop Loss en pips |
| `tp_pips` | float | required | Take Profit en pips |
| `comment` | str | "" | Razón del trade (para auditoría) |

**Output:**
```json
{
  "success": true,
  "ticket": 12345678,
  "symbol": "EURUSD",
  "side": "BUY",
  "lot_size": 0.05,
  "entry_price": 1.0898,
  "stop_loss": 1.0868,
  "take_profit": 1.0958,
  "sl_pips": 30,
  "tp_pips": 60,
  "rr_ratio": 2.0,
  "risk_usd": 15.0,
  "opened_at": "2026-07-13T20:00:05Z",
  "trade_id": "uuid-xxx"
}
```

**Lógica interna:**
1. SafetyGuard.can_open_position() → valida reglas
2. Calcula SL/TP en precio: sl_price = entry ± (sl_pips × point)
3. Envía orden al MT5 Bridge: POST /order/open
4. Si éxito → registra en DB (register_trade)
5. Retorna confirmación con trade_id

**Validaciones previas:**
- Symbol en ALLOWED_PAIRS
- Max positions no excedido
- Daily loss no excedido
- Lot size dentro de límites
- Kill switch no activo

---

## Tool 2: `close_position`

**Propósito:** Cerrar una posición específica por ticket.

**Inputs:**
| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `ticket` | int | required | Ticket de MT5 |
| `close_reason` | str | "" | "tp_hit", "sl_hit", "expired", "manual", "target_reached" |

**Output:**
```json
{
  "success": true,
  "ticket": 12345678,
  "symbol": "EURUSD",
  "side": "BUY",
  "entry_price": 1.0898,
  "exit_price": 1.0928,
  "pnl_pips": 30.0,
  "pnl_usd": 15.0,
  "holding_time_minutes": 45,
  "close_reason": "tp_hit",
  "closed_at": "2026-07-13T20:45:00Z"
}
```

**Lógica interna:**
1. Envía al Bridge: POST /order/close {ticket}
2. Calcula PnL en pips y USD
3. Actualiza DB (update_trade)
4. Actualiza daily PnL acumulado

---

## Tool 3: `modify_position`

**Propósito:** Modificar SL/TP de una posición abierta (breakeven, trailing).

**Inputs:**
| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `ticket` | int | required | Ticket de MT5 |
| `new_sl` | float | null | Nuevo Stop Loss (precio) |
| `new_tp` | float | null | Nuevo Take Profit (precio) |

**Output:**
```json
{
  "success": true,
  "ticket": 12345678,
  "old_sl": 1.0868,
  "new_sl": 1.0898,
  "old_tp": 1.0958,
  "new_tp": 1.0958,
  "note": "SL moved to breakeven"
}
```

**Casos de uso:**
- Move SL to breakeven cuando PnL > +15 pips
- Trailing stop: mover SL siguiendo al precio
- Extender TP si la tendencia es fuerte

---

## Tool 4: `close_all_positions`

**Propósito:** Cerrar todas las posiciones abiertas (o filtradas por símbolo).

**Inputs:**
| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `symbol` | str | null | Si se provee, solo cierra ese par |
| `reason` | str | "batch_close" | Razón del cierre masivo |

**Output:**
```json
{
  "closed_count": 2,
  "total_pnl_pips": 18.5,
  "total_pnl_usd": 12.30,
  "details": [
    {"ticket": 123, "symbol": "EURUSD", "pnl_usd": 8.50},
    {"ticket": 456, "symbol": "GBPUSD", "pnl_usd": 3.80}
  ]
}
```

---

## Tool 5: `get_open_positions`

**Propósito:** Listar todas las posiciones abiertas con PnL en tiempo real.

**Inputs:** Ninguno

**Output:**
```json
{
  "count": 2,
  "total_unrealized_pnl": 12.50,
  "positions": [
    {
      "ticket": 12345678,
      "symbol": "EURUSD",
      "side": "BUY",
      "lot_size": 0.05,
      "entry_price": 1.0898,
      "current_price": 1.0918,
      "sl": 1.0868,
      "tp": 1.0958,
      "pnl_pips": 20.0,
      "pnl_usd": 10.00,
      "age_minutes": 35,
      "comment": "H1 bullish alignment score +3"
    }
  ]
}
```

---

## Tool 6: `get_account_info`

**Propósito:** Información de la cuenta de trading.

**Inputs:** Ninguno

**Output:**
```json
{
  "broker": "XM",
  "account_type": "demo",
  "balance": 10000.00,
  "equity": 10012.50,
  "margin_used": 45.00,
  "free_margin": 9967.50,
  "margin_level_pct": 22250.0,
  "leverage": 500,
  "currency": "USD",
  "open_positions": 2
}
```

---

## Tool 7: `get_symbol_info`

**Propósito:** Información técnica de un par (spread, pip value, horarios).

**Inputs:**
| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `symbol` | str | required | Par forex |

**Output:**
```json
{
  "symbol": "EURUSD",
  "spread_points": 16,
  "spread_pips": 1.6,
  "pip_value_per_lot": 10.0,
  "min_lot": 0.01,
  "max_lot": 50.0,
  "lot_step": 0.01,
  "digits": 5,
  "point": 0.00001,
  "trade_allowed": true,
  "session_open": true
}
```
