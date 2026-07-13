# 📈 Trading Forex Gen AI

Sistema de Trading Forex con IA para análisis técnico multi-temporalidad y generación de señales de entrada al mercado.

## Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Frontend | Quasar Framework (Vue 3 + TypeScript) |
| Backend | AdonisJS v6 (TypeScript) |
| Base de Datos | PostgreSQL 16 |
| Cache | Redis 7 |
| WebSocket | AdonisJS WebSocket |
| Charts | Lightweight Charts (TradingView) |
| APIs Datos | Massive (REST + WebSocket) |

## Arquitectura Multi-Agente (Kiro)

El sistema usa agentes especializados de Kiro para desarrollo:

- **forex-trading-agent** — Agente principal orquestador
- **forex-analisis-tecnico** — Indicadores, patrones, confluencias
- **forex-gestion-riesgo** — Cálculo de posiciones, SL/TP, protección de capital
- **forex-senales** — Generación y seguimiento de señales

## Estructura del Proyecto

```
trading-forex-gen-ai/
├── frontend/              # Quasar (Vue 3) SPA/PWA
│   └── src/
│       ├── modules/       # Módulos funcionales
│       ├── components/    # Componentes compartidos
│       ├── stores/        # Pinia stores
│       └── services/      # API, WebSocket
├── backend/               # AdonisJS v6
│   └── app/
│       ├── controllers/   # REST API controllers
│       ├── services/      # Lógica de negocio (indicadores, señales, riesgo)
│       ├── models/        # Lucid ORM models
│       └── middleware/    # Auth, rate limiting
├── .kiro/                 # Configuración de agentes Kiro
│   ├── agents/            # Agentes especializados
│   ├── skills/            # Skills por dominio
│   ├── steering/          # Reglas y convenciones
│   └── prompts/           # System prompts
└── docker-compose.yml     # PostgreSQL + Redis
```

## Inicio Rápido

```bash
# 0. Usar Node 24
nvm use 24

# 1. Iniciar servicios
docker compose up -d

# 2. Backend
cd backend
cp .env.example .env
node ace generate:key   # genera APP_KEY en .env
npm install
node ace migration:run
node ace serve --hmr

# 3. Frontend (otra terminal)
cd frontend
npm install
npx quasar dev
```

## Módulos del Sistema

### 🔬 Análisis Técnico
- Indicadores: EMA (8/21/50/200), RSI (14), MACD (12,26,9), BB (20,2), ATR (14), ADX (14)
- Patrones: Velas japonesas, figuras chartistas, estructura de mercado
- Multi-temporalidad: M5, M15, H1, H4, D1 (top-down analysis)
- Confluencias: Mínimo 3 factores para señal válida

### 🛡️ Gestión de Riesgo
- Cálculo de posición (lot size basado en % riesgo)
- Stop Loss dinámico (ATR + estructura)
- Take Profit multi-nivel (TP1/TP2/TP3 con parciales)
- Correlaciones entre pares
- Monitor de drawdown y exposición

### 🎯 Señales de Trading
- Clasificación: A (alta confianza), B (media), C (no operar)
- Score 1-10 basado en confluencias
- Seguimiento en tiempo real (WebSocket)
- Historial y métricas de rendimiento (win rate, profit factor)

## ⚠️ Disclaimer

Este sistema es una herramienta de **apoyo a la decisión**, NO un sistema de trading automático.
El trading de Forex conlleva riesgo significativo de pérdida de capital. Todas las decisiones
de trading son responsabilidad exclusiva del usuario.
