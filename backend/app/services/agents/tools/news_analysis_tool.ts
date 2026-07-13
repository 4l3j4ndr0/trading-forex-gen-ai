import { tool } from '@strands-agents/sdk'
import { z } from 'zod'
import db from '@adonisjs/lucid/services/db'

/**
 * Mapea pares de forex a las monedas que los componen
 */
function getCurrenciesFromPair(symbol: string): string[] {
  const clean = symbol.replace('/', '')
  return [clean.slice(0, 3), clean.slice(3, 6)]
}

/**
 * Eventos de alto impacto conocidos que afectan el mercado
 */
const HIGH_IMPACT_EVENTS: Record<string, string[]> = {
  USD: [
    'Non-Farm Payrolls (NFP)',
    'FOMC Interest Rate Decision',
    'CPI (Consumer Price Index)',
    'GDP',
    'Retail Sales',
    'Unemployment Claims',
    'Fed Chair Speech',
    'ISM Manufacturing PMI',
    'PPI (Producer Price Index)',
  ],
  EUR: [
    'ECB Interest Rate Decision',
    'ECB Press Conference',
    'German CPI',
    'Eurozone CPI',
    'German Manufacturing PMI',
    'Eurozone GDP',
  ],
  GBP: [
    'BoE Interest Rate Decision',
    'UK CPI',
    'UK GDP',
    'UK Employment Change',
    'UK Retail Sales',
  ],
  JPY: [
    'BoJ Interest Rate Decision',
    'Japan CPI',
    'Japan GDP',
    'Tankan Survey',
  ],
  AUD: [
    'RBA Interest Rate Decision',
    'Australia Employment Change',
    'Australia CPI',
    'Australia GDP',
  ],
  CAD: [
    'BoC Interest Rate Decision',
    'Canada Employment Change',
    'Canada CPI',
    'Canada GDP',
  ],
  NZD: [
    'RBNZ Interest Rate Decision',
    'New Zealand GDP',
    'New Zealand CPI',
  ],
  CHF: [
    'SNB Interest Rate Decision',
    'Switzerland CPI',
  ],
}

export const newsAnalysisTool = tool({
  name: 'check_news_impact',
  description:
    'Analiza el impacto de noticias económicas sobre un par de forex. Consulta el calendario económico para eventos de alto impacto en las próximas horas y evalúa si es seguro operar. USAR SIEMPRE como primer paso antes del análisis técnico.',
  inputSchema: z.object({
    symbol: z.string().describe('Par de forex, ej: "EUR/USD"'),
    hoursAhead: z
      .number()
      .min(1)
      .max(24)
      .default(4)
      .describe('Ventana de horas hacia adelante para buscar eventos (1-24)'),
  }),
  callback: async (input) => {
    const { symbol, hoursAhead } = input
    const currencies = getCurrenciesFromPair(symbol)

    const now = new Date()
    const futureLimit = new Date(now.getTime() + hoursAhead * 60 * 60 * 1000)
    const pastLimit = new Date(now.getTime() - 30 * 60 * 1000) // 30 min atrás (post-news volatility)

    // Consultar eventos de la BD
    const events = await db
      .from('economic_events')
      .whereIn('currency', currencies)
      .where('event_at', '>=', pastLimit.toISOString())
      .where('event_at', '<=', futureLimit.toISOString())
      .orderBy('event_at', 'asc')

    // Clasificar eventos por impacto
    const highImpactEvents = events.filter(
      (e: Record<string, unknown>) => e.impact === 'high'
    )
    const mediumImpactEvents = events.filter(
      (e: Record<string, unknown>) => e.impact === 'medium'
    )

    // Determinar si es seguro operar
    let safeToTrade = true
    let riskLevel: 'low' | 'medium' | 'high' | 'extreme' = 'low'
    const warnings: string[] = []

    // Eventos de alto impacto en los próximos 30 minutos → NO OPERAR
    const imminent = highImpactEvents.filter((e: Record<string, unknown>) => {
      const eventTime = new Date(e.event_at as string)
      const minutesUntil = (eventTime.getTime() - now.getTime()) / 60000
      return minutesUntil >= -30 && minutesUntil <= 30
    })

    if (imminent.length > 0) {
      safeToTrade = false
      riskLevel = 'extreme'
      warnings.push(
        `🚨 EVENTO DE ALTO IMPACTO INMINENTE (±30 min): ${imminent.map((e: Record<string, unknown>) => `${e.title} (${e.currency})`).join(', ')}`
      )
    }

    // Eventos de alto impacto en las próximas 2 horas → precaución
    const upcoming = highImpactEvents.filter((e: Record<string, unknown>) => {
      const eventTime = new Date(e.event_at as string)
      const minutesUntil = (eventTime.getTime() - now.getTime()) / 60000
      return minutesUntil > 30 && minutesUntil <= 120
    })

    if (upcoming.length > 0 && riskLevel !== 'extreme') {
      riskLevel = 'high'
      warnings.push(
        `⚠️ Evento de alto impacto próximo (< 2h): ${upcoming.map((e: Record<string, unknown>) => `${e.title} (${e.currency}) en ${Math.round((new Date(e.event_at as string).getTime() - now.getTime()) / 60000)} min`).join(', ')}`
      )
    }

    // Eventos medium en próxima hora → nota
    if (mediumImpactEvents.length > 0 && riskLevel === 'low') {
      riskLevel = 'medium'
      warnings.push(
        `📋 Eventos de impacto medio programados: ${mediumImpactEvents.map((e: Record<string, unknown>) => e.title).join(', ')}`
      )
    }

    // Info adicional sobre eventos conocidos de alto impacto para estas monedas
    const relevantHighImpact: string[] = []
    for (const currency of currencies) {
      const events_list = HIGH_IMPACT_EVENTS[currency]
      if (events_list) {
        relevantHighImpact.push(`${currency}: ${events_list.slice(0, 5).join(', ')}`)
      }
    }

    // Determinar sesión de mercado activa
    const utcHour = now.getUTCHours()
    let activeSessions: string[] = []
    if (utcHour >= 0 && utcHour < 9) activeSessions.push('Tokyo')
    if (utcHour >= 7 && utcHour < 16) activeSessions.push('London')
    if (utcHour >= 12 && utcHour < 21) activeSessions.push('New York')
    if (utcHour >= 12 && utcHour < 16) activeSessions.push('London-NY Overlap (máxima liquidez)')
    if (activeSessions.length === 0) activeSessions = ['Baja liquidez (entre sesiones)']

    // Buscar eventos geopolíticos recientes (últimas 48h) que afecten sentimiento
    const geopoliticalEvents = await db
      .from('economic_events')
      .where('event_at', '>=', new Date(now.getTime() - 48 * 60 * 60 * 1000).toISOString())
      .where('event_at', '<=', now.toISOString())
      .whereILike('title', '%tension%')
      .orWhereILike('title', '%war%')
      .orWhereILike('title', '%military%')
      .orWhereILike('title', '%crisis%')
      .orWhereILike('title', '%sanctions%')
      .orderBy('event_at', 'desc')
      .limit(5)

    const geopoliticalContext =
      geopoliticalEvents.length > 0
        ? geopoliticalEvents.map((e: Record<string, unknown>) => e.title as string)
        : []

    // Sentimiento general basado en eventos
    let marketSentiment: 'risk_on' | 'risk_off' | 'neutral' = 'neutral'
    if (geopoliticalContext.some((t) => t.toLowerCase().includes('tension') || t.toLowerCase().includes('military'))) {
      marketSentiment = 'risk_off'
      if (riskLevel === 'low') riskLevel = 'medium'
      warnings.push('📊 Sentimiento risk-off por tensiones geopolíticas — USD y JPY como refugio, monedas de riesgo (AUD, NZD, CAD) presionadas.')
    }

    return JSON.stringify({
      symbol,
      currencies,
      timestamp: now.toISOString(),
      activeSessions,
      marketSentiment,
      geopoliticalContext,
      newsAssessment: {
        safeToTrade,
        riskLevel,
        warnings,
        eventsFound: {
          highImpact: highImpactEvents.length,
          mediumImpact: mediumImpactEvents.length,
          total: events.length,
        },
        events: events.map((e: Record<string, unknown>) => ({
          title: e.title,
          currency: e.currency,
          impact: e.impact,
          eventAt: e.event_at,
          forecast: e.forecast,
          previous: e.previous,
          actual: e.actual,
        })),
      },
      knownHighImpactEvents: relevantHighImpact,
      recommendation: safeToTrade
        ? riskLevel === 'low'
          ? '✅ Sin eventos de impacto. Seguro para operar.'
          : riskLevel === 'medium'
            ? '⚠️ Precaución — hay factores de riesgo. Operar con SL ajustado o reducir exposición.'
            : '⚠️ Alto riesgo por eventos próximos. Considerar no operar o reducir significativamente la exposición.'
        : '🚫 NO OPERAR — Evento de alto impacto inminente. Esperar mínimo 30 minutos post-noticia.',
    })
  },
})
