import { tool } from '@strands-agents/sdk'
import { z } from 'zod'
import db from '@adonisjs/lucid/services/db'

export const emitSignalTool = tool({
  name: 'emit_signal',
  description:
    'Emite una señal de trading cuando el análisis técnico indica una oportunidad válida con confluencia >= 3 y riesgo validado. SOLO usar después de calculate_indicators y calculate_risk. Esta acción guarda la señal en la base de datos.',
  inputSchema: z.object({
    userId: z.string().describe('ID del usuario para quien se genera la señal'),
    pairId: z.number().describe('ID del par en la BD'),
    symbol: z.string().describe('Símbolo del par, ej: "EUR/USD"'),
    direction: z.enum(['buy', 'sell']).describe('Dirección: buy o sell'),
    signalType: z
      .enum(['continuation', 'reversal', 'breakout'])
      .describe('Tipo de señal basado en el contexto del mercado'),
    classification: z.enum(['A', 'B']).describe('A = alta confianza (4+ confluencias), B = media (3 confluencias)'),
    score: z.number().min(1).max(10).describe('Score de 1-10 basado en confluencias y calidad'),
    entryPrice: z.number().describe('Precio de entrada'),
    stopLoss: z.number().describe('Stop Loss'),
    takeProfit1: z.number().describe('Take Profit 1'),
    takeProfit2: z.number().optional().describe('Take Profit 2'),
    takeProfit3: z.number().optional().describe('Take Profit 3'),
    lotSize: z.number().describe('Tamaño del lote calculado por risk tool'),
    riskPercent: z.number().describe('% de riesgo usado'),
    riskReward: z.number().describe('Ratio riesgo:beneficio'),
    pipsAtRisk: z.number().describe('Pips hasta el SL'),
    pipsToTP1: z.number().describe('Pips hasta TP1'),
    pipsToTP2: z.number().optional().describe('Pips hasta TP2'),
    pipsToTP3: z.number().optional().describe('Pips hasta TP3'),
    confluences: z
      .array(
        z.object({
          factorType: z.string().describe('Tipo: ema_alignment, rsi_oversold, macd_cross, etc.'),
          timeframe: z.string().describe('Timeframe donde se detectó'),
          description: z.string().describe('Descripción legible del factor'),
          weight: z.number().min(0).max(1).describe('Peso del factor (0-1)'),
        })
      )
      .describe('Lista de confluencias que validan la señal'),
    timeframeAlignment: z
      .record(z.string(), z.string())
      .describe('Alineación por timeframe: {"D1":"bullish","H4":"bullish","H1":"bullish"}'),
    notes: z.string().describe('Explicación del análisis y razón de la señal'),
  }),
  callback: async (input) => {
    try {
      const signalId = await db.transaction(async (trx) => {
        // Insertar señal
        const [signal] = await trx
          .insertQuery()
          .table('signals')
          .insert({
            user_id: input.userId,
            pair_id: input.pairId,
            direction: input.direction,
            signal_type: input.signalType,
            classification: input.classification,
            score: input.score,
            entry_price: input.entryPrice,
            stop_loss: input.stopLoss,
            take_profit_1: input.takeProfit1,
            take_profit_2: input.takeProfit2 ?? null,
            take_profit_3: input.takeProfit3 ?? null,
            lot_size: input.lotSize,
            risk_percent: input.riskPercent,
            risk_reward: input.riskReward,
            pips_at_risk: input.pipsAtRisk,
            pips_to_tp1: input.pipsToTP1,
            pips_to_tp2: input.pipsToTP2 ?? null,
            pips_to_tp3: input.pipsToTP3 ?? null,
            timeframe_alignment: JSON.stringify(input.timeframeAlignment),
            confluence_count: input.confluences.length,
            status: 'pending',
            notes: input.notes,
            expires_at: new Date(Date.now() + 4 * 60 * 60 * 1000), // 4 horas
            created_at: new Date(),
            updated_at: new Date(),
          })
          .returning('id')

        // Insertar confluencias
        const confluenceRows = input.confluences.map((c) => ({
          signal_id: signal.id,
          factor_type: c.factorType,
          timeframe: c.timeframe,
          description: c.description,
          weight: c.weight,
          created_at: new Date(),
        }))

        if (confluenceRows.length > 0) {
          await trx.insertQuery().table('signal_confluences').multiInsert(confluenceRows)
        }

        return signal.id as string
      })

      return JSON.stringify({
        success: true,
        signalId,
        message: `✅ Señal ${input.classification} emitida para ${input.symbol} (${input.direction.toUpperCase()}) — Score: ${input.score}/10, R:R ${input.riskReward}:1, ${input.confluences.length} confluencias`,
        summary: {
          pair: input.symbol,
          direction: input.direction,
          entry: input.entryPrice,
          sl: input.stopLoss,
          tp1: input.takeProfit1,
          tp2: input.takeProfit2,
          tp3: input.takeProfit3,
          classification: input.classification,
          score: input.score,
        },
      })
    } catch (error) {
      return JSON.stringify({
        success: false,
        message: `❌ Error al guardar la señal: ${error instanceof Error ? error.message : 'Unknown error'}`,
      })
    }
  },
})
