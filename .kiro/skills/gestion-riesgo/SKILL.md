---
name: gestion-riesgo
description: Guía para el módulo de gestión de riesgo — cálculo de posiciones, SL/TP, correlaciones y protección de capital. Usar al trabajar con calculadoras de riesgo o validaciones pre-trade.
---

# Skill: Gestión de Riesgo

## Estructura del Módulo
```
backend/app/services/riesgo/
├── position_calculator.ts    # Cálculo de tamaño de posición
├── stop_loss_service.ts      # SL dinámico basado en ATR/estructura
├── take_profit_service.ts    # TP multi-nivel con parciales
├── correlation_service.ts    # Evaluación de correlación entre pares
├── exposure_service.ts       # Exposición total del portafolio
├── drawdown_monitor.ts       # Monitor de drawdown diario/semanal
└── risk_validator.ts         # Checklist pre-trade completa

src/modules/gestion-riesgo/
├── pages/
│   ├── GestionRiesgo.vue           # Dashboard de riesgo
│   └── CalculadoraPosicion.vue     # Calculadora interactiva
├── components/
│   ├── RiskSemaphore.vue           # Semáforo visual de riesgo
│   ├── PositionSizeCalc.vue        # Widget calculadora
│   ├── ExposureGauge.vue           # Gauge de exposición
│   ├── CorrelationMatrix.vue       # Matriz visual de correlaciones
│   └── DrawdownChart.vue           # Gráfico de drawdown histórico
└── composables/
    ├── useRiskCalculator.ts        # Composable de cálculos
    └── usePortfolioExposure.ts     # Composable de exposición
```

## Cálculo de Posición — Implementación
```typescript
// backend/app/services/riesgo/position_calculator.ts
export interface IPositionCalcInput {
  balance: number
  riskPercent: number      // 0.01 = 1%
  entryPrice: number
  stopLossPrice: number
  pair: string
  accountCurrency: string  // 'USD'
}

export interface IPositionCalcResult {
  lotSize: number
  riskInMoney: number
  pipsAtRisk: number
  pipValue: number
  maxLoss: number
}

export class PositionCalculator {
  calculate(input: IPositionCalcInput): IPositionCalcResult {
    const riskInMoney = input.balance * input.riskPercent
    const pipSize = this.getPipSize(input.pair)
    const pipsAtRisk = Math.abs(input.entryPrice - input.stopLossPrice) / pipSize
    const pipValue = this.getPipValue(input.pair, input.accountCurrency)
    const lotSize = riskInMoney / (pipsAtRisk * pipValue)

    return {
      lotSize: Math.floor(lotSize * 100) / 100, // Redondear a 0.01
      riskInMoney,
      pipsAtRisk,
      pipValue,
      maxLoss: pipsAtRisk * pipValue * lotSize,
    }
  }

  private getPipSize(pair: string): number {
    // JPY pairs: 0.01, others: 0.0001
    return pair.includes('JPY') ? 0.01 : 0.0001
  }

  private getPipValue(pair: string, accountCurrency: string): number {
    // Standard lot (100,000 units)
    // Para USD como moneda de cuenta y pares XXX/USD: $10 per pip
    // Para pares USD/XXX: $10 / precio actual
    // Para crosses: requiere conversión
    return 10 // Simplificado — implementar conversión real
  }
}
```

## Stop Loss Service
```typescript
export interface IStopLossInput {
  entryPrice: number
  direction: 'buy' | 'sell'
  atr: number
  nearestSR: number  // Soporte/Resistencia más cercano
  method: 'atr' | 'structure' | 'hybrid'
}

export interface IStopLossResult {
  price: number
  pips: number
  method: string
  rationale: string
}

// Método híbrido (recomendado):
// 1. Calcular SL por ATR (1.5x)
// 2. Buscar estructura (S/R) más allá del SL
// 3. Usar el que esté más lejos + buffer de 5-10 pips
```

## Take Profit Multi-Nivel
```typescript
export interface ITakeProfitResult {
  tp1: { price: number; pips: number; percentage: 50; rr: number }
  tp2: { price: number; pips: number; percentage: 30; rr: number }
  tp3: { price: number; pips: number; percentage: 20; rr: number }
  averageRR: number
}
```

## Correlaciones de Pares (Valores Típicos)
```typescript
const CORRELATIONS: Record<string, Record<string, number>> = {
  'EUR/USD': { 'GBP/USD': 0.85, 'USD/CHF': -0.90, 'AUD/USD': 0.60 },
  'GBP/USD': { 'EUR/USD': 0.85, 'EUR/GBP': -0.70, 'GBP/JPY': 0.80 },
  'AUD/USD': { 'NZD/USD': 0.90, 'EUR/USD': 0.60, 'USD/CAD': -0.55 },
  // ... completar
}

// Regla: Si |correlación| > 0.75 → Reducir exposición combinada a max 2%
```

## Endpoints
- `POST /api/v1/risk/calculate-position` — Calcular lote
- `POST /api/v1/risk/validate-trade` — Validación pre-trade completa
- `GET /api/v1/risk/exposure` — Exposición actual del portafolio
- `GET /api/v1/risk/drawdown` — Drawdown diario/semanal/mensual
- `GET /api/v1/risk/correlations/:pair` — Correlaciones de un par
