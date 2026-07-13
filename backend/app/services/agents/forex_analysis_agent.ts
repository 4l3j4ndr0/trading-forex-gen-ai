import { createTechnicalAnalysisAgent } from './technical_analysis_agent.js'
import { createRiskManagementAgent } from './risk_management_agent.js'
import { createSignalsAgent } from './signals_agent.js'

export interface UserSettings {
  maxRiskPerTrade: number
  maxDailyDrawdown: number
  maxWeeklyDrawdown: number
  maxOpenPositions: number
  preferredPairs: string[]
  preferredSessions: string[]
  minSignalScore: number
  minSignalClass: string
  timezone: string
}

export interface AnalysisContext {
  userId: string
  pairId: number
  symbol: string
  accountBalance: number
  settings: UserSettings
  triggerType: 'manual' | 'scheduled'
}

export interface AnalysisResult {
  success: boolean
  technicalAnalysis: string
  riskAssessment: string
  signalDecision: string
  durationMs: number
  steps: {
    technical: { success: boolean; durationMs: number }
    risk: { success: boolean; durationMs: number }
    signal: { success: boolean; durationMs: number }
  }
}

/**
 * Orquestador Multi-Agente — Workflow Secuencial
 *
 * Flujo: Análisis Técnico → Gestión de Riesgo → Decisión de Señal
 *
 * Cada agente recibe el output del anterior como contexto,
 * manteniendo separación de responsabilidades.
 */
export async function runAnalysis(context: AnalysisContext): Promise<AnalysisResult> {
  const totalStart = Date.now()

  const steps = {
    technical: { success: false, durationMs: 0 },
    risk: { success: false, durationMs: 0 },
    signal: { success: false, durationMs: 0 },
  }

  // ═══════════════════════════════════════════════════════════
  // PASO 1: Análisis Técnico Multi-Temporalidad
  // ═══════════════════════════════════════════════════════════
  let technicalAnalysis = ''
  const step1Start = Date.now()

  try {
    const techAgent = createTechnicalAnalysisAgent()
    const techResult = await techAgent.invoke(
      `Analiza el par ${context.symbol} usando Top-Down Analysis (D1 → H4 → H1).
      
Obtén los datos de mercado para cada timeframe y calcula los indicadores técnicos.
Identifica:
- Sesgo direccional en cada temporalidad
- Confluencias técnicas (mínimo 3 necesarias)
- Niveles clave de entrada, stop loss y take profit
- Score de confianza (1-10)

Si el score es menor a ${context.settings.minSignalScore}, indica que no hay oportunidad válida y explica por qué.`
    )

    technicalAnalysis =
      typeof techResult.lastMessage === 'string'
        ? techResult.lastMessage
        : JSON.stringify(techResult.lastMessage)
    steps.technical = { success: true, durationMs: Date.now() - step1Start }
  } catch (error) {
    technicalAnalysis = `Error en análisis técnico: ${error instanceof Error ? error.message : 'Unknown'}`
    steps.technical = { success: false, durationMs: Date.now() - step1Start }

    return {
      success: false,
      technicalAnalysis,
      riskAssessment: 'No ejecutado — análisis técnico falló',
      signalDecision: 'No ejecutado',
      durationMs: Date.now() - totalStart,
      steps,
    }
  }

  // ═══════════════════════════════════════════════════════════
  // PASO 2: Validación de Riesgo
  // ═══════════════════════════════════════════════════════════
  let riskAssessment = ''
  const step2Start = Date.now()

  try {
    const riskAgent = createRiskManagementAgent(context.settings)
    const riskResult = await riskAgent.invoke(
      `Evalúa el riesgo de esta operación basándote en el siguiente análisis técnico:

${technicalAnalysis}

Datos del trader:
- Balance: $${context.accountBalance}
- Riesgo máximo por operación: ${context.settings.maxRiskPerTrade}%
- Par: ${context.symbol}

Usa el tool calculate_risk con los niveles propuestos por el análisis técnico.
Si el análisis no propone niveles claros (score bajo), indica que no hay operación para validar.`
    )

    riskAssessment =
      typeof riskResult.lastMessage === 'string'
        ? riskResult.lastMessage
        : JSON.stringify(riskResult.lastMessage)
    steps.risk = { success: true, durationMs: Date.now() - step2Start }
  } catch (error) {
    riskAssessment = `Error en evaluación de riesgo: ${error instanceof Error ? error.message : 'Unknown'}`
    steps.risk = { success: false, durationMs: Date.now() - step2Start }

    return {
      success: false,
      technicalAnalysis,
      riskAssessment,
      signalDecision: 'No ejecutado — evaluación de riesgo falló',
      durationMs: Date.now() - totalStart,
      steps,
    }
  }

  // ═══════════════════════════════════════════════════════════
  // PASO 3: Decisión de Señal
  // ═══════════════════════════════════════════════════════════
  let signalDecision = ''
  const step3Start = Date.now()

  try {
    const signalsAgent = createSignalsAgent(context.settings)
    const signalResult = await signalsAgent.invoke(
      `Toma la decisión final sobre emitir o no una señal de trading.

## Análisis Técnico:
${technicalAnalysis}

## Evaluación de Riesgo:
${riskAssessment}

## Contexto:
- User ID: ${context.userId}
- Pair ID: ${context.pairId}
- Par: ${context.symbol}
- Balance: $${context.accountBalance}
- Score mínimo requerido: ${context.settings.minSignalScore}/10
- Clasificación mínima: Clase ${context.settings.minSignalClass}

Si el análisis muestra una oportunidad válida Y el riesgo está validado:
→ Usa emit_signal con todos los datos

Si NO hay oportunidad válida:
→ Explica por qué y qué debería cambiar para generar señal`
    )

    signalDecision =
      typeof signalResult.lastMessage === 'string'
        ? signalResult.lastMessage
        : JSON.stringify(signalResult.lastMessage)
    steps.signal = { success: true, durationMs: Date.now() - step3Start }
  } catch (error) {
    signalDecision = `Error en decisión de señal: ${error instanceof Error ? error.message : 'Unknown'}`
    steps.signal = { success: false, durationMs: Date.now() - step3Start }
  }

  return {
    success: steps.technical.success && steps.risk.success && steps.signal.success,
    technicalAnalysis,
    riskAssessment,
    signalDecision,
    durationMs: Date.now() - totalStart,
    steps,
  }
}
