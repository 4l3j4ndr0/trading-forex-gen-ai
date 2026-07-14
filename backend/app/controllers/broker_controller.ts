import type { HttpContext } from '@adonisjs/core/http'
import db from '@adonisjs/lucid/services/db'
import encryption from '@adonisjs/core/services/encryption'

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
        bridgeUrl: config.bridge_url,
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
      'bridgeUrl',
      'bridgeApiKey',
      'symbolSuffix',
      'accountType',
    ])

    const data = {
      user_id: cognito.user.id,
      broker_name: body.brokerName || 'XM',
      mt5_login: body.mt5Login,
      mt5_password_encrypted: encryption.encrypt(body.mt5Password),
      mt5_server: body.mt5Server,
      bridge_url: body.bridgeUrl,
      bridge_api_key_encrypted: encryption.encrypt(body.bridgeApiKey),
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

    try {
      const bridgeApiKey = encryption.decrypt(config.bridge_api_key_encrypted) as string
      const res = await fetch(`${config.bridge_url}/health`, {
        headers: { 'X-Bridge-Api-Key': bridgeApiKey },
      })
      const data = (await res.json()) as Record<string, unknown>

      if (data.mt5_connected) {
        await db
          .from('broker_configs')
          .where('user_id', cognito.user.id)
          .update({ last_connected_at: new Date() })
      }

      return response.ok({ data, connected: !!data.mt5_connected })
    } catch (error) {
      return response.ok({ connected: false, error: 'Cannot reach bridge' })
    }
  }

  async destroy({ cognito, response }: HttpContext) {
    await db.from('broker_configs').where('user_id', cognito.user.id).delete()
    return response.ok({ message: 'Broker config eliminada' })
  }
}
