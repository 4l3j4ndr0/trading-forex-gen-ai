import type { HttpContext } from '@adonisjs/core/http'
import db from '@adonisjs/lucid/services/db'
import { runAnalysis } from '#services/agents/forex_analysis_agent'
import type { UserSettings } from '#services/agents/forex_analysis_agent'

export default class AnalysisController {
  /**
   * POST /api/v1/analysis/run
   * Ejecuta un análisis manual para un par específico usando el orquestador multi-agente
   */
  async run({ cognito, request, response }: HttpContext) {
    const { symbol } = request.only(['symbol'])

    if (!symbol) {
      return response.badRequest({ message: 'El campo "symbol" es requerido (ej: "EUR/USD")' })
    }

    // Buscar el par en la BD
    const pair = await db.from('pairs').where('symbol', symbol).where('is_active', true).first()
    if (!pair) {
      return response.notFound({ message: `Par "${symbol}" no encontrado o no está activo` })
    }

    // Obtener settings del usuario
    const settingsRow = await db.from('user_settings').where('user_id', cognito.user.id).first()
    const accountBalance = Number(cognito.user.accountBalance) || 10000

    const userSettings: UserSettings = {
      maxRiskPerTrade: settingsRow ? Number(settingsRow.max_risk_per_trade) : 1.0,
      maxDailyDrawdown: settingsRow ? Number(settingsRow.max_daily_drawdown) : 6.0,
      maxWeeklyDrawdown: settingsRow ? Number(settingsRow.max_weekly_drawdown) : 15.0,
      maxOpenPositions: settingsRow ? Number(settingsRow.max_open_positions) : 3,
      preferredPairs: settingsRow?.preferred_pairs ?? ['EUR/USD', 'GBP/USD'],
      preferredSessions: settingsRow?.preferred_sessions ?? ['london', 'new_york'],
      minSignalScore: settingsRow ? Number(settingsRow.min_signal_score) : 6,
      minSignalClass: settingsRow?.min_signal_class ?? 'B',
      timezone: settingsRow?.timezone ?? 'America/Bogota',
    }

    // Verificar que el par está en los preferidos del usuario
    if (!userSettings.preferredPairs.includes(symbol)) {
      return response.badRequest({
        message: `El par "${symbol}" no está en tus pares preferidos. Agrégalo en configuración.`,
      })
    }

    // Registrar el job de análisis
    const [job] = await db
      .insertQuery()
      .table('analysis_jobs')
      .insert({
        session: 'manual',
        pairs_analyzed: JSON.stringify([symbol]),
        signals_generated: 0,
        status: 'running',
        started_at: new Date(),
        created_at: new Date(),
      })
      .returning('id')

    try {
      // Ejecutar el orquestador multi-agente
      const result = await runAnalysis({
        userId: cognito.user.id,
        pairId: pair.id as number,
        symbol,
        accountBalance,
        settings: userSettings,
        triggerType: 'manual',
      })

      // Guardar análisis en BD
      const responseText = result.response
      // Extraer texto limpio del JSON del agente si aplica
      let cleanText = responseText
      try {
        const parsed = JSON.parse(responseText) as { content?: Array<{ text?: string }> }
        if (parsed.content?.[0]?.text) {
          cleanText = parsed.content[0].text
        }
      } catch {
        // No es JSON, usar tal cual
      }

      await db.insertQuery().table('analyses').insert({
        pair_id: pair.id,
        user_id: cognito.user.id,
        trigger_type: 'manual',
        timeframe_primary: 'H1',
        timeframes_analyzed: JSON.stringify(['D1', 'H4', 'H1']),
        summary: cleanText.slice(0, 2000),
        ai_reasoning: cleanText,
        status: result.success ? 'completed' : 'failed',
        executed_at: new Date(),
        duration_ms: result.durationMs,
        created_at: new Date(),
      })

      // Contar señales generadas
      const signalsCount = await db
        .from('signals')
        .where('user_id', cognito.user.id)
        .where('pair_id', pair.id as number)
        .where('created_at', '>=', new Date(Date.now() - 120000)) // últimos 2 minutos
        .count('* as total')

      const totalSignals = Number(signalsCount[0]?.total ?? 0)

      // Actualizar job
      await db.from('analysis_jobs').where('id', job.id).update({
        status: 'completed',
        signals_generated: totalSignals,
        finished_at: new Date(),
      })

      return response.ok({
        data: {
          success: result.success,
          analysis: result.response,
          durationMs: result.durationMs,
          signalsGenerated: totalSignals,
        },
      })
    } catch (error) {
      await db.from('analysis_jobs').where('id', job.id).update({
        status: 'failed',
        error_message: error instanceof Error ? error.message : 'Unknown error',
        finished_at: new Date(),
      })

      return response.internalServerError({
        message: 'Error al ejecutar el análisis',
        error: error instanceof Error ? error.message : 'Unknown',
      })
    }
  }

  /**
   * GET /api/v1/analyses
   * Historial de análisis del usuario
   */
  async analyses({ cognito, request, response }: HttpContext) {
    const { page = 1, limit = 10 } = request.qs()

    const offset = (Number(page) - 1) * Number(limit)

    const analyses = await db
      .from('analyses')
      .join('pairs', 'pairs.id', 'analyses.pair_id')
      .where('analyses.user_id', cognito.user.id)
      .select(
        'analyses.id',
        'analyses.trigger_type',
        'analyses.timeframe_primary',
        'analyses.ai_reasoning',
        'analyses.status',
        'analyses.duration_ms',
        'analyses.created_at',
        'pairs.symbol as pair_symbol'
      )
      .orderBy('analyses.created_at', 'desc')
      .offset(offset)
      .limit(Number(limit))

    const countResult = await db
      .from('analyses')
      .where('user_id', cognito.user.id)
      .count('* as total')

    return response.ok({
      data: analyses,
      meta: {
        total: Number(countResult[0]?.total ?? 0),
        page: Number(page),
        limit: Number(limit),
      },
    })
  }

  /**
   * GET /api/v1/signals
   * Lista las señales del usuario
   */
  async signals({ cognito, request, response }: HttpContext) {
    const { status, pair, classification, page = 1, limit = 20 } = request.qs()

    let query = db
      .from('signals')
      .join('pairs', 'pairs.id', 'signals.pair_id')
      .where('signals.user_id', cognito.user.id)
      .select('signals.*', 'pairs.symbol as pair_symbol', 'pairs.category as pair_category')
      .orderBy('signals.created_at', 'desc')

    if (status) query = query.where('signals.status', status)
    if (pair) query = query.where('pairs.symbol', pair)
    if (classification) query = query.where('signals.classification', classification)

    const offset = (Number(page) - 1) * Number(limit)
    const signals = await query.offset(offset).limit(Number(limit))

    const countResult = await db
      .from('signals')
      .where('user_id', cognito.user.id)
      .count('* as total')

    return response.ok({
      data: signals,
      meta: {
        total: Number(countResult[0]?.total ?? 0),
        page: Number(page),
        limit: Number(limit),
      },
    })
  }
}
