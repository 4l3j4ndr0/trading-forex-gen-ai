import type { HttpContext } from '@adonisjs/core/http'
import db from '@adonisjs/lucid/services/db'
import env from '#start/env'

export default class BrokerController {
  async show({ cognito, response }: HttpContext) {
    const config = await db.from('broker_configs').where('user_id', cognito.user.id).first()

    if (!config) {
      return response.ok({ data: null })
    }

    return response.ok({
      data: {
        id: config.id,
        brokerName: config.broker_name,
        mt5Login: config.mt5_login,
        mt5Server: config.mt5_server,
        symbolSuffix: config.symbol_suffix,
        accountType: config.account_type,
        isActive: config.is_active,
        lastConnectedAt: config.last_connected_at,
      },
    })
  }

  async upsert({ cognito, request, response }: HttpContext) {
    const body = request.only([
      'brokerName',
      'mt5Login',
      'mt5Password',
      'mt5Server',
      'symbolSuffix',
      'accountType',
    ])

    const data = {
      user_id: cognito.user.id,
      broker_name: body.brokerName || 'XM',
      mt5_login: body.mt5Login,
      mt5_password_encrypted: Buffer.from(body.mt5Password).toString('base64'),
      mt5_server: body.mt5Server,
      symbol_suffix: body.symbolSuffix || '#',
      account_type: body.accountType || 'demo',
      is_active: true,
      updated_at: new Date(),
    }

    const existing = await db.from('broker_configs').where('user_id', cognito.user.id).first()

    if (existing) {
      await db.from('broker_configs').where('user_id', cognito.user.id).update(data)
    } else {
      await db.table('broker_configs').insert({ ...data, created_at: new Date() })
    }

    return response.ok({ message: 'Broker configurado correctamente' })
  }

  async testConnection({ cognito, response }: HttpContext) {
    const config = await db.from('broker_configs').where('user_id', cognito.user.id).first()

    if (!config) {
      return response.badRequest({ message: 'No broker configured' })
    }

    const bridgeUrl = env.get('MT5_BRIDGE_URL')
    const bridgeApiKey = env.get('MT5_BRIDGE_API_KEY')

    try {
      const res = await fetch(`${bridgeUrl}/account`, {
        headers: {
          'X-Bridge-Api-Key': bridgeApiKey,
          'X-User-Id': cognito.user.id,
        },
      })
      const data = (await res.json()) as Record<string, unknown>

      if (!('error' in data)) {
        await db
          .from('broker_configs')
          .where('user_id', cognito.user.id)
          .update({ last_connected_at: new Date() })
        return response.ok({ data, connected: true })
      }

      return response.ok({ connected: false, error: data.error })
    } catch {
      return response.ok({ connected: false, error: 'Cannot reach bridge' })
    }
  }

  async destroy({ cognito, response }: HttpContext) {
    await db.from('broker_configs').where('user_id', cognito.user.id).delete()
    return response.ok({ message: 'Broker config eliminada' })
  }
}
