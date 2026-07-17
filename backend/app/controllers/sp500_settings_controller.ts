import type { HttpContext } from '@adonisjs/core/http'
import db from '@adonisjs/lucid/services/db'

export default class SP500SettingsController {
  async show({ auth, response }: HttpContext) {
    const userId = auth.user!.id
    const row = await db.from('sp500_settings').where('user_id', userId).first()

    if (!row) {
      return response.json({ data: null })
    }

    return response.json({
      data: {
        symbol: row.symbol,
        pointValue: Number(row.point_value),
        minLot: Number(row.min_lot),
        maxLot: Number(row.max_lot),
        maxRiskPerTradePct: Number(row.max_risk_per_trade_pct),
        maxDailyLossPct: Number(row.max_daily_loss_pct),
        maxConsecutiveLosses: row.max_consecutive_losses,
        minRrRatio: Number(row.min_rr_ratio),
        maxOpenPositions: row.max_open_positions,
        amKillzoneStart: row.am_killzone_start,
        amKillzoneEnd: row.am_killzone_end,
        pmKillzoneStart: row.pm_killzone_start,
        pmKillzoneEnd: row.pm_killzone_end,
        premarketStart: row.premarket_start,
        regularSessionStart: row.regular_session_start,
        regularSessionEnd: row.regular_session_end,
        newsBufferMinutes: row.news_buffer_minutes,
        dailyTargetPct: Number(row.daily_target_pct),
        dailyTargetPoints: Number(row.daily_target_points),
        minStructureScore: row.min_structure_score,
        minSweepDistancePoints: Number(row.min_sweep_distance_points),
        killSwitch: row.kill_switch,
        autoTradingEnabled: row.auto_trading_enabled,
      },
    })
  }

  async upsert({ auth, request, response }: HttpContext) {
    const userId = auth.user!.id
    const body = request.body()

    const payload = {
      user_id: userId,
      symbol: body.symbol ?? 'US500Cash',
      point_value: body.pointValue,
      min_lot: body.minLot,
      max_lot: body.maxLot,
      max_risk_per_trade_pct: body.maxRiskPerTradePct,
      max_daily_loss_pct: body.maxDailyLossPct,
      max_consecutive_losses: body.maxConsecutiveLosses,
      min_rr_ratio: body.minRrRatio,
      max_open_positions: body.maxOpenPositions,
      am_killzone_start: body.amKillzoneStart,
      am_killzone_end: body.amKillzoneEnd,
      pm_killzone_start: body.pmKillzoneStart,
      pm_killzone_end: body.pmKillzoneEnd,
      premarket_start: body.premarketStart,
      regular_session_start: body.regularSessionStart,
      regular_session_end: body.regularSessionEnd,
      news_buffer_minutes: body.newsBufferMinutes,
      daily_target_pct: body.dailyTargetPct,
      daily_target_points: body.dailyTargetPoints,
      min_structure_score: body.minStructureScore,
      min_sweep_distance_points: body.minSweepDistancePoints,
      kill_switch: body.killSwitch,
      auto_trading_enabled: body.autoTradingEnabled,
      updated_at: new Date(),
    }

    // Remove undefined values
    const cleanPayload = Object.fromEntries(
      Object.entries(payload).filter(([, v]) => v !== undefined)
    )

    const exists = await db.from('sp500_settings').where('user_id', userId).first()
    if (exists) {
      await db.from('sp500_settings').where('user_id', userId).update(cleanPayload)
    } else {
      await db.from('sp500_settings').insert({ ...cleanPayload, created_at: new Date() })
    }

    return response.json({ message: 'SP500 settings saved' })
  }
}
