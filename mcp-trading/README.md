# MCP Trading Server — Crypto (Binance)

MCP Server que expone tools de trading, análisis técnico y gestión de portafolio.
No contiene lógica de decisión — eso lo hace el agente LLM (Kiro Web) que consume el MCP.

## Tools Disponibles (13)

### 📊 Análisis (TradingView real-time)
- `coin_analysis` — Indicadores completos para un par/timeframe
- `multi_timeframe_analysis` — Análisis D1 → 4H → 1H
- `get_market_status` — Overview de todos los pares activos

### 💰 Trading (Binance Futures)
- `open_position` — Abrir posición (con safety checks)
- `close_position` — Cerrar una posición específica
- `close_all_positions` — Cerrar todas las posiciones
- `get_open_positions` — Ver posiciones abiertas con PnL
- `get_account_balance` — Balance de la cuenta

### 📝 Base de Datos
- `register_trade` — Registrar trade en DB
- `trade_history` — Historial de trades por período
- `performance_stats` — Estadísticas de rendimiento
- `log_hourly_decision` — Log de decisiones por hora

### ⚙️ Configuración
- `get_safety_rules` — Reglas de seguridad activas

## Setup Local

```bash
cd mcp-trading
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Editar .env con tus API keys de Binance Testnet
```

### Correr en modo stdio (local, Kiro Desktop)
```bash
python server.py
```

### Correr en modo HTTP (para conectar remotamente)
```bash
python server.py --http
# o
MCP_TRANSPORT=http python server.py
```

## Deploy en EC2

### Prerrequisitos en el EC2
- Docker + Docker Compose instalados
- Puerto 8000 abierto en el Security Group

### Pasos
```bash
# 1. Crear tu .env con las API keys de Binance
cp .env.example .env
nano .env

# 2. Deploy
./deploy.sh ubuntu@<tu-ec2-ip> ~/.ssh/tu-key.pem
```

### O manualmente en el EC2:
```bash
ssh ubuntu@<tu-ec2-ip>
cd /opt/mcp-trading
docker compose up -d --build
# Verificar
docker compose logs -f
```

## Conectar desde Kiro Web

Una vez desplegado, agrega esto a tu configuración de MCP:

```json
{
  "mcpServers": {
    "trading": {
      "url": "http://<EC2_PUBLIC_IP>:8000/mcp",
      "type": "http"
    }
  }
}
```

## Conectar desde Kiro Desktop (local)

```json
{
  "mcpServers": {
    "trading": {
      "command": "/path/to/mcp-trading/.venv/bin/python",
      "args": ["/path/to/mcp-trading/server.py"]
    }
  }
}
```

## Safety Rules

Las reglas de seguridad se aplican **a nivel de tool** — ningún cliente puede saltarlas:

| Regla | Default | Descripción |
|-------|---------|-------------|
| MAX_OPEN_POSITIONS | 3 | Máximo trades abiertos simultáneos |
| MAX_LOT_SIZE | 0.05 | Tamaño máximo de posición |
| MAX_DAILY_LOSS_USD | $50 | Si se pierde esto, no más trades hoy |
| MAX_CONSECUTIVE_LOSSES | 5 | Pausa automática tras 5 pérdidas seguidas |
| MIN_BALANCE_USD | $100 | Balance mínimo para operar |
| KILL_SWITCH | false | Emergencia: detiene todo |

## Fase actual: MVP (Testnet)

- ✅ Binance Futures Testnet (dinero ficticio)
- ✅ SQLite local para la DB
- ✅ 13 tools funcionales
- ⬜ Validar win rate 2-4 semanas
- ⬜ Migrar a Binance real con micro-lotes
