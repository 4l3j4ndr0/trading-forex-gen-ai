---
name: indicadores
description: Guía detallada de implementación de indicadores técnicos (EMA, RSI, MACD, BB, ATR, ADX, Fibonacci). Usar al implementar, depurar o modificar cálculos de indicadores.
---

# Skill: Indicadores Técnicos

## EMA — Exponential Moving Average

### Fórmula
```
EMA = Precio_Actual × Multiplicador + EMA_Anterior × (1 - Multiplicador)
Multiplicador = 2 / (Período + 1)
```

### Parámetros del Sistema
| Período | Uso | Señal |
|---------|-----|-------|
| 8 | Ultra-corto | Timing de entrada, trailing |
| 21 | Corto | Tendencia menor, pullback |
| 50 | Medio | S/R dinámica, cruce golden/death |
| 200 | Largo | Sesgo macro (precio encima = alcista) |

### Señales de Cruce
- EMA 8 cruza EMA 21 ↑ → Señal alcista corto plazo
- EMA 21 cruza EMA 50 ↑ → Confirmación tendencia
- EMA 50 cruza EMA 200 ↑ → Golden Cross (muy alcista)
- Inversos → Señales bajistas

## RSI — Relative Strength Index (Período 14)

### Fórmula
```
RS = Ganancia_Promedio / Pérdida_Promedio
RSI = 100 - (100 / (1 + RS))
Promedio = EMA de 14 períodos (no SMA)
```

### Interpretación
| Valor | Zona | Señal |
|-------|------|-------|
| > 80 | Extremo sobrecompra | Agotamiento, posible reversión |
| 70-80 | Sobrecompra | Precaución compras |
| 50-70 | Alcista | Momentum positivo |
| 40-50 | Neutral | Sin sesgo claro |
| 30-40 | Bajista | Momentum negativo |
| 20-30 | Sobreventa | Precaución ventas |
| < 20 | Extremo sobreventa | Agotamiento, posible reversión |

### Divergencias
- **Divergencia alcista**: Precio hace LL, RSI hace HL → Compra
- **Divergencia bajista**: Precio hace HH, RSI hace LH → Venta
- **Hidden alcista**: Precio hace HL, RSI hace LL → Continuación alcista
- **Hidden bajista**: Precio hace LH, RSI hace HH → Continuación bajista

## MACD — Moving Average Convergence Divergence

### Fórmula
```
MACD_Line = EMA(12) - EMA(26)
Signal_Line = EMA(9) del MACD_Line
Histogram = MACD_Line - Signal_Line
```

### Señales
- MACD cruza Signal ↑ → Compra
- MACD cruza Signal ↓ → Venta
- MACD cruza línea 0 ↑ → Sesgo alcista confirmado
- Histograma creciente → Momentum aumentando
- Histograma decreciente → Momentum disminuyendo
- Divergencia MACD-Precio → Agotamiento

## Bandas de Bollinger (Período 20, Desviación 2)

### Fórmula
```
Banda_Media = SMA(20)
Banda_Superior = SMA(20) + 2 × StdDev(20)
Banda_Inferior = SMA(20) - 2 × StdDev(20)
Ancho = (Banda_Superior - Banda_Inferior) / Banda_Media
```

### Señales
- **Squeeze**: Bandas se contraen → Explosión de volatilidad inminente
- **Expansión**: Bandas se expanden → Movimiento direccional activo
- **Walk the Band** (superior): Tendencia alcista fuerte
- **Walk the Band** (inferior): Tendencia bajista fuerte
- Precio toca banda y regresa → Posible reversión a la media
- Squeeze + Breakout → Trade de alta probabilidad

## ATR — Average True Range (Período 14)

### Fórmula
```
True_Range = MAX(
  High - Low,
  ABS(High - Close_Anterior),
  ABS(Low - Close_Anterior)
)
ATR = EMA(14) del True_Range
```

### Uso en el Sistema
- **Stop Loss**: Entrada ± (1.0 a 1.5) × ATR
- **Filtro de volatilidad**: ATR actual vs ATR promedio 50 períodos
  - ATR actual < 0.5 × ATR_avg → Mercado dormido (no operar)
  - ATR actual > 2.0 × ATR_avg → Volatilidad extrema (reducir posición)
- **TP dinámico**: TP = Entrada + (2.0 a 3.0) × ATR

## ADX — Average Directional Index (Período 14)

### Fórmula
```
+DM = High_actual - High_anterior (si > 0 y > -DM)
-DM = Low_anterior - Low_actual (si > 0 y > +DM)
+DI = 100 × EMA(+DM) / ATR
-DI = 100 × EMA(-DM) / ATR
DX = 100 × ABS(+DI - -DI) / (+DI + -DI)
ADX = EMA(14) del DX
```

### Interpretación
| ADX | Fuerza | Acción |
|-----|--------|--------|
| 0-15 | Ausente | No operar direccional |
| 15-20 | Débil | Esperar confirmación |
| 20-25 | Emergente | Preparar entrada |
| 25-50 | Fuerte | Operar a favor |
| 50-75 | Muy fuerte | Cuidado con agotamiento |
| > 75 | Extremo | Probable reversión |

### Señales DI
- +DI > -DI → Sesgo alcista
- -DI > +DI → Sesgo bajista
- Cruce +DI/-DI con ADX > 25 → Señal fuerte

## Fibonacci

### Niveles de Retroceso
| Nivel | Importancia | Uso |
|-------|-------------|-----|
| 23.6% | Baja | Retroceso superficial (tendencia muy fuerte) |
| 38.2% | Media | Primer soporte/resistencia |
| 50.0% | Alta | Nivel psicológico |
| 61.8% | Muy Alta | Golden Ratio — zona premium |
| 78.6% | Alta | Último nivel antes de invalidar |

### Zona Golden (50% - 61.8%)
- Mayor probabilidad de reacción
- Combinado con S/R horizontal = confluencia potente
- Ideal para entradas en pullback

### Extensiones (para TP)
| Nivel | Uso |
|-------|-----|
| 127.2% | TP conservador |
| 161.8% | TP estándar |
| 200.0% | TP agresivo |
| 261.8% | TP en tendencias fuertes |
