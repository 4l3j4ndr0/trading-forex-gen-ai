import type { HttpContext } from '@adonisjs/core/http'
import db from '@adonisjs/lucid/services/db'

export default class PairsController {
  async index({ response }: HttpContext) {
    const pairs = await db
      .from('pairs')
      .where('is_active', true)
      .orderBy('symbol', 'asc')
      .select('id', 'symbol', 'base_currency', 'quote_currency', 'category', 'sessions')

    return response.ok({ data: pairs })
  }
}
