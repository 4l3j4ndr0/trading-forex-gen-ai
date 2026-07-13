---
name: senales
description: Guía para el módulo de señales de trading — generación, evaluación, emisión y seguimiento de señales. Usar al trabajar con la lógica de señales o el panel de trading.
---

# Skill: Señales de Trading

## Estructura del Módulo
```
backend/app/services/senales/
├── signal_generator.ts       # Generador de señales
├── signal_evaluator.ts       # Evaluador de calidad (score)
├── signal_tracker.ts         # Seguimiento en tiempo real
├── signal_notifier.ts        # Notificaciones WebSocket/Push
└── signal_historian.ts       # Historial y métricas

backend/app/models/
├── signal.ts                 # Modelo de señal
├── signal_confluence.ts      # Modelo de confluencia
└── trade.ts                  # Modelo de trade ejecutado

src/modules/senales/
├── pages/
│   ├── PanelSenales.vue      # Panel principal de señales activas
│   ├── HistorialSenales.vue  # Historial con filtros y métricas
│   └── DetalleSenal.vue      # Detalle completo de una señal
├── components/
│   ├── SignalCard.vue         # Card de señal individual
│   ├── SignalBadge.vue        # Badge A/B/C con color
│   ├── SignalTimeline.vue     # Timeline de estados
│   ├── ConfluenceList.vue     # Lista de confluencias
│   └── PerformanceStats.vue   # Estadísticas de rendimiento
└── composables/
    ├── useSignals.ts          # Composable principal de señales
    └── useSignalWebSocket.ts  # Composable de WebSocket
```

## Modelo de Señal (DB)
```typescript
// backend/app/models/signal.ts
export default class Signal extends BaseModel {
  @column.isPrimary() declare id: number
  @column() declare userId: number
  @column() declare pair: string
  @column() declare direction: 'buy' | 'sell'
  @column() declare type: 'continuation' | 'reversal' | 'breakout'
  @column() declare classification: 'A' | 'B' | 'C'
  @column() declare score: number  // 1-10
  @column() declare entryPrice: number
  @column() declare stopLoss: number
  @column() declare takeProfit1: number
  @column() declare takeProfit2: number
  @column() declare takeProfit3: number
  @column() declare lotSize: number
  @column() declare riskPercent: number
  @column() declare riskReward: number
  @column() declare status: SignalStatus
  @column() declare confluenceCount: number
  @column() declare timeframeAlignment: string  // JSON: {"D1":"bullish",...}
  @column() declare invalidationLevel: number
  @column() declare notes: string
  @column() declare expiresAt: DateTime
  @column.dateTime({ autoCreate: true }) declare createdAt: DateTime
  @column.dateTime() declare closedAt: DateTime | null
  @column() declare pnlPips: number | null
  @column() declare pnlMoney: number | null

  @hasMany(() => SignalConfluence) declare confluences: HasMany<typeof SignalConfluence>
}

type SignalStatus =
  | 'pending'       // Generada, esperando ejecución
  | 'active'        // Ejecutada por el usuario
  | 'hit_tp1'       // TP1 alcanzado
  | 'hit_tp2'       // TP2 alcanzado
  | 'hit_tp3'       // TP3 alcanzado (trade completo)
  | 'stopped_out'   // SL tocado
  | 'breakeven'     // Cerrada en breakeven
  | 'cancelled'     // Cancelada (condiciones invalidadas)
  | 'expired'       // Expirada (4h sin ejecutar)
  | 'manual_close'  // Cerrada manualmente
```

## Flujo de Generación de Señal
```
1. [Trigger] → Evento de análisis completo o petición manual
2. [Analysis] → Obtener resultado de Agente Análisis Técnico
3. [Validate] → Verificar confluencias >= 3 y score >= 6
4. [Risk] → Pasar por Agente de Riesgo (posición, SL/TP, exposición)
5. [Classify] → Asignar clasificación A/B/C según score
6. [Emit] → Guardar en DB + Notificar via WebSocket
7. [Track] → Monitorear precio vs niveles de la señal
8. [Close] → Actualizar estado cuando toque SL/TP/expire
```

## Endpoints de Señales
```
GET    /api/v1/signals              — Listar señales (filtros: status, pair, classification)
GET    /api/v1/signals/:id          — Detalle de una señal
POST   /api/v1/signals/generate     — Solicitar generación de señal para un par
PUT    /api/v1/signals/:id/activate — Marcar como ejecutada por el usuario
PUT    /api/v1/signals/:id/close    — Cerrar manualmente
DELETE /api/v1/signals/:id/cancel   — Cancelar señal

GET    /api/v1/signals/stats        — Estadísticas (win rate, PF, expectancy)
GET    /api/v1/signals/history      — Historial con paginación y filtros
```

## WebSocket Events
```typescript
// Servidor emite:
ws.emit('signal:new', { signal: ISignalPayload })
ws.emit('signal:update', { id: number, status: string, pnl?: number })
ws.emit('signal:tp_hit', { id: number, tpLevel: 1|2|3, price: number })
ws.emit('signal:stopped', { id: number, price: number, pnl: number })
ws.emit('signal:expired', { id: number })

// Cliente emite:
ws.emit('signal:subscribe', { pairs: string[] })
ws.emit('signal:unsubscribe', { pairs: string[] })
```

## Métricas de Rendimiento
```typescript
interface IPerformanceStats {
  totalSignals: number
  executed: number
  winRate: number           // % de trades ganadores
  profitFactor: number      // Ganancias / Pérdidas
  averageRR: number         // R:R promedio conseguido
  expectancy: number        // Ganancia esperada por trade
  maxDrawdown: number       // Máximo drawdown %
  sharpeRatio: number
  bestTrade: { pair: string; pips: number }
  worstTrade: { pair: string; pips: number }
  byClassification: {
    A: { count: number; winRate: number }
    B: { count: number; winRate: number }
  }
}
```
