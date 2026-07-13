---
name: massive-api
description: Guía de integración con la API de Massive para datos Forex. Usar al implementar servicios de datos de mercado, llamadas a endpoints OHLCV, indicadores técnicos o market status.
---

# Skill: Massive API — Forex Data Integration

## Estructura del Módulo de Datos
```
backend/app/services/market/
├── massive_client.ts          # HTTP client configurado para Massive
├── candles_service.ts         # Obtener OHLCV (Aggregate Bars)
├── indicators_api_service.ts  # Indicadores de Massive (EMA, SMA, MACD, RSI)
├── market_status_service.ts   # Estado del mercado y holidays
├── tickers_service.ts         # Gestión de pares disponibles
├── cache_service.ts           # Cache Redis para datos de mercado
└── types.ts                   # Interfaces compartidas
```

## Massive Client Base
```typescript
// backend/app/services/market/massive_client.ts
import env from '#start/env'

export class MassiveClient {
  private baseUrl: string
  private apiKey: string

  constructor() {
    this.baseUrl = env.get('MASSIVE_BASE_URL')
    this.apiKey = env.get('MASSIVE_API_KEY')
  }

  async get<T>(path: string, params?: Record<string, string | number | boolean>): Promise<T> {
    const url = new URL(path, this.baseUrl)
    url.searchParams.set('apiKey', this.apiKey)

    if (params) {
      for (const [key, value] of Object.entries(params)) {
        url.searchParams.set(key, String(value))
      }
    }

    const response = await fetch(url.toString())

    if (!response.ok) {
      throw new Error(`Massive API error: ${response.status} ${response.statusText}`)
    }

    return response.json() as Promise<T>
  }

  // Helper: Convierte par "EUR/USD" al formato Massive "C:EURUSD"
  static formatTicker(pair: string): string {
    return `C:${pair.replace('/', '')}`
  }

  // Helper: Convierte "C:EURUSD" al formato legible "EUR/USD"
  static parseTicker(ticker: string): string {
    const raw = ticker.replace('C:', '')
    return `${raw.slice(0, 3)}/${raw.slice(3)}`
  }
}
```

## Servicio de Velas (OHLCV)
```typescript
// backend/app/services/market/candles_service.ts
import { MassiveClient } from './massive_client.js'

export type Timeframe = 'M5' | 'M15' | 'H1' | 'H4' | 'D1'

interface TimeframeConfig {
  multiplier: number
  timespan: 'minute' | 'hour' | 'day'
}

const TIMEFRAME_MAP: Record<Timeframe, TimeframeConfig> = {
  M5:  { multiplier: 5, timespan: 'minute' },
  M15: { multiplier: 15, timespan: 'minute' },
  H1:  { multiplier: 1, timespan: 'hour' },
  H4:  { multiplier: 4, timespan: 'hour' },
  D1:  { multiplier: 1, timespan: 'day' },
}

export interface IOHLCV {
  timestamp: number   // Unix ms
  open: number
  high: number
  low: number
  close: number
  volume: number
  vwap?: number
  transactions?: number
}

interface MassiveAggsResponse {
  ticker: string
  queryCount: number
  resultsCount: number
  adjusted: boolean
  results: Array<{
    o: number   // open
    h: number   // high
    l: number   // low
    c: number   // close
    v: number   // volume
    vw?: number // vwap
    t: number   // timestamp (Unix ms)
    n?: number  // number of transactions
  }>
  status: string
  request_id: string
}

export class CandlesService {
  private client: MassiveClient

  constructor() {
    this.client = new MassiveClient()
  }

  async getCandles(pair: string, timeframe: Timeframe, from: string, to: string): Promise<IOHLCV[]> {
    const ticker = MassiveClient.formatTicker(pair)
    const config = TIMEFRAME_MAP[timeframe]

    const path = `/v2/aggs/ticker/${ticker}/range/${config.multiplier}/${config.timespan}/${from}/${to}`

    const response = await this.client.get<MassiveAggsResponse>(path, {
      adjusted: true,
      sort: 'asc',
      limit: 5000,
    })

    return (response.results || []).map((bar) => ({
      timestamp: bar.t,
      open: bar.o,
      high: bar.h,
      low: bar.l,
      close: bar.c,
      volume: bar.v,
      vwap: bar.vw,
      transactions: bar.n,
    }))
  }

  async getPreviousDay(pair: string): Promise<IOHLCV | null> {
    const ticker = MassiveClient.formatTicker(pair)
    const response = await this.client.get<MassiveAggsResponse>(
      `/v2/aggs/ticker/${ticker}/prev`
    )
    if (!response.results?.length) return null
    const bar = response.results[0]
    return {
      timestamp: bar.t,
      open: bar.o,
      high: bar.h,
      low: bar.l,
      close: bar.c,
      volume: bar.v,
      vwap: bar.vw,
    }
  }
}
```

## Servicio de Indicadores (via Massive API)
```typescript
// backend/app/services/market/indicators_api_service.ts
import { MassiveClient } from './massive_client.js'

interface MassiveIndicatorResponse {
  results: {
    underlying: { url: string }
    values: Array<{
      timestamp: number
      value: number
      // MACD adicional:
      signal?: number
      histogram?: number
    }>
  }
  status: string
}

export class IndicatorsApiService {
  private client: MassiveClient

  constructor() {
    this.client = new MassiveClient()
  }

  // EMA disponible en plan Free
  async getEMA(pair: string, window: number, timespan: string = 'hour'): Promise<{ timestamp: number; value: number }[]> {
    const ticker = MassiveClient.formatTicker(pair)
    const response = await this.client.get<MassiveIndicatorResponse>(
      `/v1/indicators/ema/${ticker}`,
      { timespan, window, series_type: 'close', order: 'asc', limit: 200 }
    )
    return response.results.values
  }

  // SMA disponible en plan Free
  async getSMA(pair: string, window: number, timespan: string = 'hour'): Promise<{ timestamp: number; value: number }[]> {
    const ticker = MassiveClient.formatTicker(pair)
    const response = await this.client.get<MassiveIndicatorResponse>(
      `/v1/indicators/sma/${ticker}`,
      { timespan, window, series_type: 'close', order: 'asc', limit: 200 }
    )
    return response.results.values
  }

  // RSI disponible en plan Free
  async getRSI(pair: string, window: number = 14, timespan: string = 'hour'): Promise<{ timestamp: number; value: number }[]> {
    const ticker = MassiveClient.formatTicker(pair)
    const response = await this.client.get<MassiveIndicatorResponse>(
      `/v1/indicators/rsi/${ticker}`,
      { timespan, window, series_type: 'close', order: 'asc', limit: 200 }
    )
    return response.results.values
  }

  // MACD disponible en plan Free
  async getMACD(
    pair: string,
    timespan: string = 'hour',
    shortWindow: number = 12,
    longWindow: number = 26,
    signalWindow: number = 9
  ): Promise<{ timestamp: number; value: number; signal?: number; histogram?: number }[]> {
    const ticker = MassiveClient.formatTicker(pair)
    const response = await this.client.get<MassiveIndicatorResponse>(
      `/v1/indicators/macd/${ticker}`,
      {
        timespan,
        short_window: shortWindow,
        long_window: longWindow,
        signal_window: signalWindow,
        series_type: 'close',
        order: 'asc',
        limit: 200,
      }
    )
    return response.results.values
  }
}
```

## Estrategia de Indicadores: API vs Local

| Indicador | Fuente | Razón |
|-----------|--------|-------|
| EMA (8, 21, 50, 200) | **Massive API** | Disponible en plan Free |
| SMA | **Massive API** | Disponible en plan Free |
| RSI (14) | **Massive API** | Disponible en plan Free |
| MACD (12, 26, 9) | **Massive API** | Disponible en plan Free |
| Bollinger Bands (20, 2) | **Local** (backend) | No disponible en Massive |
| ATR (14) | **Local** (backend) | No disponible en Massive |
| ADX (14) | **Local** (backend) | No disponible en Massive |
| Fibonacci | **Local** (backend) | Cálculo sobre swings |

## Cache Strategy (Redis Keys)
```
forex:candles:{pair}:{timeframe}:{date}    → TTL según TF
forex:indicator:ema:{pair}:{window}:{tf}   → TTL = timeframe
forex:indicator:rsi:{pair}:{tf}            → TTL = timeframe
forex:indicator:macd:{pair}:{tf}           → TTL = timeframe
forex:market_status                         → TTL = 5 min
forex:tickers                               → TTL = 24h
```

## Pares Soportados (Tickers Massive)
```
Majors:   C:EURUSD, C:GBPUSD, C:USDJPY, C:USDCHF, C:AUDUSD, C:NZDUSD, C:USDCAD
Crosses:  C:EURGBP, C:EURJPY, C:GBPJPY, C:AUDNZD, C:EURAUD, C:EURCHF
Exóticos: C:USDMXN, C:USDZAR, C:USDTRY
```

## Notas Importantes
- Las barras OHLC de Forex se generan a partir de QUOTES (bid/ask), NO trades
- Si no hay quotes en un intervalo → NO se genera barra (gap esperado)
- Timestamps en UTC (el mercado Forex es 24/5)
- Plan Free tiene rate limits — implementar retry con backoff exponencial
- Cachear agresivamente para no exceder rate limits
