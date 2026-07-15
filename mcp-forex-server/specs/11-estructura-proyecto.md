# Estructura del Proyecto

```
mcp-forex/
│
├── specs/                          # Especificaciones (lo que estamos haciendo)
│   ├── 01-arquitectura.md
│   ├── 02-tools-analysis.md
│   ├── 03-tools-trading.md
│   ├── 04-tools-smart.md
│   ├── 05-tools-database.md
│   ├── 06-tools-system.md
│   ├── 07-mt5-bridge.md
│   ├── 08-agent-prompt.md
│   ├── 09-safety-rules.md
│   └── 10-roadmap.md
│
├── server/                         # MCP Server (EC2 Linux)
│   ├── server.py                   # Entry point FastMCP (stdio / HTTP)
│   ├── src/
│   │   ├── __init__.py
│   │   ├── tools/
│   │   │   ├── __init__.py         # register_all_tools(mcp)
│   │   │   ├── analysis.py         # 4 tools — TradingView TA
│   │   │   ├── trading.py          # 7 tools — MT5 Bridge client
│   │   │   ├── smart.py            # 4 tools — Lógica de negocio
│   │   │   ├── database.py         # 9 tools — CRUD PostgreSQL
│   │   │   └── system.py           # 3 tools — Health + calendar
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py           # Settings dataclass (lee de BD)
│   │   │   ├── db.py               # Pool de conexiones PostgreSQL
│   │   │   ├── safety.py           # SafetyGuard (valida reglas antes de operar)
│   │   │   └── sessions.py         # Horarios forex (London/NY/Tokyo)
│   │   ├── clients/
│   │   │   ├── __init__.py
│   │   │   ├── mt5_bridge.py       # HTTP client al VPS Windows
│   │   │   └── tradingview.py      # Wrapper TradingView TA
│   │   └── external/
│   │       ├── __init__.py
│   │       └── calendar.py         # Scraper calendario económico
│   ├── migrations/
│   │   ├── 001_create_trades.sql
│   │   ├── 002_create_hourly_logs.sql
│   │   ├── 003_create_daily_summary.sql
│   │   ├── 004_create_economic_events.sql
│   │   └── 005_create_trading_settings.sql
│   ├── tests/
│   │   ├── test_analysis.py
│   │   ├── test_trading.py
│   │   ├── test_smart.py
│   │   ├── test_database.py
│   │   └── test_safety.py
│   ├── Dockerfile
│   ├── docker-compose.yml          # MCP server + PostgreSQL
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
├── bridge/                         # MT5 Bridge (VPS Windows)
│   ├── app.py                      # Flask entry point
│   ├── mt5_client.py               # Wrapper MetaTrader5 lib
│   ├── auth.py                     # API key validation
│   ├── config.py                   # MT5 login, broker, port
│   ├── requirements.txt            # Flask, waitress, MetaTrader5
│   ├── install.bat                 # Setup script Windows
│   ├── start.bat                   # Run as service
│   └── README.md
│
├── agent/                          # Configuración del agente
│   ├── AGENT_PROMPT.md             # System prompt completo
│   ├── kiro-mcp-config.json        # Config MCP para Kiro Web
│   └── cron/
│       └── trigger.sh              # Script que activa el agente cada hora
│
├── deploy/                         # Scripts de deployment
│   ├── ec2-setup.sh                # Setup inicial del EC2
│   ├── deploy-server.sh            # Build + deploy MCP server
│   ├── nginx.conf                  # Config nginx para HTTPS
│   └── docker-compose.prod.yml     # Producción (con restart policies)
│
├── .gitignore
└── README.md                       # Overview del proyecto completo
```

## Responsabilidad de cada carpeta

| Carpeta | Dónde corre | Qué hace |
|---------|-------------|----------|
| `specs/` | Local (documentación) | Especificaciones del sistema |
| `server/` | EC2 Linux (Docker) | MCP server — expone 27 tools |
| `bridge/` | VPS Windows | Conecta con MT5 + XM broker |
| `agent/` | Kiro Web / API | Prompt + config del agente LLM |
| `deploy/` | CI/CD o manual | Scripts de infraestructura |

## docker-compose.yml (server/)

```yaml
services:
  mcp-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MCP_TRANSPORT=http
      - MCP_HOST=0.0.0.0
      - MCP_PORT=8000
      - DATABASE_URL=postgresql://forex_user:forex_pass@postgres:5432/forex_trading
      - MT5_BRIDGE_URL=https://<vps-ip>:5000
      - MT5_BRIDGE_API_KEY=${MT5_BRIDGE_API_KEY}
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_USER=forex_user
      - POSTGRES_PASSWORD=forex_pass
      - POSTGRES_DB=forex_trading
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U forex_user"]
      interval: 5s
      timeout: 3s
      retries: 5
    restart: unless-stopped

volumes:
  pgdata:
```
