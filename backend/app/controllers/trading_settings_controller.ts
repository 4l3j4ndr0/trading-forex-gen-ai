import type { HttpContext } from '@adonisjs/core/http'
import db from '@adonisjs/lucid/services/db'

const DEFAULTS = {
  max_risk_per_trade_pct: 1.0,
  max_daily_loss_pct: 1.0,
  max_drawdown_pct: 5.0,
  max_consecutive_losses: 5,
  min_rr_ratio: 1.5,
  default_lot_size: 0.05,
  max_lot_size: 0.5,
  max_open_positions: 3,
  trading_start_utc: '07:00',
  trading_end_utc: '21:00',
  news_buffer_minutes: 30,
  max_trade_duration_minutes: 240,
  daily_target_pct: 1.0,
  reduce_lot_at_pct: 80,
  min_adx_entry: 25,
  min_alignment_score: 2,
  max_spread_pips: 3.0,
  allowed_pairs: JSON.stringify(['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'EURGBP']),
  kill_switch: false,
  auto_trading_enabled: true,
}

export default class TradingSettingsController {
  async show({ cognito, response }: HttpContext) {
    let settings = await db.from('trading_settings').where('user_id', cognito.user.id).first()

    if (!settings) {
      // Create defaults
      await db.table('trading_settings').insert({
        user_id: cognito.user.id,
        ...DEFAULTS,
        created_at: new Date(),
      })
      settings = await db.from('trading_settings').where('user_id', cognito.user.id).first()
    }

    return response.ok({ data: this.format(settings!) })
  }

  async update({ cognito, request, response }: HttpContext) {
    const body = request.only([
      'maxRiskPerTradePct',
      'maxDailyLossPct',
      'maxDrawdownPct',
      'maxConsecutiveLosses',
      'minRrRatio',
      'defaultLotSize',
      'maxLotSize',
      'maxOpenPositions',
      'tradingStartUtc',
      'tradingEndUtc',
      'newsBufferMinutes',
      'maxTradeDurationMinutes',
      'dailyTargetPct',
      'reduceLotAtPct',
      'minAdxEntry',
      'minAlignmentScore',
      'maxSpreadPips',
      'allowedPairs',
      'killSwitch',
      'autoTradingEnabled',
    ])

    const update: Record<string, unknown> = { updated_at: new Date() }

    if (body.maxRiskPerTradePct !== undefined) update.max_risk_per_trade_pct = body.maxRiskPerTradePct
    if (body.maxDailyLossPct !== undefined) update.max_daily_loss_pct = body.maxDailyLossPct
    if (body.maxDrawdownPct !== undefined) update.max_drawdown_pct = body.maxDrawdownPct
    if (body.maxConsecutiveLosses !== undefined) update.max_consecutive_losses = body.maxConsecutiveLosses
    if (body.minRrRatio !== undefined) update.min_rr_ratio = body.minRrRatio
    if (body.defaultLotSize !== undefined) update.default_lot_size = body.defaultLotSize
    if (body.maxLotSize !== undefined) update.max_lot_size = body.maxLotSize
    if (body.maxOpenPositions !== undefined) update.max_open_positions = body.maxOpenPositions
    if (body.tradingStartUtc !== undefined) update.trading_start_utc = body.tradingStartUtc
    if (body.tradingEndUtc !== undefined) update.trading_end_utc = body.tradingEndUtc
    if (body.newsBufferMinutes !== undefined) update.news_buffer_minutes = body.newsBufferMinutes
    if (body.maxTradeDurationMinutes !== undefined) update.max_trade_duration_minutes = body.maxTradeDurationMinutes
    if (body.dailyTargetPct !== undefined) update.daily_target_pct = body.dailyTargetPct
    if (body.reduceLotAtPct !== undefined) update.reduce_lot_at_pct = body.reduceLotAtPct
    if (body.minAdxEntry !== undefined) update.min_adx_entry = body.minAdxEntry
    if (body.minAlignmentScore !== undefined) update.min_alignment_score = body.minAlignmentScore
    if (body.maxSpreadPips !== undefined) update.max_spread_pips = body.maxSpreadPips
    if (body.allowedPairs !== undefined) update.allowed_pairs = JSON.stringify(body.allowedPairs)
    if (body.killSwitch !== undefined) update.kill_switch = body.killSwitch
    if (body.autoTradingEnabled !== undefined) update.auto_trading_enabled = body.autoTradingEnabled

    await db.from('trading_settings').where('user_id', cognito.user.id).update(update)

    const settings = await db.from('trading_settings').where('user_id', cognito.user.id).first()
    return response.ok({ data: this.format(settings!), message: 'Settings actualizados' })
  }

  async reset({ cognito, response }: HttpContext) {
    await db.from('trading_settings').where('user_id', cognito.user.id).update({
      ...DEFAULTS,
      updated_at: new Date(),
    })

    const settings = await db.from('trading_settings').where('user_id', cognito.user.id).first()
    return response.ok({ data: this.format(settings!), message: 'Settings reseteados a defaults' })
  }

  private format(s: Record<string, unknown>) {
    return {
      risk: {
        maxRiskPerTradePct: Number(s.max_risk_per_trade_pct),
        maxDailyLossPct: Number(s.max_daily_loss_pct),
        maxDrawdownPct: Number(s.max_drawdown_pct),
        maxConsecutiveLosses: Number(s.max_consecutive_losses),
        minRrRatio: Number(s.min_rr_ratio),
      },
      sizing: {
        defaultLotSize: Number(s.default_lot_size),
        maxLotSize: Number(s.max_lot_size),
        maxOpenPositions: Number(s.max_open_positions),
      },
      session: {
        tradingStartUtc: s.trading_start_utc,
        tradingEndUtc: s.trading_end_utc,
        newsBufferMinutes: Number(s.news_buffer_minutes),
        maxTradeDurationMinutes: Number(s.max_trade_duration_minutes),
      },
      target: {
        dailyTargetPct: Number(s.daily_target_pct),
        reduceLotAtPct: Number(s.reduce_lot_at_pct),
      },
      filters: {
        minAdxEntry: Number(s.min_adx_entry),
        minAlignmentScore: Number(s.min_alignment_score),
        maxSpreadPips: Number(s.max_spread_pips),
      },
      pairs: {
        allowedPairs: typeof s.allowed_pairs === 'string' ? JSON.parse(s.allowed_pairs as string) : s.allowed_pairs,
      },
      system: {
        killSwitch: s.kill_switch,
        autoTradingEnabled: s.auto_trading_enabled,
      },
    }
  }
}
