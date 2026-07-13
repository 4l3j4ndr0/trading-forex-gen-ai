import { tool } from '@strands-agents/sdk'
import { z } from 'zod'

/**
 * Calcula EMA (Exponential Moving Average)
 */
function calculateEMA(closes: number[], period: number): number[] {
  const ema: number[] = []
  const multiplier = 2 / (period + 1)

  // SMA como primer valor
  let sum = 0
  for (let i = 0; i < period && i < closes.length; i++) {
    sum += closes[i]!
  }
  ema.push(sum / period)

  // EMA para el resto
  for (let i = period; i < closes.length; i++) {
    const value = (closes[i]! - ema[ema.length - 1]!) * multiplier + ema[ema.length - 1]!
    ema.push(value)
  }

  return ema
}

/**
 * Calcula RSI (Relative Strength Index)
 */
function calculateRSI(closes: number[], period: number = 14): number[] {
  const rsi: number[] = []
  const gains: number[] = []
  const losses: number[] = []

  for (let i = 1; i < closes.length; i++) {
    const change = closes[i]! - closes[i - 1]!
    gains.push(change > 0 ? change : 0)
    losses.push(change < 0 ? Math.abs(change) : 0)
  }

  // Primer promedio
  let avgGain = gains.slice(0, period).reduce((a, b) => a + b, 0) / period
  let avgLoss = losses.slice(0, period).reduce((a, b) => a + b, 0) / period

  for (let i = period; i < gains.length; i++) {
    avgGain = (avgGain * (period - 1) + gains[i]!) / period
    avgLoss = (avgLoss * (period - 1) + losses[i]!) / period

    const rs = avgLoss === 0 ? 100 : avgGain / avgLoss
    rsi.push(100 - 100 / (1 + rs))
  }

  return rsi
}

/**
 * Calcula MACD
 */
function calculateMACD(
  closes: number[],
  fastPeriod: number = 12,
  slowPeriod: number = 26,
  signalPeriod: number = 9
) {
  const emaFast = calculateEMA(closes, fastPeriod)
  const emaSlow = calculateEMA(closes, slowPeriod)

  // Alinear las EMAs (la slow empieza después)
  const offset = slowPeriod - fastPeriod
  const macdLine: number[] = []

  for (let i = 0; i < emaSlow.length; i++) {
    macdLine.push(emaFast[i + offset]! - emaSlow[i]!)
  }

  const signalLine = calculateEMA(macdLine, signalPeriod)
  const histogramOffset = macdLine.length - signalLine.length
  const histogram: number[] = []

  for (let i = 0; i < signalLine.length; i++) {
    histogram.push(macdLine[i + histogramOffset]! - signalLine[i]!)
  }

  return {
    macd: macdLine[macdLine.length - 1] ?? 0,
    signal: signalLine[signalLine.length - 1] ?? 0,
    histogram: histogram[histogram.length - 1] ?? 0,
  }
}

/**
 * Calcula ATR (Average True Range)
 */
function calculateATR(
  highs: number[],
  lows: number[],
  closes: number[],
  period: number = 14
): number {
  const trueRanges: number[] = []

  for (let i = 1; i < highs.length; i++) {
    const tr = Math.max(
      highs[i]! - lows[i]!,
      Math.abs(highs[i]! - closes[i - 1]!),
      Math.abs(lows[i]! - closes[i - 1]!)
    )
    trueRanges.push(tr)
  }

  // EMA del ATR
  let atr = trueRanges.slice(0, period).reduce((a, b) => a + b, 0) / period
  for (let i = period; i < trueRanges.length; i++) {
    atr = (atr * (period - 1) + trueRanges[i]!) / period
  }

  return atr
}

/**
 * Calcula Bollinger Bands
 */
function calculateBollingerBands(closes: number[], period: number = 20, stdDev: number = 2) {
  const sma = closes.slice(-period).reduce((a, b) => a + b, 0) / period
  const squaredDiffs = closes.slice(-period).map((c) => Math.pow(c - sma, 2))
  const variance = squaredDiffs.reduce((a, b) => a + b, 0) / period
  const sd = Math.sqrt(variance)

  return {
    upper: sma + stdDev * sd,
    middle: sma,
    lower: sma - stdDev * sd,
    bandwidth: ((sma + stdDev * sd - (sma - stdDev * sd)) / sma) * 100,
  }
}

export const technicalIndicatorsTool = tool({
  name: 'calculate_indicators',
  description:
    'Calcula indicadores técnicos (EMA, RSI, MACD, ATR, Bollinger Bands) a partir de datos OHLCV. Devuelve los valores actuales y la interpretación de cada indicador.',
  inputSchema: z.object({
    candles: z
      .array(
        z.object({
          open: z.number(),
          high: z.number(),
          low: z.number(),
          close: z.number(),
          volume: z.number(),
          timestamp: z.number(),
        })
      )
      .describe('Array de velas OHLCV del market data tool'),
    symbol: z.string().describe('Par de forex para contexto'),
    timeframe: z.string().describe('Timeframe para contexto'),
  }),
  callback: (input) => {
    const { candles, symbol, timeframe } = input
    const closes = candles.map((c) => c.close)
    const highs = candles.map((c) => c.high)
    const lows = candles.map((c) => c.low)
    const currentPrice = closes[closes.length - 1] ?? 0

    // EMAs
    const ema8 = calculateEMA(closes, 8)
    const ema21 = calculateEMA(closes, 21)
    const ema50 = calculateEMA(closes, 50)
    const ema200 = calculateEMA(closes, 200)

    const currentEma8 = ema8[ema8.length - 1] ?? 0
    const currentEma21 = ema21[ema21.length - 1] ?? 0
    const currentEma50 = ema50.length > 0 ? ema50[ema50.length - 1]! : null
    const currentEma200 = ema200.length > 0 ? ema200[ema200.length - 1]! : null

    // RSI
    const rsiValues = calculateRSI(closes, 14)
    const currentRSI = rsiValues[rsiValues.length - 1] ?? 50

    // MACD
    const macd = calculateMACD(closes)

    // ATR
    const atr = calculateATR(highs, lows, closes, 14)

    // Bollinger Bands
    const bb = calculateBollingerBands(closes)

    // Interpretaciones
    const emaAlignment =
      currentPrice > currentEma8 &&
      currentEma8 > currentEma21 &&
      (currentEma50 === null || currentEma21 > currentEma50)
        ? 'bullish'
        : currentPrice < currentEma8 &&
            currentEma8 < currentEma21 &&
            (currentEma50 === null || currentEma21 < currentEma50)
          ? 'bearish'
          : 'mixed'

    const rsiInterpretation =
      currentRSI > 70
        ? 'overbought'
        : currentRSI < 30
          ? 'oversold'
          : currentRSI > 50
            ? 'bullish_momentum'
            : 'bearish_momentum'

    const macdInterpretation =
      macd.histogram > 0 && macd.macd > macd.signal
        ? 'bullish'
        : macd.histogram < 0 && macd.macd < macd.signal
          ? 'bearish'
          : 'neutral'

    const bbPosition =
      currentPrice > bb.upper
        ? 'above_upper'
        : currentPrice < bb.lower
          ? 'below_lower'
          : currentPrice > bb.middle
            ? 'upper_half'
            : 'lower_half'

    return JSON.stringify({
      symbol,
      timeframe,
      currentPrice,
      indicators: {
        ema: {
          ema8: currentEma8,
          ema21: currentEma21,
          ema50: currentEma50,
          ema200: currentEma200,
          alignment: emaAlignment,
        },
        rsi: {
          value: Math.round(currentRSI * 100) / 100,
          interpretation: rsiInterpretation,
        },
        macd: {
          line: Math.round(macd.macd * 100000) / 100000,
          signal: Math.round(macd.signal * 100000) / 100000,
          histogram: Math.round(macd.histogram * 100000) / 100000,
          interpretation: macdInterpretation,
        },
        atr: {
          value: atr,
          pips: Math.round(atr * 10000 * 10) / 10, // Convertir a pips
        },
        bollingerBands: {
          upper: bb.upper,
          middle: bb.middle,
          lower: bb.lower,
          bandwidth: Math.round(bb.bandwidth * 100) / 100,
          pricePosition: bbPosition,
        },
      },
    })
  },
})
