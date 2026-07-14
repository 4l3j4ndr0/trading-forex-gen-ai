import type { HttpContext } from '@adonisjs/core/http'
import db from '@adonisjs/lucid/services/db'

export default class TradesController {
  async index({ cognito, request, response }: HttpContext) {
    const { status, symbol, period, page = 1, limit = 20 } = request.qs()

    let query = db.from('trades').where('user_id', cognito.user.id)

    if (status) query = query.where('status', status)
    if (symbol) {
      const pair = await db.from('pairs').where('symbol', symbol).first()
      if (pair) query = query.where('pair_id', pair.id)
    }
    if (period === 'today') {
      query = query.whereRaw("closed_at::date = CURRENT_DATE")
    } else if (period === '7d') {
      query = query.whereRaw("closed_at >= NOW() - INTERVAL '7 days'")
    } else if (period === '30d') {
      query = query.whereRaw("closed_at >= NOW() - INTERVAL '30 days'")
    }

    const trades = await query
      .orderBy('opened_at', 'desc')
      .offset((Number(page) - 1) * Number(limit))
      .limit(Number(limit))

    const countResult = await db.from('trades')
      .where('user_id', cognito.user.id)
      .count('* as total')
      .first()

    return response.ok({
      data: trades,
      meta: { total: Number(countResult?.total || 0), page: Number(page), limit: Number(limit) },
    })
  }

  async open({ cognito, response }: HttpContext) {
    const trades = await db
      .from('trades')
      .where('user_id', cognito.user.id)
      .where('status', 'open')
      .orderBy('opened_at', 'desc')

    return response.ok({ data: trades })
  }

  async show({ cognito, params, response }: HttpContext) {
    const trade = await db
      .from('trades')
      .where('user_id', cognito.user.id)
      .where('id', params.id)
      .first()

    if (!trade) return response.notFound({ message: 'Trade not found' })
    return response.ok({ data: trade })
  }

  async stats({ cognito, request, response }: HttpContext) {
    const { period = '30d' } = request.qs()

    let interval = "30 days"
    if (period === '7d') interval = "7 days"
    if (period === '90d') interval = "90 days"
    if (period === 'all') interval = "100 years"

    const trades = await db
      .from('trades')
      .where('user_id', cognito.user.id)
      .where('status', 'closed')
      .whereRaw(`closed_at >= NOW() - INTERVAL '${interval}'`)

    const pnls = trades.map((t) => Number(t.pnl_usd || 0))
    const wins = pnls.filter((p) => p > 0)
    const losses = pnls.filter((p) => p <= 0)

    const grossProfit = wins.reduce((a, b) => a + b, 0)
    const grossLoss = Math.abs(losses.reduce((a, b) => a + b, 0))

    return response.ok({
      data: {
        period,
        totalTrades: trades.length,
        winRate: trades.length > 0 ? Math.round((wins.length / trades.length) * 1000) / 10 : 0,
        profitFactor: grossLoss > 0 ? Math.round((grossProfit / grossLoss) * 100) / 100 : 0,
        totalPnl: Math.round(pnls.reduce((a, b) => a + b, 0) * 100) / 100,
        avgWinner: wins.length > 0 ? Math.round((grossProfit / wins.length) * 100) / 100 : 0,
        avgLoser: losses.length > 0 ? Math.round((grossLoss / losses.length) * -100) / 100 : 0,
        bestTrade: pnls.length > 0 ? Math.max(...pnls) : 0,
        worstTrade: pnls.length > 0 ? Math.min(...pnls) : 0,
      },
    })
  }
}
