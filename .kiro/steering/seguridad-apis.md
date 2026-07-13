# Seguridad y APIs Externas

## Seguridad del Sistema
- Nunca almacenar API keys en código fuente — usar `.env`
- JWT con refresh tokens para autenticación
- Rate limiting en endpoints de datos de mercado
- Validar TODOS los inputs con VineJS
- CORS configurado solo para orígenes permitidos
- WebSocket autenticado con token JWT
- Logs de auditoría para operaciones financieras

## API Principal: Massive (Forex Data)

### Base URL
```
https://api.massive.io  (verificar en docs oficiales)
```

### Autenticación
- API Key via header o query param
- Plan actual: **Currencies Basic (Free)**

### Endpoints Disponibles (Plan Free)

| Endpoint | Path | Uso en el Sistema |
|----------|------|-------------------|
| All Tickers | `GET /v3/reference/tickers` | Descubrir pares disponibles |
| Ticker Overview | `GET /v3/reference/tickers/{ticker}` | Detalles de un par |
| Aggregate Bars (OHLC) | `GET /v2/aggs/ticker/{forexTicker}/range/{multiplier}/{timespan}/{from}/{to}` | **PRINCIPAL** — Datos OHLCV multi-temporalidad |
| Daily Market Summary | `GET /v2/aggs/grouped/locale/global/market/fx/{date}` | Resumen diario todos los pares |
| Previous Day Bar | `GET /v2/aggs/ticker/{forexTicker}/prev` | OHLC del día anterior |
| SMA | `GET /v1/indicators/sma/{fxTicker}` | Simple Moving Average |
| EMA | `GET /v1/indicators/ema/{fxTicker}` | Exponential Moving Average |
| MACD | `GET /v1/indicators/macd/{fxTicker}` | MACD (momentum) |
| RSI | `GET /v1/indicators/rsi/{fxTicker}` | Relative Strength Index |
| Exchanges | `GET /v3/reference/exchanges` | Info de exchanges |
| Market Holidays | `GET /v1/marketstatus/upcoming` | Calendario de festivos |
| Market Status | `GET /v1/marketstatus/now` | Estado actual del mercado |

### Endpoints que Requieren Plan Superior (NO disponibles en Free)

| Endpoint | Path | Plan Requerido |
|----------|------|----------------|
| Currency Conversion | `GET /v1/conversion/{from}/{to}` | Starter ($49/mo) |
| Single Ticker Snapshot | `GET /v2/snapshot/locale/global/markets/forex/tickers/{ticker}` | Starter |
| Full Market Snapshot | `GET /v2/snapshot/locale/global/markets/forex/tickers` | Starter |
| Unified Snapshot | `GET /v3/snapshot` | Starter |
| Top Market Movers | `GET /v2/snapshot/locale/global/markets/forex/{direction}` | Starter |
| Quotes (BBO Historical) | `GET /v3/quotes/{fxTicker}` | Starter |
| Last Quote | `GET /v1/last_quote/currencies/{from}/{to}` | Starter |

### Formato de Ticker Forex en Massive
- Formato: `C:EURUSD` (prefijo `C:` + par sin slash)
- Ejemplos: `C:EURUSD`, `C:GBPUSD`, `C:USDJPY`, `C:AUDUSD`

### Parámetros de Aggregate Bars
```
GET /v2/aggs/ticker/C:EURUSD/range/5/minute/2024-01-01/2024-01-31
                              ↑multiplier ↑timespan  ↑from       ↑to

Timespans válidos: minute, hour, day, week, month, quarter, year
```

### Mapeo Temporalidades → Parámetros Massive
| Temporalidad | multiplier | timespan |
|--------------|-----------|----------|
| M5 | 5 | minute |
| M15 | 15 | minute |
| H1 | 1 | hour |
| H4 | 4 | hour |
| D1 | 1 | day |

### Indicadores Técnicos — Parámetros
```
GET /v1/indicators/ema/C:EURUSD?timespan=hour&window=21&series_type=close

Params comunes:
- timespan: minute, hour, day, week, month, quarter, year
- window: período del indicador (ej: 14 para RSI, 21 para EMA)
- series_type: close, open, high, low
- adjusted: true/false
- limit: número de resultados
- order: asc/desc

MACD params adicionales:
- short_window: 12 (EMA rápida)
- long_window: 26 (EMA lenta)
- signal_window: 9 (línea de señal)
```

### Notas Importantes sobre Massive
- Los datos OHLC de Forex se generan a partir de quotes bid/ask (NO trades ejecutados)
- Si no hay nuevos quotes en un intervalo, NO se genera barra (gaps normales)
- Todos los timestamps están en UTC
- El mercado Forex opera 24/5 (lunes-viernes)
- Datos descentralizados: agregados de múltiples bancos y market makers

## Indicadores Calculados Localmente (No disponibles en Massive Free)
Los siguientes indicadores se calculan en nuestro backend a partir de datos OHLCV:
- **Bollinger Bands** (20, 2) — Calculado local con SMA + StdDev
- **ATR** (14) — Calculado local con True Range
- **ADX** (14) — Calculado local con DI+/DI-
- **Fibonacci** — Calculado local con High/Low del swing

## Variables de Entorno Requeridas
```
# App
TZ=UTC
PORT=3333
HOST=localhost
LOG_LEVEL=info
APP_KEY=
NODE_ENV=development

# Database (PostgreSQL)
DB_HOST=127.0.0.1
DB_PORT=5432
DB_USER=forex_user
DB_PASSWORD=forex_pass_dev
DB_DATABASE=forex_trading

# Redis
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=

# Massive API (Forex Data Provider)
MASSIVE_API_KEY=
MASSIVE_BASE_URL=https://api.massive.io

# JWT / Session
SESSION_DRIVER=cookie

# WebSocket
WS_PORT=3334

# Frontend URL (CORS)
FRONTEND_URL=http://localhost:9000
```

## Estrategia de Cache (Redis)
- Datos OHLCV M5: Cache 1 minuto (actualización frecuente)
- Datos OHLCV M15/H1: Cache 5 minutos
- Datos OHLCV H4/D1: Cache 30 minutos
- Indicadores técnicos: Cache igual al timeframe
- Market Status: Cache 5 minutos
- Tickers/Reference data: Cache 24 horas

## Disclaimers Legales
- El sistema NO es asesoría financiera
- Todas las decisiones son responsabilidad del usuario
- El trading de Forex conlleva riesgo de pérdida de capital
- Mostrar disclaimer visible en la UI en todo momento
- No garantizar rendimientos ni porcentajes de éxito
