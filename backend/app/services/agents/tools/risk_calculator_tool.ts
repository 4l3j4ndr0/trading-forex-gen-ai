import { tool } from '@strands-agents/sdk'
import { z } from 'zod'

/**
 * Obtiene el tamaño del pip según el par
 */
function getPipSize(symbol: string): number {
  return symbol.includes('JPY') ? 0.01 : 0.0001
}

/**
 * Calcula el valor de 1 pip por lote estándar (aprox)
 */
function getPipValue(symbol: string): number {
  // Simplificado — para pares XXX/USD es $10, para USD/XXX es ~$10/precio
  if (symbol.endsWith('USD') || symbol.endsWith('/USD')) return 10
  if (symbol.includes('JPY')) return 6.67
  return 10 // Aproximación para crosses
}

export const riskCalculatorTool = tool({
  name: 'calculate_risk',
  description:
    'Calcula el tamaño de posición (lot size), pips en riesgo y valida si el trade cumple las reglas de riesgo del usuario. Usar SIEMPRE antes de emitir una señal.',
  inputSchema: z.object({
    symbol: z.string().describe('Par de forex, ej: "EUR/USD"'),
    direction: z.enum(['buy', 'sell']).describe('Dirección del trade'),
    entryPrice: z.number().describe('Precio de entrada propuesto'),
    stopLoss: z.number().describe('Nivel de Stop Loss propuesto'),
    takeProfit1: z.number().describe('Take Profit 1 (50% del lote)'),
    takeProfit2: z.number().optional().describe('Take Profit 2 (30% del lote)'),
    takeProfit3: z.number().optional().describe('Take Profit 3 (20% del lote)'),
    accountBalance: z.number().describe('Balance de la cuenta del usuario en USD'),
    maxRiskPercent: z.number().describe('% máximo de riesgo por operación (ej: 1.0 = 1%)'),
    atr: z.number().optional().describe('ATR actual para validación'),
  }),
  callback: (input) => {
    const {
      symbol,
      direction,
      entryPrice,
      stopLoss,
      takeProfit1,
      takeProfit2,
      takeProfit3,
      accountBalance,
      maxRiskPercent,
      atr,
    } = input

    const pipSize = getPipSize(symbol)
    const pipValue = getPipValue(symbol)

    // Calcular pips en riesgo
    const pipsAtRisk = Math.abs(entryPrice - stopLoss) / pipSize

    // Calcular pips a cada TP
    const pipsToTP1 = Math.abs(takeProfit1 - entryPrice) / pipSize
    const pipsToTP2 = takeProfit2 ? Math.abs(takeProfit2 - entryPrice) / pipSize : 0
    const pipsToTP3 = takeProfit3 ? Math.abs(takeProfit3 - entryPrice) / pipSize : 0

    // Risk:Reward ratio (usando TP1 como mínimo)
    const riskReward = pipsToTP1 / pipsAtRisk

    // Calcular lot size
    const riskInMoney = accountBalance * (maxRiskPercent / 100)
    const lotSize = Math.floor((riskInMoney / (pipsAtRisk * pipValue)) * 100) / 100

    // Validaciones
    const validations: string[] = []
    let isValid = true

    // R:R mínimo 1:2
    if (riskReward < 2) {
      validations.push(`❌ R:R insuficiente (${riskReward.toFixed(2)}:1). Mínimo 1:2`)
      isValid = false
    } else {
      validations.push(`✅ R:R aceptable (${riskReward.toFixed(2)}:1)`)
    }

    // SL coherente con dirección
    if (direction === 'buy' && stopLoss >= entryPrice) {
      validations.push('❌ Stop Loss debe estar DEBAJO del entry para BUY')
      isValid = false
    }
    if (direction === 'sell' && stopLoss <= entryPrice) {
      validations.push('❌ Stop Loss debe estar ENCIMA del entry para SELL')
      isValid = false
    }

    // TP coherente con dirección
    if (direction === 'buy' && takeProfit1 <= entryPrice) {
      validations.push('❌ Take Profit debe estar ENCIMA del entry para BUY')
      isValid = false
    }
    if (direction === 'sell' && takeProfit1 >= entryPrice) {
      validations.push('❌ Take Profit debe estar DEBAJO del entry para SELL')
      isValid = false
    }

    // Validar ATR (SL no debería ser menor que 1x ATR)
    if (atr) {
      const atrPips = atr / pipSize
      if (pipsAtRisk < atrPips * 0.8) {
        validations.push(
          `⚠️ SL muy ajustado (${pipsAtRisk.toFixed(1)} pips) vs ATR (${atrPips.toFixed(1)} pips). Riesgo de barrida.`
        )
      }
    }

    // Lot size razonable
    if (lotSize < 0.01) {
      validations.push('❌ Lot size demasiado pequeño. Balance insuficiente o SL muy amplio.')
      isValid = false
    }

    return JSON.stringify({
      symbol,
      direction,
      isValid,
      position: {
        lotSize,
        riskInMoney: Math.round(riskInMoney * 100) / 100,
        pipsAtRisk: Math.round(pipsAtRisk * 10) / 10,
        pipsToTP1: Math.round(pipsToTP1 * 10) / 10,
        pipsToTP2: Math.round(pipsToTP2 * 10) / 10,
        pipsToTP3: Math.round(pipsToTP3 * 10) / 10,
        riskReward: Math.round(riskReward * 100) / 100,
        maxLoss: Math.round(pipsAtRisk * pipValue * lotSize * 100) / 100,
      },
      levels: {
        entry: entryPrice,
        stopLoss,
        takeProfit1,
        takeProfit2: takeProfit2 ?? null,
        takeProfit3: takeProfit3 ?? null,
      },
      validations,
    })
  },
})
