import type { HttpContext } from '@adonisjs/core/http'
import db from '@adonisjs/lucid/services/db'

export default class MeController {
  async show({ cognito, response }: HttpContext) {
    const user = cognito.user

    const settings = await db.from('user_settings').where('user_id', user.id).first()

    return response.ok({
      data: {
        id: user.id,
        email: user.email,
        fullName: user.fullName,
        avatarUrl: user.avatarUrl,
        accountCurrency: user.accountCurrency,
        accountBalance: Number(user.accountBalance),
        isActive: user.isActive,
        lastLoginAt: user.lastLoginAt,
        createdAt: user.createdAt,
        settings: settings ? this.formatSettings(settings) : null,
      },
    })
  }

  async updateSettings({ cognito, request, response }: HttpContext) {
    const user = cognito.user
    const body = request.only([
      'maxRiskPerTrade',
      'maxDailyDrawdown',
      'maxWeeklyDrawdown',
      'maxOpenPositions',
      'preferredPairs',
      'preferredSessions',
      'minSignalScore',
      'minSignalClass',
      'alertChannels',
      'timezone',
      'accountBalance',
      'accountCurrency',
    ])

    // Actualizar balance/currency en users si vienen
    if (body.accountBalance !== undefined || body.accountCurrency !== undefined) {
      const userUpdates: Record<string, unknown> = {}
      if (body.accountBalance !== undefined) userUpdates.account_balance = body.accountBalance
      if (body.accountCurrency !== undefined) userUpdates.account_currency = body.accountCurrency
      if (Object.keys(userUpdates).length > 0) {
        await db.from('users').where('id', user.id).update(userUpdates)
      }
    }

    // Actualizar settings
    const settingsUpdate: Record<string, unknown> = { updated_at: new Date() }

    if (body.maxRiskPerTrade !== undefined) settingsUpdate.max_risk_per_trade = body.maxRiskPerTrade
    if (body.maxDailyDrawdown !== undefined)
      settingsUpdate.max_daily_drawdown = body.maxDailyDrawdown
    if (body.maxWeeklyDrawdown !== undefined)
      settingsUpdate.max_weekly_drawdown = body.maxWeeklyDrawdown
    if (body.maxOpenPositions !== undefined)
      settingsUpdate.max_open_positions = body.maxOpenPositions
    if (body.preferredPairs !== undefined)
      settingsUpdate.preferred_pairs = JSON.stringify(body.preferredPairs)
    if (body.preferredSessions !== undefined)
      settingsUpdate.preferred_sessions = JSON.stringify(body.preferredSessions)
    if (body.minSignalScore !== undefined) settingsUpdate.min_signal_score = body.minSignalScore
    if (body.minSignalClass !== undefined) settingsUpdate.min_signal_class = body.minSignalClass
    if (body.alertChannels !== undefined)
      settingsUpdate.alert_channels = JSON.stringify(body.alertChannels)
    if (body.timezone !== undefined) settingsUpdate.timezone = body.timezone

    await db.from('user_settings').where('user_id', user.id).update(settingsUpdate)

    // Recargar
    const settings = await db.from('user_settings').where('user_id', user.id).first()
    await user.refresh()

    return response.ok({
      data: {
        accountBalance: Number(user.accountBalance),
        accountCurrency: user.accountCurrency,
        settings: settings ? this.formatSettings(settings) : null,
      },
      message: 'Configuración actualizada',
    })
  }

  private formatSettings(settings: Record<string, unknown>) {
    return {
      maxRiskPerTrade: Number(settings.max_risk_per_trade),
      maxDailyDrawdown: Number(settings.max_daily_drawdown),
      maxWeeklyDrawdown: Number(settings.max_weekly_drawdown),
      maxOpenPositions: Number(settings.max_open_positions),
      preferredPairs: settings.preferred_pairs,
      preferredSessions: settings.preferred_sessions,
      minSignalScore: Number(settings.min_signal_score),
      minSignalClass: settings.min_signal_class,
      alertChannels: settings.alert_channels,
      timezone: settings.timezone,
    }
  }
}
