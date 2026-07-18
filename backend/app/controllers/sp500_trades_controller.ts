import type { HttpContext } from '@adonisjs/core/http'
import db from '@adonisjs/lucid/services/db'

export default class SP500TradesController {
  async index({ cognito, request, response }: HttpContext) {
    const userId = cognito.user.id
    const page = request.input('page', 1)
    const limit = request.input('limit', 25)
    const status = request.input('status')

    let query = db.from('sp500_trades').where('user_id', userId)

    if (status) {
      query = query.where('status', status)
    }

    const trades = await query
      .orderBy('opened_at', 'desc')
      .paginate(page, limit)

    return response.json({
      data: trades.all().map((t) => ({
        id: t.id,
        ticket: t.ticket,
        side: t.side,
        lotSize: Number(t.lot_size),
        entryPrice: Number(t.entry_price),
        exitPrice: t.exit_price ? Number(t.exit_price) : null,
        slPrice: t.sl_price ? Number(t.sl_price) : null,
        tpPrice: t.tp_price ? Number(t.tp_price) : null,
        slPoints: t.sl_points ? Number(t.sl_points) : null,
        tpPoints: t.tp_points ? Number(t.tp_points) : null,
        pnlPoints: t.pnl_points ? Number(t.pnl_points) : null,
        pnlUsd: t.pnl_usd ? Number(t.pnl_usd) : null,
        riskUsd: t.risk_usd ? Number(t.risk_usd) : null,
        comment: t.comment,
        basketId: t.basket_id,
        closeReason: t.close_reason,
        status: t.status,
        openedAt: t.opened_at,
        closedAt: t.closed_at,
        holdingMinutes: t.holding_minutes,
      })),
      meta: {
        total: trades.total,
        page: trades.currentPage,
        totalPages: trades.lastPage,
      },
    })
  }

  async open({ cognito, response }: HttpContext) {
    const userId = cognito.user.id
    const trades = await db.from('sp500_trades')
      .where('user_id', userId)
      .where('status', 'open')
      .orderBy('opened_at', 'desc')

    return response.json({
      data: trades.map((t) => ({
        id: t.id,
        ticket: t.ticket,
        side: t.side,
        lotSize: Number(t.lot_size),
        entryPrice: Number(t.entry_price),
        slPrice: t.sl_price ? Number(t.sl_price) : null,
        tpPrice: t.tp_price ? Number(t.tp_price) : null,
        slPoints: t.sl_points ? Number(t.sl_points) : null,
        tpPoints: t.tp_points ? Number(t.tp_points) : null,
        riskUsd: t.risk_usd ? Number(t.risk_usd) : null,
        comment: t.comment,
        basketId: t.basket_id,
        status: t.status,
        openedAt: t.opened_at,
      })),
    })
  }

  async stats({ cognito, response }: HttpContext) {
    const userId = cognito.user.id

    const row = await db.from('sp500_trades')
      .where('user_id', userId)
      .where('status', 'closed')
      .select(
        db.raw('COUNT(*) as total'),
        db.raw('COUNT(CASE WHEN pnl_usd > 0 THEN 1 END) as wins'),
        db.raw('COUNT(CASE WHEN pnl_usd < 0 THEN 1 END) as losses'),
        db.raw('COALESCE(SUM(pnl_usd), 0) as total_pnl'),
        db.raw('COALESCE(AVG(pnl_usd), 0) as avg_pnl'),
        db.raw('COALESCE(MAX(pnl_usd), 0) as best_trade'),
        db.raw('COALESCE(MIN(pnl_usd), 0) as worst_trade'),
      )
      .first()

    if (!row || Number(row.total) === 0) {
      return response.json({ data: { totalTrades: 0 } })
    }

    const total = Number(row.total)
    const wins = Number(row.wins)

    return response.json({
      data: {
        totalTrades: total,
        wins,
        losses: Number(row.losses),
        winRate: Math.round((wins / total) * 100 * 10) / 10,
        totalPnl: Number(Number(row.total_pnl).toFixed(2)),
        avgPnl: Number(Number(row.avg_pnl).toFixed(2)),
        bestTrade: Number(Number(row.best_trade).toFixed(2)),
        worstTrade: Number(Number(row.worst_trade).toFixed(2)),
      },
    })
  }
}
