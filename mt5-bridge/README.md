# MT5 Bridge

REST API que expone MetaTrader 5 para el MCP server.

## Requisitos

- Windows 10/11 o Windows Server
- Python 3.12+
- MetaTrader 5 instalado (XM)
- Cuenta demo de XM

## Instalación

```bat
install.bat
```

## Configuración

1. Copia `.env.example` a `.env`
2. Llena con tus credenciales de XM demo:
   - `MT5_LOGIN` — número de cuenta
   - `MT5_PASSWORD` — password
   - `MT5_SERVER` — generalmente `XMGlobal-MT5`
   - `BRIDGE_API_KEY` — genera un key seguro (ej: `openssl rand -hex 32`)

## Ejecución

```bat
start.bat
```

## Endpoints

| Method | Path | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/health` | No | Estado de MT5 |
| GET | `/account` | Sí | Balance, equity, margin |
| GET | `/positions` | Sí | Posiciones abiertas |
| GET | `/symbol/<pair>` | Sí | Info del par (spread, pip value) |
| POST | `/order/open` | Sí | Abrir posición |
| POST | `/order/close` | Sí | Cerrar posición |
| POST | `/order/modify` | Sí | Modificar SL/TP |

Auth: Header `X-Bridge-Api-Key: tu-api-key`

## Ejemplo

```bash
# Health check
curl http://localhost:5000/health

# Open order
curl -X POST http://localhost:5000/order/open \
  -H "X-Bridge-Api-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "EURUSD", "side": "BUY", "lot": 0.05, "sl": 1.0868, "tp": 1.0958}'
```

## Auto-start como servicio

Usa NSSM (Non-Sucking Service Manager):
```bat
nssm install MT5Bridge "C:\Python312\python.exe" "C:\mt5-bridge\app.py"
nssm start MT5Bridge
```
