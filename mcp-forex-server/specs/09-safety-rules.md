# Safety Rules — Reglas de Seguridad

## Principio

Cada tool de trading valida las safety rules ANTES de ejecutar. Si alguna regla falla, el tool retorna un error explicativo y NO ejecuta la operación.

## Reglas

Las reglas se almacenan en la tabla `trading_settings` de PostgreSQL. Se leen al inicio de cada ciclo y se pueden modificar en caliente (sin redeploy) via el tool `update_trading_setting` o desde un frontend futuro.

| Regla | Key en BD | Valor Default | Categoría |
|-------|-----------|--------------|-----------|
| Max posiciones abiertas | `max_open_positions` | 3 | sizing |
| Max lot size | `max_lot_size` | 0.50 | sizing |
| Max riesgo por trade | `max_risk_per_trade_pct` | 1% | risk |
| Max pérdida diaria | `max_daily_loss_pct` | 1% | risk |
| Max pérdidas consecutivas | `max_consecutive_losses` | 5 | risk |
| Min balance | `min_balance_usd` | $500 | system |
| Min R:R | `min_rr_ratio` | 1.5 | risk |
| Min ADX | `min_adx_entry` | 25 | filters |
| Pares permitidos | `allowed_pairs` | 6 majors | pairs |
| Horario | `trading_start_utc` / `trading_end_utc` | 07-21 UTC | session |
| News buffer | `news_buffer_minutes` | 30 min | session |
| Kill switch | `kill_switch` | false | system |
| Target diario | `daily_target_pct` | 1% | target |
| Max spread | `max_spread_pips` | 3.0 | filters |

## Validación en `open_position`

```python
def can_open_position(symbol, lot_size, sl_pips, risk_usd, rr_ratio):
    checks = []
    
    # 1. Kill switch
    if config.kill_switch:
        return BLOCKED("Kill switch is ON")
    
    # 2. Horario
    if not in_trading_hours():
        return BLOCKED("Outside trading hours (07-21 UTC)")
    
    # 3. Par permitido
    if symbol not in config.allowed_pairs:
        return BLOCKED(f"{symbol} not in allowed pairs")
    
    # 4. Max posiciones
    if count_open_positions() >= config.max_open_positions:
        return BLOCKED(f"Max positions reached ({config.max_open_positions})")
    
    # 5. Lot size
    if lot_size > config.max_lot_size:
        return BLOCKED(f"Lot {lot_size} exceeds max {config.max_lot_size}")
    
    # 6. Riesgo por trade
    balance = get_balance()
    max_risk = balance * config.max_risk_pct / 100
    if risk_usd > max_risk:
        return BLOCKED(f"Risk ${risk_usd} exceeds {config.max_risk_pct}% of balance")
    
    # 7. Pérdida diaria
    daily_pnl = get_daily_pnl()
    max_daily_loss = balance * config.max_daily_loss_pct / 100
    if daily_pnl <= -max_daily_loss:
        return BLOCKED(f"Daily loss limit hit (${daily_pnl})")
    
    # 8. Pérdidas consecutivas
    if get_consecutive_losses() >= config.max_consecutive_losses:
        return BLOCKED(f"Too many consecutive losses")
    
    # 9. Min balance
    if balance < config.min_balance_usd:
        return BLOCKED(f"Balance ${balance} below minimum ${config.min_balance_usd}")
    
    # 10. R:R ratio
    if rr_ratio < config.min_rr_ratio:
        return BLOCKED(f"RR {rr_ratio} below minimum {config.min_rr_ratio}")
    
    return ALLOWED()
```

## Kill Switch

Uso de emergencia. Se activa:
- Manualmente: cambiar variable de entorno y restart container
- O via un tool futuro `toggle_kill_switch(on/off)`

Cuando está ON:
- `open_position` → bloqueado
- `close_position` → PERMITIDO (para cerrar existentes)
- `close_all_positions` → PERMITIDO
- Análisis → PERMITIDO

## Validación Diaria (Auto-reset)

Cada día a las 00:00 UTC:
- Reset consecutive_losses counter (solo si hubo pausa)
- Guardar daily_summary del día anterior
- Calcular nuevo target basado en balance actual
