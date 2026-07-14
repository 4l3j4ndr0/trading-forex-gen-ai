import type { HttpContext } from '@adonisjs/core/http'
import db from '@adonisjs/lucid/services/db'

export default class LogsController {
  async index({ cognito, request, response }: HttpContext) {
    const { date, limit = 50 } = request.qs()

    let query = db.from('hourly_logs').where('user_id', cognito.user.id)

    if (date) {
      query = query.whereRaw("timestamp::date = ?", [date])
    }

    const logs = await query.orderBy('timestamp', 'desc').limit(Number(limit))

    return response.ok({ data: logs })
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
