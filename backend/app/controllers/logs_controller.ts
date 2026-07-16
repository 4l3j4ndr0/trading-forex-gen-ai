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
