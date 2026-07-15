# MCP Forex Trading — Especificación del Sistema

## Visión General

Sistema de trading automatizado para Forex que usa un MCP server como capa de herramientas y un agente LLM (Claude) como decisor. El agente se ejecuta cada hora durante las sesiones de London y New York, analiza el mercado, y ejecuta operaciones en MetaTrader 5 via un broker (XM).

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SCHEDULER (Cron cada hora)                         │
│               Activo: 07:00 - 21:00 UTC (London + NY)                │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       🤖 AGENTE LLM (Claude)                         │
│                                                                       │
│  • System Prompt: AGENT_PROMPT.md                                    │
│  • Consume: MCP Forex Trading Server (25 tools)                      │
│  • Decide: 5 filtros + target diario 1%                              │
│  • Ejecuta: Órdenes via MT5 Bridge                                   │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    MCP FOREX TRADING SERVER                           │
│                    (FastMCP — Python — EC2 Linux)                     │
│                                                                       │
│  25 tools organizados en 5 dominios:                                 │
│  • Analysis (4) — TradingView TA                                     │
│  • Trading (7) — MT5 Bridge                                          │
│  • Smart (4) — Lógica de negocio                                     │
│  • Database (7) — Histórico y tracking                               │
│  • System (3) — Salud y configuración                                │
└──────────────────┬────────────────────────────┬─────────────────────┘
                   │                            │
                   ▼                            ▼
┌──────────────────────────┐       ┌──────────────────────────┐
│  🖥️ VPS WINDOWS          │       │  🗄️ PostgreSQL 16        │
│                          │       │  (Docker — mismo EC2)    │
│  MetaTrader 5 + XM      │       │                          │
│  Bridge API (Flask)      │       │  • trades                │
│  Puerto: 5000            │       │  • hourly_logs           │
│  Auth: API Key           │       │  • daily_summary         │
│                          │       │  • economic_events       │
└──────────────────────────┘       └──────────────────────────┘
```

## Componentes

### 1. MCP Server (EC2 Linux)
- **Runtime:** Python 3.12+ / FastMCP
- **Transporte:** Streamable HTTP (HTTPS via nginx)
- **Dominio:** `mcp-trading.awslearn.cloud`
- **Contenedor:** Docker
- **Credenciales MT5:** Via headers HTTP del cliente

### 2. MT5 Bridge (VPS Windows)
- **Runtime:** Python 3.12 + Flask + MetaTrader5 lib
- **Puerto:** 5000 (interno) — expuesto via HTTPS o VPN
- **Auth:** API Key en header
- **Broker:** XM (cuenta demo primero, luego real)
- **MT5:** Corriendo 24/7, login automático

### 3. Agente LLM
- **Modelo:** Claude (via Kiro Web o API directa)
- **Trigger:** Cron cada hora (07:00-21:00 UTC)
- **Conexión:** MCP streamable-http con headers

### 4. Base de Datos
- **Engine:** PostgreSQL 16 (contenedor Docker en el mismo EC2)
- **Conexión:** `psycopg2` via `DATABASE_URL`
- **Migraciones:** Scripts SQL versionados
- **Tablas:** trades, hourly_logs, daily_summary, economic_events

## Pares a Operar

| Par | Sesión Óptima | Spread típico XM | Pip value (1 lot) |
|-----|--------------|-------------------|-------------------|
| EUR/USD | London + NY | 1.6 pips | $10 |
| GBP/USD | London + NY | 2.1 pips | $10 |
| USD/JPY | Tokyo + NY | 1.8 pips | ~$6.70 |
| AUD/USD | Tokyo + London | 1.8 pips | $10 |
| USD/CAD | NY | 2.2 pips | ~$7.50 |
| EUR/GBP | London | 2.0 pips | ~$12.50 |

## Sesiones de Trading

| Sesión | Horario UTC | Características |
|--------|-------------|-----------------|
| Tokyo | 00:00 - 09:00 | Baja volatilidad, rangos |
| London | 07:00 - 16:00 | Alta volatilidad, breakouts |
| New York | 12:00 - 21:00 | Continuaciones, reversiones |
| Overlap | 12:00 - 16:00 | Máxima liquidez |

**El agente solo opera:** 07:00 - 21:00 UTC (London + NY)

## Objetivo de Rentabilidad

- **Target diario:** 1% del balance
- **Ejemplo:** Balance $10,000 → Target $100/día
- **Si alcanza el target:** No más trades ese día
- **Si pierde 1%:** Stop loss diario, no más trades

## Stack Tecnológico

| Componente | Tecnología |
|-----------|-----------|
| MCP Server | Python + FastMCP + Docker |
| MT5 Bridge | Python + Flask + MetaTrader5 |
| Análisis | TradingView TA (tradingview-ta) |
| Calendario | Web scraping Forex Factory |
| Database | PostgreSQL 16 (Docker) + psycopg2 |
| Deploy MCP | EC2 Linux + nginx + certbot |
| Deploy Bridge | VPS Windows |
| Agente | Claude via Kiro Web / API |
| Scheduler | Cron (EC2) o CloudWatch Events |
