# Agent Prompt — Especificación

## Flujo del Agente por Hora

```
┌─ FASE 0: Pre-check ──────────────────────────────────────┐
│  should_trade_now() → ¿Puedo operar?                      │
│  Si NO → log_hourly_decision(skipped) → FIN               │
└───────────────────────────────┬───────────────────────────┘
                                │ SÍ
                                ▼
┌─ FASE 1: Gestión de posiciones ──────────────────────────┐
│  get_open_positions() → ¿Hay trades abiertos?             │
│  Para cada uno:                                           │
│  • Expirado (>55 min)? → close_position(expired)          │
│  • PnL > target? → close_position(tp_hit)                 │
│  • PnL < -SL? → close_position(sl_hit)                    │
│  • PnL > +15 pips? → modify_position(SL to breakeven)     │
└───────────────────────────────┬───────────────────────────┘
                                │
                                ▼
┌─ FASE 2: Target check ───────────────────────────────────┐
│  get_daily_target_status() → ¿Ya llegué al 1%?           │
│  Si SÍ → log(target_reached) → FIN                       │
│  Si pérdida > límite → log(daily_stop) → FIN             │
└───────────────────────────────┬───────────────────────────┘
                                │ NO alcanzado
                                ▼
┌─ FASE 3: Análisis ───────────────────────────────────────┐
│  get_session_info() → ¿Qué pares son óptimos ahora?      │
│  forex_market_scan(optimal_pairs) → Top oportunidades     │
│  forex_multi_timeframe(top_pair) → Alineación             │
│  forex_analysis(top_pair, "1h") → Indicadores             │
└───────────────────────────────┬───────────────────────────┘
                                │
                                ▼
┌─ FASE 4: Decisión ───────────────────────────────────────┐
│  5 FILTROS (todos deben pasar):                           │
│  1. Alineación TF ≥ 2 de 3 (D1+H4+H1)                   │
│  2. ADX H1 > 25                                          │
│  3. RSI no en zona muerta (40-60)                         │
│  4. Spread < 3 pips (majors)                              │
│  5. Sin news high-impact en 30 min                        │
│                                                           │
│  Si pasan → calcular trade                                │
│  Si NO → skip + log razón                                 │
└───────────────────────────────┬───────────────────────────┘
                                │ PASAN
                                ▼
┌─ FASE 5: Ejecución ─────────────────────────────────────┐
│  get_optimal_sl_tp(symbol, side) → SL/TP dinámicos        │
│  calculate_lot_size(sl_pips, risk=1%) → Lot exacto        │
│  open_position(symbol, side, lot, sl, tp, comment)        │
└───────────────────────────────┬───────────────────────────┘
                                │
                                ▼
┌─ FASE 6: Log ────────────────────────────────────────────┐
│  log_hourly_decision(                                     │
│    trades_opened, trades_closed, trades_skipped,          │
│    pnl_this_hour, market_context, decision_summary        │
│  )                                                        │
└──────────────────────────────────────────────────────────┘
```

## Los 5 Filtros de Entrada

| # | Filtro | Condición para BUY | Condición para SELL |
|---|--------|-------------------|---------------------|
| 1 | Alineación TF | Score ≥ +2 | Score ≤ -2 |
| 2 | Fuerza tendencia | ADX H1 > 25 | ADX H1 > 25 |
| 3 | Momentum | RSI < 40 o > 60 | RSI < 40 o > 60 |
| 4 | Spread | < 3 pips (majors) | < 3 pips (majors) |
| 5 | Calendario | No news 30 min | No news 30 min |

## Scoring de Alineación

```
D1: +1 (BULL) / -1 (BEAR) / 0 (NEUTRAL)
H4: +1 (BULL) / -1 (BEAR) / 0 (NEUTRAL)
H1: +1 (BULL) / -1 (BEAR) / 0 (NEUTRAL)

Score = D1 + H4 + H1

 +3 → STRONG BUY (lot size mayor)
 +2 → BUY (lot size normal)
 +1 → WEAK, no operar
  0 → No operar
 -1 → WEAK, no operar
 -2 → SELL (lot size normal)
 -3 → STRONG SELL (lot size mayor)
```

## Gestión Post-Entrada

| Condición | Acción |
|-----------|--------|
| PnL > +15 pips | Mover SL a breakeven |
| PnL > +30 pips | Trailing stop (SL = precio - 15 pips) |
| Posición > 55 min | Cerrar (expirada) |
| Target diario alcanzado | Cerrar todas, parar |
| Daily loss limit alcanzado | Cerrar todas, parar |

## Target Diario

- **Cálculo:** Balance × 1% = Target USD
- **Ejemplo:** $10,000 × 1% = $100
- **Comportamiento:**
  - 0-80%: Opera normal
  - 80-100%: Reduce lot size a la mitad
  - 100%+: STOP, no más trades
  - Pérdida > -1%: STOP total

## Formato de Respuesta del Agente

```
═══════════════════════════════════════════
📅 2026-07-13 | 🕐 20:00 UTC | 🏦 NY Session
═══════════════════════════════════════════

🔍 PRE-CHECK:
✅ Session active (NY: 12:00-21:00)
✅ No high-impact news next 2h
✅ Daily PnL: +$65.30 (target: $100)
✅ Positions: 1/3

📊 ANÁLISIS:
┌──────────┬──────┬─────┬─────┬───────┬───────┐
│ Par      │ D1   │ H4  │ H1  │ Score │ ADX   │
├──────────┼──────┼─────┼─────┼───────┼───────┤
│ EURUSD   │ BUY  │ BUY │ BUY │  +3   │ 32.5  │
│ GBPUSD   │ SELL │SELL │ NEU │  -2   │ 28.1  │
│ USDJPY   │ NEU  │ NEU │ BUY │  +1   │ 18.5  │
└──────────┴──────┴─────┴─────┴───────┴───────┘

📈 DECISIÓN:
• EURUSD: ✅ STRONG BUY (score +3, ADX 32.5, RSI 62)
  → Lot: 0.33 | SL: 28 pips | TP: 56 pips | RR: 2.0
• GBPUSD: ⚠️ SKIP — H1 no confirma (neutral)
• USDJPY: ❌ SKIP — ADX 18.5 < 25

💼 EJECUCIÓN:
• Opened: EURUSD BUY 0.33 lots @ 1.0898
  SL: 1.0870 | TP: 1.0954 | Risk: $92.40

💰 ESTADO:
• PnL hoy: +$65.30 (65.3% del target)
• Posiciones: 2 abiertas
• Racha: 3W / 0L
═══════════════════════════════════════════
```
