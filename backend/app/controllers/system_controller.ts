import type { HttpContext } from '@adonisjs/core/http'
import db from '@adonisjs/lucid/services/db'
import env from '#start/env'

export default class SystemController {
  async health({ cognito, response }: HttpContext) {
    const config = await db.from('broker_configs').where('user_id', cognito.user.id).first()

    const components: Record<string, unknown> = {
      database: { status: 'ok' },
      broker: { status: 'not_configured' },
    }

    if (config) {
      try {
        const bridgeUrl = env.get('MT5_BRIDGE_URL')
        const bridgeApiKey = env.get('MT5_BRIDGE_API_KEY')
        const res = await fetch(`${bridgeUrl}/health`, {
          headers: { 'X-Bridge-Api-Key': bridgeApiKey },
          signal: AbortSignal.timeout(5000),
        })
        const data = (await res.json()) as Record<string, unknown>
        components.broker = { status: data.mt5_connected ? 'ok' : 'disconnected', broker: data.broker }
      } catch {
        components.broker = { status: 'unreachable' }
      }
    }

    const overall = Object.values(components).every((c: any) => c.status === 'ok')
      ? 'healthy'
      : 'degraded'

    return response.ok({ status: overall, components, timestamp: new Date().toISOString() })
  }

  async status({ cognito, response }: HttpContext) {
    const settings = await db.from('trading_settings').where('user_id', cognito.user.id).first()
    const openTrades = await db.from('trades').where('user_id', cognito.user.id).where('status', 'open').count('* as cnt').first()
    const todayPnl = await db.from('trades')
      .where('user_id', cognito.user.id)
      .where('status', 'closed')
      .whereRaw("closed_at::date = CURRENT_DATE")
      .sum('pnl_usd as total')
      .first()

    return response.ok({
      data: {
        killSwitch: settings?.kill_switch || false,
        autoTradingEnabled: settings?.auto_trading_enabled || false,
        openPositions: Number(openTrades?.cnt || 0),
        dailyPnl: Number(todayPnl?.total || 0),
      },
    })
  }

  async killSwitch({ cognito, request, response }: HttpContext) {
    const { enabled } = request.only(['enabled'])

    await db
      .from('trading_settings')
      .where('user_id', cognito.user.id)
      .update({ kill_switch: enabled, updated_at: new Date() })

    return response.ok({
      message: enabled ? '🛑 Kill switch ACTIVADO — Trading detenido' : '✅ Kill switch desactivado — Trading habilitado',
      killSwitch: enabled,
    })
  }
}
