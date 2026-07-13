import { tool } from '@strands-agents/sdk'
import { z } from 'zod'
import env from '#start/env'

const MASSIVE_BASE_URL = env.get('MASSIVE_BASE_URL')
const MASSIVE_API_KEY = env.get('MASSIVE_API_KEY')

export interface OHLCBar {
  open: number
  high: number
  low: number
  close: number
  volume: number
  timestamp: number
}

/**
 * Mapea timeframes del sistema a parámetros de Massive API
 */
function getTimeframeParams(timeframe: string): { multiplier: number; timespan: string } {
  const map: Record<string, { multiplier: number; timespan: string }> = {
    M5: { multiplier: 5, timespan: 'minute' },
    M15: { multiplier: 15, timespan: 'minute' },
    H1: { multiplier: 1, timespan: 'hour' },
    H4: { multiplier: 4, timespan: 'hour' },
    D1: { multiplier: 1, timespan: 'day' },
  }
  return map[timeframe] ?? { multiplier: 1, timespan: 'hour' }
}

/**
 * Convierte un símbolo como "EUR/USD" al formato Massive "C:EURUSD"
 */
function toMassiveTicker(symbol: string): string {
  return `C:${symbol.replace('/', '')}`
}

export const marketDataTool = tool({
  name: 'get_market_data',
  description:
    'Obtiene datos OHLCV (velas) de un par de forex para un timeframe específico. Usa estos datos para calcular indicadores técnicos y analizar la acción del precio.',
  inputSchema: z.object({
    symbol: z.string().describe('Par de forex, ej: "EUR/USD", "GBP/USD"'),
    timeframe: z
      .enum(['M5', 'M15', 'H1', 'H4', 'D1'])
      .describe('Temporalidad: M5, M15, H1, H4 o D1'),
    bars: z
      .number()
      .min(10)
      .max(200)
      .default(100)
      .describe('Número de velas a obtener (10-200)'),
  }),
  callback: async (input) => {
    const { symbol, timeframe, bars } = input
    const ticker = toMassiveTicker(symbol)
    const { multiplier, timespan } = getTimeframeParams(timeframe)

    // Calcular rango de fechas — usar "to" como hoy y "from" basado en el timeframe
    const to = new Date()
    const from = new Date()

    // Días hacia atrás según timeframe (considerando mercado 24/5, gaps de fines de semana)
    const daysBack: Record<string, number> = {
      M5: 5,       // 5 días para velas de 5 min
      M15: 14,     // 14 días para velas de 15 min
      H1: 21,      // 21 días para velas de 1 hora (~120 velas hábiles)
      H4: 60,      // 60 días para velas de 4 horas (~120 velas hábiles)
      D1: 200,     // 200 días para velas diarias
    }
    from.setDate(from.getDate() - (daysBack[timeframe] ?? 10))

    const fromStr = from.toISOString().split('T')[0]
    const toStr = to.toISOString().split('T')[0]

    const url = `${MASSIVE_BASE_URL}/v2/aggs/ticker/${ticker}/range/${multiplier}/${timespan}/${fromStr}/${toStr}?adjusted=true&sort=asc&limit=5000&apiKey=${MASSIVE_API_KEY}`

    try {
      console.log(`[MarketData] Fetching ${symbol} ${timeframe} (${fromStr} → ${toStr}, limit=${bars})`)
      const response = await fetch(url)

      if (!response.ok) {
        return `Error al obtener datos de ${symbol} (${timeframe}): HTTP ${response.status}`
      }

      const data = (await response.json()) as {
        results?: Array<{ o: number; h: number; l: number; c: number; v: number; t: number }>
        resultsCount?: number
      }

      if (!data.results || data.results.length === 0) {
        return `No hay datos disponibles para ${symbol} en timeframe ${timeframe}`
      }

      // Tomar las últimas N velas (ya vienen en orden cronológico asc)
      const recentResults = data.results.slice(-bars)

      const candles: OHLCBar[] = recentResults.map((r) => ({
        open: r.o,
        high: r.h,
        low: r.l,
        close: r.c,
        volume: r.v,
        timestamp: r.t,
      }))

      const latest = candles[candles.length - 1]!
      const first = candles[0]!

      console.log(`[MarketData] ✅ ${symbol} ${timeframe}: ${candles.length} velas, precio actual: ${latest.close}, rango: ${new Date(first.timestamp).toISOString().split('T')[0]} → ${new Date(latest.timestamp).toISOString().split('T')[0]}`)

      return JSON.stringify({
        symbol,
        timeframe,
        totalBars: candles.length,
        period: {
          from: new Date(first.timestamp).toISOString(),
          to: new Date(latest.timestamp).toISOString(),
        },
        currentPrice: latest.close,
        high24h: Math.max(...candles.slice(-24).map((c) => c.high)),
        low24h: Math.min(...candles.slice(-24).map((c) => c.low)),
        candles,
      })
    } catch (error) {
      return `Error de conexión al obtener datos de ${symbol}: ${error instanceof Error ? error.message : 'Unknown error'}`
    }
  },
})
