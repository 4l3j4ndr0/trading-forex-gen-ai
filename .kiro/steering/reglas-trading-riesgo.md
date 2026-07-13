# Reglas de Trading y Gestión de Riesgo

## Reglas Inquebrantables
1. **Máximo 1-2% de riesgo por operación** — NUNCA exceder
2. **Mínimo R:R 1:2** — No tomar trades con ratio inferior
3. **Máximo 3-5 posiciones simultáneas** — Evitar sobreoperar
4. **Drawdown diario máximo 6%** — Dejar de operar si se alcanza
5. **Drawdown semanal máximo 15%** — Reducir tamaño de posiciones
6. **No operar en noticias NFP/FOMC/BCE** — Esperar 30 minutos post-noticia
7. **Confluencia mínima de 3 factores** — Sin confluencia, no hay trade
8. **Respetar el Stop Loss** — NUNCA mover SL en contra

## Filtros de Validación
- ADX > 20 para trades direccionales
- Spread < 3 pips en majors (< 5 en crosses)
- Sesión de mercado activa para el par
- Sin eventos de alto impacto en próximos 30 min
- ATR dentro de rango normal (no extremos)
- No operar los primeros 15 min de apertura de sesión

## Sesiones Óptimas de Operación
| Sesión | Horario UTC | Pares Óptimos | Características |
|--------|-------------|---------------|-----------------|
| Tokyo | 00:00-09:00 | JPY, AUD, NZD | Rangos, baja volatilidad |
| London | 07:00-16:00 | EUR, GBP, CHF | Alta volatilidad, breakouts |
| New York | 12:00-21:00 | USD, CAD | Continuaciones, reversiones |
| Overlap LN-NY | 12:00-16:00 | Todos | Máxima liquidez y volumen |

## Gestión Post-Entrada
- TP1 alcanzado → Mover SL a breakeven
- TP2 alcanzado → Trailing stop activo
- Si el precio no avanza en 4 horas → Reevaluar señal
- Si confluencias se invalidan → Cerrar manualmente

## Métricas de Desempeño a Trackear
- Win Rate (objetivo: > 55%)
- Profit Factor (objetivo: > 1.5)
- Average R:R conseguido
- Expectancy por trade
- Max Drawdown
- Sharpe Ratio
- Trades por semana (max 15-20)
- Señales A vs B (ratio calidad)
