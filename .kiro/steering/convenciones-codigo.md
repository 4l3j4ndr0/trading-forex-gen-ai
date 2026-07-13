# Convenciones de Código — Forex Trading System

## Frontend (Quasar / Vue 3)
- Usar `<script setup lang="ts">` en todos los componentes
- State management con Pinia (stores en `src/stores/`)
- Componentes Quasar preferidos: QTable, QCard, QChip, QBadge, QDialog, QTabs
- Peticiones HTTP via `src/services/api.ts` (wrapper de fetch con JWT)
- Charts con `lightweight-charts` (TradingView) o `apexcharts`
- WebSocket para datos en tiempo real via `src/services/websocket.ts`
- Rutas lazy-loaded con `() => import('pages/...')`

## Backend (AdonisJS v6)
- TypeScript estricto, usar imports con alias `#controllers/*`, `#models/*`, etc.
- Un controller por dominio: `analisis_controller.ts`, `senales_controller.ts`, `riesgo_controller.ts`
- Validación con VineJS (`#validators/*`)
- Migraciones en `backend/database/migrations/` con timestamps
- Responses JSON consistentes: `{ data, meta? }` en éxito, `{ message, errors? }` en error
- Services para lógica pesada de cálculos (indicadores, señales)

## Nombrado
- Archivos backend: `snake_case.ts`
- Componentes Vue: `PascalCase.vue`
- Stores Pinia: `camelCase.ts` (ej: `tradingSignals.ts`, `marketData.ts`)
- Tablas DB: `snake_case` plural (ej: `signals`, `trades`, `market_data`)
- Columnas DB: `snake_case` (ej: `stop_loss`, `take_profit_1`, `entry_price`)
- Interfaces/Types: `PascalCase` con prefijo `I` para interfaces (ej: `ISignal`, `IIndicatorResult`)

## Estructura de Módulos Frontend
```
src/
├── modules/
│   ├── analisis-tecnico/    # Componentes de análisis
│   ├── gestion-riesgo/      # Calculadoras de riesgo
│   ├── senales/             # Panel de señales
│   ├── dashboard/           # Vista principal
│   └── historial/           # Historial y métricas
├── components/              # Componentes compartidos (charts, badges)
├── stores/                  # Pinia stores globales
├── services/                # API, WebSocket, utilidades
└── composables/             # Composables reutilizables
```

## Git
- Ramas: `feature/`, `fix/`, `chore/`
- Commits: conventional commits en español con gitmoji
  - ✨ feat(señales): agregar filtro por confluencia
  - 🐛 fix(riesgo): corregir cálculo de lot size
  - 📊 feat(charts): implementar gráfico multi-temporalidad
  - 🔧 chore: actualizar dependencias
  - ♻️ refactor(indicadores): optimizar cálculo de EMA
  - ✅ test: agregar tests de cálculo RSI
