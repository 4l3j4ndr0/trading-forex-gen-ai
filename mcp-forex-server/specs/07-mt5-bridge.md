# MT5 Bridge — Especificación

## Qué es

Un servicio REST API que corre en un VPS Windows junto a MetaTrader 5. Expone las funciones de MT5 como endpoints HTTP para que el MCP server (Linux) pueda ejecutar operaciones.

## Stack

- **OS:** Windows Server 2022 (o Windows 10/11)
- **Runtime:** Python 3.12
- **Framework:** Flask + waitress (production server)
- **Librería:** MetaTrader5 (pip install MetaTrader5)
- **Auth:** API Key via header `X-Bridge-Api-Key`

## Estructura

```
mt5-bridge/
├── app.py                  # Flask entry point
├── mt5_client.py           # Wrapper de MetaTrader5 lib
├── auth.py                 # Validación de API key
├── config.py               # Settings
├── requirements.txt        # Flask, waitress, MetaTrader5
├── install.bat             # Script de instalación
└── start.bat               # Script para correr como servicio
```

## Endpoints

### Health
```
GET /health
Response: {"status": "ok", "mt5_connected": true, "account": "demo", "broker": "XM"}
```

### Account
```
GET /account
Response: {"balance": 10000, "equity": 10012.5, "margin": 45.0, ...}
```

### Positions
```
GET /positions
Response: [{"ticket": 123, "symbol": "EURUSD", "side": "BUY", "pnl": 12.5, ...}]
```

### Symbol Info
```
GET /symbol/<symbol>
Response: {"spread": 16, "pip_value": 10.0, "digits": 5, ...}
```

### Open Order
```
POST /order/open
Body: {"symbol": "EURUSD", "side": "BUY", "lot": 0.05, "sl": 1.0868, "tp": 1.0958}
Response: {"ticket": 12345678, "entry_price": 1.0898, ...}
```

### Close Order
```
POST /order/close
Body: {"ticket": 12345678}
Response: {"closed": true, "exit_price": 1.0928, "pnl": 15.0}
```

### Modify Order
```
POST /order/modify
Body: {"ticket": 12345678, "sl": 1.0898, "tp": 1.0968}
Response: {"modified": true}
```

## Seguridad

- API Key requerida en todas las requests
- HTTPS via certificado self-signed o Let's Encrypt
- Firewall: solo acepta requests desde la IP del EC2
- MT5 login automático al iniciar el bridge

## Configuración (config.py)

```python
MT5_LOGIN = 12345678          # Número de cuenta XM
MT5_PASSWORD = "xxx"          # Password de la cuenta
MT5_SERVER = "XMGlobal-MT5"   # Servidor del broker
MT5_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"

BRIDGE_PORT = 5000
BRIDGE_API_KEY = "tu-api-key-segura"
ALLOWED_IPS = ["52.201.104.115"]  # IP del EC2
```

## Flujo de una operación

```
1. MCP Tool (open_position) llamado por el agente
2. MCP Server valida safety rules
3. MCP Server envía POST /order/open al Bridge
4. Bridge recibe request, valida API key
5. Bridge llama mt5.order_send() con los parámetros
6. MT5 ejecuta la orden en el broker XM
7. Bridge retorna ticket + entry_price
8. MCP Server registra en DB y retorna al agente
```

## Instalación en VPS Windows

```bat
:: install.bat
pip install flask waitress MetaTrader5
:: Descargar e instalar MT5 de XM: https://www.xm.com/mt5
:: Login con credenciales demo
:: Ejecutar: python app.py
```

## Auto-start (Windows Service)

Opciones:
- NSSM (Non-Sucking Service Manager) → registra app.py como servicio
- Task Scheduler → ejecutar al boot
- PM2 para Windows → process manager

## Reconexión MT5

```python
# mt5_client.py — reconexión automática
def ensure_connected():
    if not mt5.terminal_info():
        mt5.initialize(path=MT5_PATH)
        mt5.login(MT5_LOGIN, MT5_PASSWORD, MT5_SERVER)
```

## Latencia esperada

- MCP → Bridge (internet): 50-100ms
- Bridge → MT5 (local): <5ms
- MT5 → Broker (XM servers): 20-50ms
- **Total:** ~100-200ms por operación
