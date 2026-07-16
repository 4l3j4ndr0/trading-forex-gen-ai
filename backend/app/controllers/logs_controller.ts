import type { HttpContext } from '@adonisjs/core/http'
import db from '@adonisjs/lucid/services/db'

export default class LogsController {
  async index({ cognito, request, response }: HttpContext) {
    const { date, page = 1, limit = 25 } = request.qs()

    let query = db.from('hourly_logs').where('user_id', cognito.user.id)

    if (date) {
      query = query.whereRaw("created_at::date = ?", [date])
    }

    const total = await query.clone().count('* as cnt').first()

    // Get real totals from trades table (source of truth)
    let tradesQuery = db.from('trades').where('user_id', cognito.user.id)
    let closedQuery = db.from('trades').where('user_id', cognito.user.id).where('status', 'closed')

    if (date) {
      tradesQuery = tradesQuery.whereRaw("opened_at::date = ?", [date])
      closedQuery = closedQuery.whereRaw("closed_at::date = ?", [date])
    }

    const openedCount = await tradesQuery.clone().count('* as cnt').first()
    const closedAgg = await closedQuery.clone()
      .select(
        db.raw('COUNT(*) as cnt'),
        db.raw('COALESCE(SUM(pnl_usd), 0) as total_pnl'),
      )
      .first()

    const logs = await query
      .orderBy('created_at', 'desc')
      .limit(Number(limit))
      .offset((Number(page) - 1) * Number(limit))

    return response.ok({
      data: logs,
      meta: {
        total: Number(total?.cnt || 0),
        page: Number(page),
        limit: Number(limit),
        totalPages: Math.ceil(Number(total?.cnt || 0) / Number(limit)),
        totals: {
          opened: Number(openedCount?.cnt || 0),
          closed: Number(closedAgg?.cnt || 0),
          realizedPnl: Number(closedAgg?.total_pnl || 0),
        },
      },
    })
  }

  async show({ cognito, params, response }: HttpContext) {
    const log = await db
      .from('hourly_logs')
      .where('user_id', cognito.user.id)
      .where('id', params.id)
      .first()

    if (!log) return response.notFound({ message: 'Log not found' })
    return response.ok({ data: log })
  }
}
