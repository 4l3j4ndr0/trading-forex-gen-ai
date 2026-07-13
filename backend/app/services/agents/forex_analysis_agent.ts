import { Agent, BedrockModel, tool } from '@strands-agents/sdk'
import { z } from 'zod'
import { createTechnicalAnalysisAgent } from './technical_analysis_agent.js'
import { createRiskManagementAgent } from './risk_management_agent.js'
import { createSignalsAgent } from './signals_agent.js'
import env from '#start/env'

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
  response: string
  durationMs: number
}

/**
 * Crea un tool que delega al agente de análisis técnico
 */
function createTechnicalAnalysisTool() {
  return tool({
    name: 'run_technical_analysis',
    description:
      'Delega al Agente de Análisis Técnico especializado. Obtiene datos OHLCV multi-temporalidad (D1, H4, H1), calcula indicadores (EMA, RSI, MACD, ATR, Bollinger) y evalúa confluencias. Usar SIEMPRE como primer paso antes de evaluar riesgo.',
    inputSchema: z.object({
      symbol: z.string().describe('Par de forex a analizar, ej: "EUR/USD"'),
      instruction: z
        .string()
        .describe(
          'Instrucción específica para el análisis. Ej: "Analiza D1, H4 y H1, identifica confluencias y propón niveles de entrada"'
        ),
    }),
    callback: async (input) => {
      const agent = createTechnicalAnalysisAgent()
      try {
        const result = await agent.invoke(
          `${input.instruction}\n\nPar: ${input.symbol}\nTimeframes: D1, H4, H1`
        )
        return typeof result.lastMessage === 'string'
          ? result.lastMessage
          : JSON.stringify(result.lastMessage)
      } catch (error) {
        return `Error en análisis técnico: ${error instanceof Error ? error.message : 'Unknown'}`
      }
    },
  })
}

/**
 * Crea un tool que delega al agente de gestión de riesgo
 */
function createRiskManagementTool(settings: UserSettings) {
  return tool({
    name: 'evaluate_risk',
    description:
      'Delega al Agente de Gestión de Riesgo. Calcula lot size, valida R:R, verifica drawdown y correlaciones. Usar DESPUÉS del análisis técnico, pasándole los niveles propuestos.',
    inputSchema: z.object({
      symbol: z.string().describe('Par de forex'),
      accountBalance: z.number().describe('Balance del trader en USD'),
      technicalContext: z
        .string()
        .describe(
          'Resultado del análisis técnico con niveles propuestos (entry, SL, TP). Pasar textualmente.'
        ),
    }),
    callback: async (input) => {
      const agent = createRiskManagementAgent(settings)
      try {
        const result = await agent.invoke(
          `Evalúa el riesgo de esta operación:

Par: ${input.symbol}
Balance: $${input.accountBalance}
Riesgo máximo permitido: ${settings.maxRiskPerTrade}%

Análisis técnico:
${input.technicalContext}

Usa calculate_risk con los niveles propuestos. Si no hay niveles claros, indica que no hay operación para validar.`
        )
        return typeof result.lastMessage === 'string'
          ? result.lastMessage
          : JSON.stringify(result.lastMessage)
      } catch (error) {
        return `Error en evaluación de riesgo: ${error instanceof Error ? error.message : 'Unknown'}`
      }
    },
  })
}

/**
 * Crea un tool que delega al agente de señales
 */
function createSignalDecisionTool(settings: UserSettings, context: AnalysisContext) {
  return tool({
    name: 'decide_signal',
    description:
      'Delega al Agente de Señales para la decisión FINAL. Decide si emitir o rechazar la señal basándose en el análisis técnico + validación de riesgo. Si emite, guarda en BD. Usar SOLO después de technical_analysis y evaluate_risk.',
    inputSchema: z.object({
      technicalAnalysis: z.string().describe('Resultado completo del análisis técnico'),
      riskAssessment: z.string().describe('Resultado completo de la evaluación de riesgo'),
    }),
    callback: async (input) => {
      const agent = createSignalsAgent(settings)
      try {
        const result = await agent.invoke(
          `Toma la decisión final sobre emitir o no una señal.

## Análisis Técnico:
${input.technicalAnalysis}

## Evaluación de Riesgo:
${input.riskAssessment}

## Contexto:
- User ID: ${context.userId}
- Pair ID: ${context.pairId}
- Par: ${context.symbol}
- Balance: $${context.accountBalance}
- Score mínimo: ${settings.minSignalScore}/10
- Clasificación mínima: Clase ${settings.minSignalClass}

Si todo cuadra → usa emit_signal
Si no → explica por qué y cuándo re-evaluar`
        )
        return typeof result.lastMessage === 'string'
          ? result.lastMessage
          : JSON.stringify(result.lastMessage)
      } catch (error) {
        return `Error en decisión de señal: ${error instanceof Error ? error.message : 'Unknown'}`
      }
    },
  })
}

function buildOrchestratorPrompt(settings: UserSettings): string {
  return `Eres el Agente Orquestador del Sistema de Trading Forex con IA. Tu rol es coordinar el análisis de un par de divisas delegando a agentes especializados y tomando decisiones inteligentes sobre el flujo.

## Tu Equipo de Agentes:
1. **run_technical_analysis** — Análisis técnico multi-temporalidad (D1→H4→H1)
2. **evaluate_risk** — Validación de riesgo y cálculo de posición
3. **decide_signal** — Decisión final de emitir/rechazar señal

## Configuración del Trader:
- Riesgo máximo: ${settings.maxRiskPerTrade}%
- Drawdown diario: ${settings.maxDailyDrawdown}%
- Drawdown semanal: ${settings.maxWeeklyDrawdown}%
- Posiciones simultáneas: ${settings.maxOpenPositions}
- Score mínimo: ${settings.minSignalScore}/10
- Clasificación mínima: Clase ${settings.minSignalClass}
- Sesiones: ${settings.preferredSessions.join(', ')}
- Zona horaria: ${settings.timezone}

## Tu Proceso de Decisión:

### SIEMPRE empezar con run_technical_analysis
Pide análisis completo Top-Down del par.

### Evaluar resultado del análisis técnico:
- Si el análisis indica score < ${settings.minSignalScore} o no hay confluencias suficientes → **DETENER**. No invocar risk ni signal. Reportar directamente al usuario que no hay oportunidad y por qué.
- Si el análisis indica oportunidad potencial (score >= ${settings.minSignalScore}, confluencias >= 3) → continuar con evaluate_risk.

### Evaluar resultado del riesgo:
- Si el riesgo es rechazado (semáforo rojo, R:R < 1:2, etc.) → **DETENER**. No invocar signal. Reportar que el setup no cumple criterios de riesgo.
- Si el riesgo es aceptable → continuar con decide_signal.

### Resultado final:
- Si se emitió señal → confirmar al usuario con resumen
- Si no se emitió → explicar claramente por qué y qué vigilar

## Reglas:
- SÉ EFICIENTE: Si el primer paso ya muestra que no hay oportunidad, NO gastes tokens invocando los demás agentes.
- SÉ CLARO: Tu respuesta final al usuario debe ser un resumen ejecutivo legible, no JSON crudo.
- RESPETA los parámetros del trader — nunca sugieras operar fuera de sus límites.
- Incluye siempre: par analizado, timeframes, dirección del mercado, y si hay o no señal.`
}

/**
 * Ejecuta el análisis con el agente orquestador inteligente
 */
export async function runAnalysis(context: AnalysisContext): Promise<AnalysisResult> {
  const startTime = Date.now()
  const modelId = env.get('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-5')
  const region = env.get('AWS_REGION', 'us-east-1')

  const orchestrator = new Agent({
    model: new BedrockModel({ modelId, region, temperature: 0.3 }),
    tools: [
      createTechnicalAnalysisTool(),
      createRiskManagementTool(context.settings),
      createSignalDecisionTool(context.settings, context),
    ],
    systemPrompt: buildOrchestratorPrompt(context.settings),
    printer: false,
  })

  try {
    const result = await orchestrator.invoke(
      `Analiza el par ${context.symbol} y determina si hay una oportunidad de trading válida para este trader.

Datos:
- Balance: $${context.accountBalance}
- Trigger: ${context.triggerType}
- Hora actual UTC: ${new Date().toISOString()}

Ejecuta tu proceso de decisión completo.`
    )

    const response =
      typeof result.lastMessage === 'string'
        ? result.lastMessage
        : JSON.stringify(result.lastMessage)

    return {
      success: true,
      response,
      durationMs: Date.now() - startTime,
    }
  } catch (error) {
    return {
      success: false,
      response: error instanceof Error ? error.message : 'Error desconocido en el orquestador',
      durationMs: Date.now() - startTime,
    }
  }
}
