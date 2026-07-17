import type { HttpContext } from '@adonisjs/core/http'
import db from '@adonisjs/lucid/services/db'

export default class SP500LogsController {
  async index({ auth, request, response }: HttpContext) {
    const userId = auth.user!.id
    const page = request.input('page', 1)
    const limit = request.input('limit', 25)
    const date = request.input('date')

    let query = db.from('sp500_logs').where('user_id', userId)

    if (date) {
      query = query.whereRaw('DATE(created_at) = ?', [date])
    }

    const logs = await query.orderBy('created_at', 'desc').paginate(page, limit)

    // Get totals from sp500_trades table (source of truth)
    let totalsQuery = db.from('sp500_trades').where('user_id', userId).where('status', 'closed')
    if (date) {
      totalsQuery = totalsQuery.whereRaw('DATE(closed_at) = ?', [date])
    }
    const totalsRow = await totalsQuery
      .select(
        db.raw('COALESCE(SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END), 0) as wins'),
        db.raw('COALESCE(SUM(CASE WHEN pnl_usd < 0 THEN 1 ELSE 0 END), 0) as losses'),
        db.raw('COALESCE(SUM(pnl_usd), 0) as realized_pnl'),
      )
      .first()

    return response.json({
      data: logs.all().map((l) => ({
        id: l.id,
        timestamp: l.created_at,
        decision: l.decision,
        tradesOpened: l.trades_opened,
        tradesClosed: l.trades_closed,
        floatingPnl: Number(l.floating_pnl),
      })),
      meta: {
        total: logs.total,
        page: logs.currentPage,
        totalPages: logs.lastPage,
        totals: {
          wins: Number(totalsRow?.wins ?? 0),
          losses: Number(totalsRow?.losses ?? 0),
          realizedPnl: Number(Number(totalsRow?.realized_pnl ?? 0).toFixed(2)),
        },
      },
    })
  }
}
