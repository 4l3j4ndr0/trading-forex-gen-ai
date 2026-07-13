---
name: analisis-tecnico
description: Guía para el módulo de análisis técnico multi-temporalidad. Usar al crear/modificar indicadores, detectores de patrones, análisis de confluencias o visualización de gráficos técnicos.
---

# Skill: Análisis Técnico Multi-Temporalidad

## Estructura del Módulo
```
backend/app/services/analisis/
├── indicators/
│   ├── ema_service.ts          # EMA (8, 21, 50, 200)
│   ├── rsi_service.ts          # RSI (14)
│   ├── macd_service.ts         # MACD (12, 26, 9)
│   ├── bollinger_service.ts    # Bandas de Bollinger (20, 2)
│   ├── atr_service.ts          # ATR (14)
│   ├── adx_service.ts          # ADX (14) con DI+/DI-
│   └── fibonacci_service.ts    # Retrocesos y extensiones
├── patterns/
│   ├── candlestick_service.ts  # Patrones de velas
│   ├── chart_patterns_service.ts # Figuras chartistas
│   └── structure_service.ts    # Estructura de mercado (HH/HL/LL/LH)
├── confluence_service.ts       # Evaluador de confluencias
├── multi_timeframe_service.ts  # Análisis top-down
└── analysis_orchestrator.ts    # Orquestador principal

src/modules/analisis-tecnico/
├── pages/
│   ├── AnalisisTecnico.vue     # Vista principal de análisis
│   └── DetalleAnalisis.vue     # Detalle por par/temporalidad
├── components/
│   ├── ChartTradingView.vue    # Gráfico con lightweight-charts
│   ├── IndicatorPanel.vue      # Panel de indicadores
│   ├── ConfluenceMatrix.vue    # Matriz de confluencias
│   ├── TimeframeSelector.vue   # Selector de temporalidad
│   └── PatternBadge.vue        # Badge de patrón detectado
└── composables/
    ├── useIndicators.ts        # Composable de indicadores
    └── useMultiTimeframe.ts    # Composable multi-TF
```

## Patrón de Servicio de Indicador
```typescript
// backend/app/services/analisis/indicators/ema_service.ts
import type { IOHLCV } from '#services/market/types'

export interface IEMAResult {
  period: number
  values: { timestamp: number; value: number }[]
  currentValue: number
  previousValue: number
  direction: 'bullish' | 'bearish' | 'flat'
}

export class EMAService {
  calculate(candles: IOHLCV[], period: number): IEMAResult {
    const multiplier = 2 / (period + 1)
    const values: { timestamp: number; value: number }[] = []
    let ema = candles[0].close

    for (let i = 1; i < candles.length; i++) {
      ema = (candles[i].close - ema) * multiplier + ema
      values.push({ timestamp: candles[i].timestamp, value: ema })
    }

    const current = values[values.length - 1].value
    const previous = values[values.length - 2].value

    return {
      period,
      values,
      currentValue: current,
      previousValue: previous,
      direction: current > previous ? 'bullish' : current < previous ? 'bearish' : 'flat',
    }
  }
}
```

## Patrón de Evaluación de Confluencia
```typescript
// backend/app/services/analisis/confluence_service.ts
export interface IConfluence {
  factor: string
  description: string
  direction: 'bullish' | 'bearish'
  strength: number  // 1-3
  timeframe: string
}

export interface IConfluenceResult {
  confluences: IConfluence[]
  totalScore: number
  direction: 'bullish' | 'bearish' | 'neutral'
  isValid: boolean  // >= 3 confluences, score >= 7
}
```

## Temporalidades y Períodos de Velas
| Temporalidad | Velas Mínimas | Uso Principal |
|--------------|---------------|---------------|
| M5 | 200 | Timing de entrada |
| M15 | 200 | Confirmación momentum |
| H1 | 200 | Dirección intradía |
| H4 | 200 | Tendencia intermedia (PRINCIPAL) |
| D1 | 100 | Contexto macro |

## Endpoint de Análisis Completo
```
GET /api/v1/analysis/:pair
Query: ?timeframes=M5,M15,H1,H4,D1

Response: {
  data: {
    pair: "EUR/USD",
    timestamp: "2024-...",
    timeframes: {
      D1: { bias: "bullish", indicators: {...}, patterns: [...] },
      H4: { bias: "bullish", indicators: {...}, patterns: [...] },
      ...
    },
    confluences: [...],
    score: 8,
    recommendation: "BUY" | "SELL" | "WAIT"
  }
}
```
