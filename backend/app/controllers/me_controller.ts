import type { HttpContext } from '@adonisjs/core/http'
import db from '@adonisjs/lucid/services/db'

export default class MeController {
  async show({ cognito, response }: HttpContext) {
    const user = cognito.user

    const broker = await db.from('broker_configs').where('user_id', user.id).first()
    const settings = await db.from('trading_settings').where('user_id', user.id).first()

    return response.ok({
      data: {
        id: user.id,
        email: user.email,
        fullName: user.fullName,
        accountCurrency: user.accountCurrency,
        isActive: user.isActive,
        createdAt: user.createdAt,
        hasBroker: !!broker,
        hasSettings: !!settings,
        brokerName: broker?.broker_name || null,
        accountType: broker?.account_type || null,
      },
    })
  }
}
