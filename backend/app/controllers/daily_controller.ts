import type { HttpContext } from '@adonisjs/core/http'
import db from '@adonisjs/lucid/services/db'

export default class DailyController {
  async index({ cognito, request, response }: HttpContext) {
    const { limit = 30 } = request.qs()

    const summaries = await db
      .from('daily_summaries')
      .where('user_id', cognito.user.id)
      .orderBy('date', 'desc')
      .limit(Number(limit))

    return response.ok({ data: summaries })
  }

  async today({ cognito, response }: HttpContext) {
    const summary = await db
      .from('daily_summaries')
      .where('user_id', cognito.user.id)
      .whereRaw("date = CURRENT_DATE")
      .first()

    if (!summary) {
      // Calculate from trades
      const todayTrades = await db
        .from('trades')
        .where('user_id', cognito.user.id)
        .where('status', 'closed')
        .whereRaw("closed_at::date = CURRENT_DATE")

      const pnls = todayTrades.map((t) => Number(t.pnl_usd || 0))
      const wins = pnls.filter((p) => p > 0)

      return response.ok({
        data: {
          date: new Date().toISOString().split('T')[0],
          realizedPnl: pnls.reduce((a, b) => a + b, 0),
          tradesTotal: todayTrades.length,
          tradesWon: wins.length,
          tradesLost: todayTrades.length - wins.length,
          winRate: todayTrades.length > 0 ? Math.round((wins.length / todayTrades.length) * 100) : 0,
          targetReached: false,
        },
      })
    }

    return response.ok({ data: summary })
  }

  async show({ cognito, params, response }: HttpContext) {
    const summary = await db
      .from('daily_summaries')
      .where('user_id', cognito.user.id)
      .where('date', params.date)
      .first()

    if (!summary) return response.notFound({ message: 'No summary for that date' })
    return response.ok({ data: summary })
  }
}
