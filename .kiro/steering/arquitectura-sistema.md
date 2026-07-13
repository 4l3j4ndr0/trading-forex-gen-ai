# Arquitectura del Sistema — Forex Trading

## Principios de Arquitectura
- Separación clara entre módulos (análisis, riesgo, señales)
- Services contienen la lógica de negocio pesada
- Controllers solo orquestan (validan, delegan a services, responden)
- Los cálculos de indicadores se hacen en el backend (no en el frontend)
- El frontend muestra resultados y permite interacción

## Flujo de Datos
```
[APIs de Datos] → [Backend: Data Service] → [Cache Redis]
                                           ↓
[Backend: Análisis Service] ← [Market Data]
         ↓
[Backend: Señales Service] ← [Análisis + Riesgo]
         ↓
[WebSocket] → [Frontend: Dashboard en tiempo real]
         ↓
[DB PostgreSQL] → [Historial de señales y trades]
```

## Capas del Backend
1. **Data Layer**: Obtiene datos OHLCV de APIs externas, cachea en Redis
2. **Indicators Layer**: Calcula indicadores técnicos sobre los datos
3. **Analysis Layer**: Interpreta indicadores, detecta patrones, evalúa confluencias
4. **Risk Layer**: Calcula posiciones, SL/TP, valida reglas de riesgo
5. **Signals Layer**: Combina análisis + riesgo → genera señales accionables
6. **Notification Layer**: WebSocket + push notifications para señales

## Estructura de Rutas API
- `/api/v1/market/*` — Datos de mercado (precios, OHLCV, spread)
- `/api/v1/analysis/*` — Análisis técnico y resultados de indicadores
- `/api/v1/signals/*` — Señales de trading (CRUD + evaluación)
- `/api/v1/risk/*` — Cálculos de riesgo y posición
- `/api/v1/trades/*` — Historial de operaciones
- `/api/v1/settings/*` — Configuración del usuario (preferencias, broker)
- `/api/v1/backtest/*` — Backtesting de estrategias

## WebSocket Events
- `market:price_update` — Actualización de precio en tiempo real
- `signal:new` — Nueva señal generada
- `signal:update` — Señal actualizada (TP hit, SL hit, expirada)
- `signal:cancelled` — Señal cancelada
- `analysis:complete` — Análisis terminado para un par

## Base de Datos — Tablas Principales
- `users`: Datos del trader
- `user_settings`: Preferencias (riesgo max, pares favoritos, broker)
- `signals`: Señales generadas con todos los niveles
- `signal_confluences`: Confluencias de cada señal
- `trades`: Operaciones ejecutadas (vinculadas a señal)
- `market_snapshots`: Snapshots de indicadores al momento de la señal
- `pairs`: Pares de divisas configurados
- `economic_calendar`: Eventos económicos de alto impacto
