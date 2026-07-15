# Roadmap de Implementación

## Fase 1: MCP Server (1-2 días)
> EC2 Linux — todo funcional excepto trading real

- [ ] Refactorizar `server.py` (limpiar crypto, enfocar forex)
- [ ] **PostgreSQL** — docker-compose con postgres:16 + migraciones
- [ ] **Analysis tools** (4) — TradingView con screener="forex"
- [ ] **Smart tools** (4) — calculate_lot_size, daily_target, should_trade, optimal_sl_tp
- [ ] **Database tools** (7) — PostgreSQL schema + todas las operaciones
- [ ] **System tools** (3) — safety_rules, health_check, economic_calendar
- [ ] **Trading tools** (7) — mock mode (simula respuestas MT5 para testing)
- [ ] Dockerizar y deploy en EC2
- [ ] Probar con Kiro Web

## Fase 2: MT5 Bridge (1 día)
> VPS Windows — Flask API que conecta a MT5 + XM

- [ ] Setup VPS Windows (contratar o usar existente)
- [ ] Instalar MT5 + login con cuenta demo XM
- [ ] Construir Flask bridge (`app.py`, `mt5_client.py`)
- [ ] Autenticación con API key
- [ ] Endpoints: /order/open, /order/close, /order/modify, /positions, /account, /symbol
- [ ] Endpoint /health para monitoring
- [ ] HTTPS (o VPN entre EC2 y VPS)
- [ ] Auto-start como servicio Windows

## Fase 3: Integración (0.5 días)
> Conectar MCP ↔ Bridge

- [ ] Trading tools llaman al Bridge en vez de mock
- [ ] Configurar IP del Bridge en MCP server
- [ ] Test end-to-end: Kiro Web → MCP → Bridge → MT5 → XM demo
- [ ] Verificar latencia y reconexión

## Fase 4: Agent Prompt + Scheduler (0.5 días)
> Automatización completa

- [ ] System prompt definitivo (AGENT_PROMPT.md)
- [ ] Cron en EC2 que trigger el agente cada hora
- [ ] Horario: solo 07:00-21:00 UTC
- [ ] Logging de cada ciclo
- [ ] Alertas (email/telegram) en errores

## Fase 5: Paper Trading (2-4 semanas)
> Validación sin dinero real

- [ ] Correr 24/5 en cuenta demo XM
- [ ] Trackear métricas diarias
- [ ] Revisar decisiones del agente (auditoría)
- [ ] Ajustar filtros y parámetros según resultados
- [ ] Objetivo: win rate > 55%, profit factor > 1.5

## Fase 6: Producción
> Solo después de validar en demo

- [ ] Crear cuenta real XM (mínimo $500-1000)
- [ ] Cambiar credenciales MT5 a cuenta real
- [ ] Reducir lot sizes inicialmente (0.01)
- [ ] Monitoreo intensivo primera semana
- [ ] Escalar gradualmente

---

## Orden de construcción (empezamos por aquí)

```
1. mcp-trading/src/tools/analysis.py     ← TradingView forex
2. mcp-trading/src/tools/smart.py        ← Lógica de negocio
3. mcp-trading/src/tools/database.py     ← DB schema + tools
4. mcp-trading/src/tools/system.py       ← Health + calendar
5. mcp-trading/src/tools/trading.py      ← Mock mode primero
6. mt5-bridge/                           ← VPS Windows
7. Conectar todo
```
