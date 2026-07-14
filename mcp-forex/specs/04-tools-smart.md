# Tools — Smart (Lógica de Negocio)

## Propósito

Estos tools encapsulan la lógica de negocio del sistema de trading. Le dan al agente información procesada para tomar mejores decisiones sin que tenga que calcular manualmente.

---

## Tool 1: `calculate_lot_size`

**Propósito:** Calcular el tamaño de lote correcto basado en gestión de riesgo.

**Fórmula:** `lot_size = (balance × risk_pct) / (sl_pips × pip_value_per_lot)`

**Inputs:**
| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `symbol` | str | required | Par forex (para obtener pip_value) |
| `sl_pips` | float | required | Stop loss en pips |
| `risk_pct` | float | 1.0 | Porcentaje del balance a arriesgar |

**Output:**
```json
{
  "symbol": "EURUSD",
  "balance": 10000.00,
  "risk_pct": 1.0,
  "risk_usd": 100.00,
  "sl_pips": 30,
  "pip_value_per_lot": 10.0,
  "calculated_lot": 0.33,
  "adjusted_lot": 0.33,
  "max_allowed_lot": 0.50,
  "margin_required": 66.00,
  "note": "Lot size adjusted to step size 0.01"
}
```

**Lógica interna:**
1. Obtiene balance actual via `get_account_info()`
2. Obtiene pip_value via `get_symbol_info(symbol)`
3. Calcula: `(balance × risk_pct/100) / (sl_pips × pip_value)`
4. Ajusta al step_size del broker (redondea hacia abajo)
5. Verifica que no exceda max_lot del safety rules
6. Verifica que margin_required < free_margin

---

## Tool 2: `get_daily_target_status`

**Propósito:** ¿Ya llegamos al target del día? ¿Cuánto falta?

**Inputs:** Ninguno

**Output:**
```json
{
  "date": "2026-07-13",
  "balance_start_of_day": 10000.00,
  "target_pct": 1.0,
  "target_usd": 100.00,
  "realized_pnl_today": 65.30,
  "unrealized_pnl": 12.50,
  "total_pnl": 77.80,
  "progress_pct": 77.8,
  "remaining_usd": 22.20,
  "target_reached": false,
  "trades_today": 4,
  "wins_today": 3,
  "losses_today": 1,
  "recommendation": "CONTINUE — Target not reached, 2 hours of NY session remaining"
}
```

**Lógica interna:**
1. Lee balance al inicio del día (de DB o calcula balance - pnl_today)
2. Calcula target: balance_start × target_pct/100
3. Suma PnL realizado del día (trades cerrados)
4. Suma PnL no realizado (posiciones abiertas)
5. Determina si continuar o parar

**Reglas de recomendación:**
- `progress >= 100%` → "STOP — Daily target reached. No more trades."
- `progress >= 80%` → "CAREFUL — Close to target. Reduce lot size."
- `realized_pnl < -target` → "STOP — Daily loss limit hit."
- Else → "CONTINUE"

---

## Tool 3: `should_trade_now`

**Propósito:** Validación integral de si es buen momento para operar.

**Inputs:** Ninguno

**Output:**
```json
{
  "can_trade": true,
  "checks": {
    "session_active": {
      "pass": true,
      "detail": "New York session active (12:00-21:00 UTC)"
    },
    "no_high_impact_news": {
      "pass": true,
      "detail": "Next high-impact event: FOMC in 6 hours"
    },
    "daily_loss_ok": {
      "pass": true,
      "detail": "Daily PnL: +$65.30 (limit: -$100)"
    },
    "max_positions_ok": {
      "pass": true,
      "detail": "Open: 1/3 positions"
    },
    "kill_switch_off": {
      "pass": true,
      "detail": "Kill switch: OFF"
    },
    "consecutive_losses_ok": {
      "pass": true,
      "detail": "Consecutive losses: 1 (max: 5)"
    }
  },
  "warnings": [
    "NY session ends in 1.5 hours — consider smaller positions"
  ],
  "blocked_reasons": []
}
```

**Lógica interna:**
1. Verifica sesión activa (hora UTC)
2. Consulta calendario económico (próximas 30 min)
3. Verifica daily PnL vs límite
4. Cuenta posiciones abiertas vs máximo
5. Verifica kill switch
6. Cuenta pérdidas consecutivas
7. Si ALGUNO falla → `can_trade: false` + `blocked_reasons`

---

## Tool 4: `get_optimal_sl_tp`

**Propósito:** Calcular SL y TP dinámicos basados en ATR y estructura del mercado.

**Inputs:**
| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `symbol` | str | required | Par forex |
| `side` | str | required | "BUY" o "SELL" |
| `strategy` | str | "balanced" | "conservative", "balanced", "aggressive" |

**Output:**
```json
{
  "symbol": "EURUSD",
  "side": "BUY",
  "strategy": "balanced",
  "current_price": 1.0898,
  "atr_14_h1": 0.00085,
  "atr_14_pips": 8.5,
  "stop_loss": {
    "price": 1.0870,
    "pips": 28,
    "method": "1.5 × ATR below entry"
  },
  "take_profit_1": {
    "price": 1.0938,
    "pips": 40,
    "method": "2 × ATR above entry",
    "rr_ratio": 1.43
  },
  "take_profit_2": {
    "price": 1.0968,
    "pips": 70,
    "method": "3 × ATR above entry",
    "rr_ratio": 2.50
  },
  "recommended_tp": "take_profit_1",
  "min_rr_ratio": 1.43
}
```

**Estrategias:**
| Estrategia | SL | TP1 | TP2 | Uso |
|-----------|-----|-----|-----|-----|
| conservative | 2×ATR | 2×ATR | 3×ATR | Mercado incierto |
| balanced | 1.5×ATR | 2×ATR | 3×ATR | Default |
| aggressive | 1×ATR | 2.5×ATR | 4×ATR | Tendencia fuerte |

**Lógica interna:**
1. Obtiene ATR(14) del H1 via `forex_analysis`
2. Calcula SL/TP según estrategia
3. Verifica que RR >= 1.5 (mínimo aceptable)
4. Si RR < 1.5 → ajusta o advierte
