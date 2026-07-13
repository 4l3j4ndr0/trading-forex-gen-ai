<template>
  <q-page class="signals-page q-pa-md q-pa-md-lg">
    <!-- Header -->
    <div class="row items-center q-mb-lg">
      <div class="col">
        <div class="text-h5 text-weight-bold">Señales de Trading</div>
        <div class="text-caption text-grey-6">
          Análisis con IA multi-agente — Claude Sonnet 5 + Indicadores Técnicos + Gestión de Riesgo
        </div>
      </div>
    </div>

    <!-- Panel de Análisis -->
    <q-card flat class="analysis-card q-mb-lg">
      <q-card-section>
        <div class="row items-center q-mb-md">
          <q-icon name="psychology" size="28px" color="primary" class="q-mr-sm" />
          <div class="text-subtitle1 text-weight-bold">Ejecutar Análisis</div>
        </div>

        <div class="row q-col-gutter-md items-end">
          <div class="col-12 col-sm-5">
            <q-select
              v-model="selectedPair"
              :options="availablePairs"
              label="Par a analizar"
              outlined
              dense
              emit-value
              map-options
            >
              <template #prepend>
                <q-icon name="currency_exchange" />
              </template>
            </q-select>
          </div>

          <div class="col-12 col-sm-4">
            <q-btn
              color="primary"
              icon="play_arrow"
              label="Ejecutar Análisis"
              :loading="analyzing"
              :disable="!selectedPair"
              no-caps
              unelevated
              class="full-width"
              @click="runAnalysis"
            />
          </div>

          <div class="col-12 col-sm-3">
            <q-btn
              flat
              color="grey-7"
              icon="refresh"
              label="Recargar señales"
              no-caps
              class="full-width"
              @click="loadSignals"
            />
          </div>
        </div>
      </q-card-section>

      <!-- Resultado del análisis -->
      <q-card-section v-if="analysisResult" class="q-pt-none">
        <q-separator class="q-mb-md" />
        <div class="row items-center q-mb-sm">
          <q-icon
            :name="analysisResult.success ? 'check_circle' : 'info'"
            :color="analysisResult.success ? 'positive' : 'orange'"
            size="20px"
            class="q-mr-xs"
          />
          <span class="text-subtitle2 text-weight-medium">
            Análisis completado en {{ (analysisResult.durationMs / 1000).toFixed(1) }}s
            <q-badge
              v-if="analysisResult.signalsGenerated > 0"
              color="positive"
              class="q-ml-sm"
            >
              {{ analysisResult.signalsGenerated }} señal(es) generada(s)
            </q-badge>
          </span>
        </div>

        <q-expansion-item
          label="Ver análisis completo"
          icon="description"
          dense
          header-class="text-primary"
        >
          <q-card flat bordered class="q-mt-sm">
            <q-card-section class="analysis-output">
              <pre class="text-body2">{{ analysisResult.analysis }}</pre>
            </q-card-section>
          </q-card>
        </q-expansion-item>
      </q-card-section>

      <!-- Loading state -->
      <q-card-section v-if="analyzing" class="q-pt-none">
        <q-separator class="q-mb-md" />
        <div class="row items-center q-gutter-sm">
          <q-spinner-dots size="24px" color="primary" />
          <span class="text-body2 text-grey-7">
            {{ analysisStep }}
          </span>
        </div>
        <q-linear-progress
          :value="analysisProgress"
          color="primary"
          class="q-mt-sm"
          rounded
        />
      </q-card-section>
    </q-card>

    <!-- Lista de Señales -->
    <div class="row items-center q-mb-md">
      <div class="col">
        <div class="text-subtitle1 text-weight-bold">Señales Generadas</div>
      </div>
      <q-btn-toggle
        v-model="signalFilter"
        toggle-color="primary"
        :options="filterOptions"
        no-caps
        dense
        rounded
        unelevated
        size="sm"
      />
    </div>

    <!-- Empty state -->
    <q-card v-if="!loadingSignals && signals.length === 0" flat class="text-center q-pa-xl" bordered>
      <q-icon name="gps_off" size="64px" color="grey-4" />
      <div class="text-h6 text-grey-5 q-mt-md">No hay señales aún</div>
      <div class="text-body2 text-grey-5 q-mt-xs">
        Selecciona un par y ejecuta un análisis para generar tu primera señal
      </div>
    </q-card>

    <!-- Signal cards -->
    <div class="row q-col-gutter-md">
      <div v-for="signal in signals" :key="signal.id" class="col-12 col-md-6">
        <q-card flat class="signal-card" bordered>
          <q-card-section class="q-pb-sm">
            <div class="row items-center justify-between">
              <div class="row items-center q-gutter-xs">
                <q-badge
                  :color="signal.classification === 'A' ? 'positive' : 'warning'"
                  :label="'Clase ' + signal.classification"
                />
                <q-badge
                  :color="signal.direction === 'buy' ? 'green-8' : 'red-8'"
                  :label="signal.direction.toUpperCase()"
                />
                <q-badge color="blue-grey-1" text-color="blue-grey-8">
                  Score {{ signal.score }}/10
                </q-badge>
              </div>
              <q-chip
                :color="statusColor(signal.status)"
                text-color="white"
                dense
                size="sm"
              >
                {{ signal.status }}
              </q-chip>
            </div>
          </q-card-section>

          <q-card-section class="q-pt-none">
            <div class="text-h6 text-weight-bold">{{ signal.pair_symbol }}</div>
            <div class="text-caption text-grey-6">
              {{ signal.signal_type }} · {{ formatDate(signal.created_at) }}
            </div>

            <q-separator class="q-my-sm" />

            <div class="row q-col-gutter-xs text-body2">
              <div class="col-6">
                <span class="text-grey-6">Entry:</span>
                <span class="text-weight-medium q-ml-xs">{{ signal.entry_price }}</span>
              </div>
              <div class="col-6">
                <span class="text-grey-6">SL:</span>
                <span class="text-weight-medium text-negative q-ml-xs">{{ signal.stop_loss }}</span>
              </div>
              <div class="col-6">
                <span class="text-grey-6">TP1:</span>
                <span class="text-weight-medium text-positive q-ml-xs">{{ signal.take_profit_1 }}</span>
              </div>
              <div class="col-6">
                <span class="text-grey-6">TP2:</span>
                <span class="text-weight-medium text-positive q-ml-xs">{{ signal.take_profit_2 ?? '—' }}</span>
              </div>
              <div class="col-6">
                <span class="text-grey-6">TP3:</span>
                <span class="text-weight-medium text-positive q-ml-xs">{{ signal.take_profit_3 ?? '—' }}</span>
              </div>
              <div class="col-6">
                <span class="text-grey-6">R:R:</span>
                <span class="text-weight-medium q-ml-xs">1:{{ signal.risk_reward }}</span>
              </div>
            </div>

            <q-separator class="q-my-sm" />

            <div class="row q-gutter-xs text-caption">
              <q-badge outline color="grey-7">
                {{ signal.lot_size }} lots
              </q-badge>
              <q-badge outline color="grey-7">
                {{ signal.pips_at_risk }} pips riesgo
              </q-badge>
              <q-badge outline color="grey-7">
                {{ signal.confluence_count }} confluencias
              </q-badge>
            </div>
          </q-card-section>

          <q-card-actions v-if="signal.status === 'pending'">
            <q-btn flat color="positive" label="Activar" icon="play_arrow" no-caps dense />
            <q-btn flat color="negative" label="Cancelar" icon="close" no-caps dense />
            <q-space />
            <q-btn flat color="grey" icon="info" dense>
              <q-tooltip>{{ signal.notes }}</q-tooltip>
            </q-btn>
          </q-card-actions>
        </q-card>
      </div>
    </div>

    <!-- Loading signals -->
    <div v-if="loadingSignals" class="text-center q-pa-lg">
      <q-spinner-dots size="32px" color="primary" />
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/services/api'

const $q = useQuasar()
const authStore = useAuthStore()

interface Signal {
  id: string
  pair_symbol: string
  pair_category: string
  direction: string
  signal_type: string
  classification: string
  score: number
  entry_price: number
  stop_loss: number
  take_profit_1: number
  take_profit_2: number | null
  take_profit_3: number | null
  lot_size: number
  risk_percent: number
  risk_reward: number
  pips_at_risk: number
  confluence_count: number
  status: string
  notes: string | null
  created_at: string
}

interface AnalysisResponse {
  data: {
    success: boolean
    analysis: string
    durationMs: number
    signalsGenerated: number
  }
}

interface SignalsResponse {
  data: Signal[]
  meta: { total: number; page: number; limit: number }
}

const selectedPair = ref<string | null>(null)
const analyzing = ref(false)
const analysisStep = ref('')
const analysisProgress = ref(0)
const analysisResult = ref<{
  success: boolean
  analysis: string
  durationMs: number
  signalsGenerated: number
} | null>(null)

const signals = ref<Signal[]>([])
const loadingSignals = ref(false)
const signalFilter = ref('all')

const filterOptions = [
  { label: 'Todas', value: 'all' },
  { label: 'Pendientes', value: 'pending' },
  { label: 'Activas', value: 'active' },
]

// Pares disponibles del usuario
const availablePairs = ref<{ label: string; value: string }[]>([])

function buildPairOptions() {
  const pairs = authStore.settings?.preferredPairs ?? ['EUR/USD', 'GBP/USD', 'USD/JPY']
  availablePairs.value = pairs.map((p) => ({ label: p, value: p }))
  if (availablePairs.value.length > 0 && !selectedPair.value) {
    selectedPair.value = availablePairs.value[0]?.value ?? null
  }
}

async function runAnalysis() {
  if (!selectedPair.value) return

  analyzing.value = true
  analysisResult.value = null
  analysisStep.value = '📰 Verificando noticias y sentimiento del mercado...'
  analysisProgress.value = 0.1

  // Simular progreso visual (el análisis real puede tardar 20-60s)
  const progressInterval = setInterval(() => {
    if (analysisProgress.value < 0.9) {
      analysisProgress.value += 0.05
      if (analysisProgress.value > 0.3 && analysisProgress.value < 0.5) {
        analysisStep.value = '🔬 Ejecutando análisis técnico multi-temporalidad (D1→H4→H1)...'
      } else if (analysisProgress.value >= 0.5 && analysisProgress.value < 0.7) {
        analysisStep.value = '🛡️ Evaluando riesgo y calculando posición...'
      } else if (analysisProgress.value >= 0.7) {
        analysisStep.value = '🎯 Agente de señales tomando decisión final...'
      }
    }
  }, 3000)

  try {
    const res = await api.post<AnalysisResponse>('/analysis/run', {
      symbol: selectedPair.value,
    })
    analysisResult.value = res.data
    analysisProgress.value = 1

    if (analysisResult.value && analysisResult.value.signalsGenerated > 0) {
      $q.notify({
        type: 'positive',
        message: `🎯 ${analysisResult.value.signalsGenerated} señal(es) generada(s) para ${selectedPair.value}`,
        icon: 'gps_fixed',
      })
      void loadSignals()
    } else {
      $q.notify({
        type: 'info',
        message: 'Análisis completado — No se generó señal en este momento',
        icon: 'info',
      })
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Error al ejecutar el análisis'
    $q.notify({ type: 'negative', message, icon: 'error' })
    analysisResult.value = {
      success: false,
      analysis: message,
      durationMs: 0,
      signalsGenerated: 0,
    }
  } finally {
    clearInterval(progressInterval)
    analyzing.value = false
  }
}

async function loadSignals() {
  loadingSignals.value = true
  try {
    const params: Record<string, string> = {}
    if (signalFilter.value !== 'all') params.status = signalFilter.value
    const res = await api.get<SignalsResponse>('/signals', params)
    signals.value = res.data ?? []
  } catch {
    // Silencioso
  } finally {
    loadingSignals.value = false
  }
}

function statusColor(status: string): string {
  const colors: Record<string, string> = {
    pending: 'blue-grey',
    active: 'primary',
    hit_tp1: 'positive',
    hit_tp2: 'positive',
    hit_tp3: 'green-9',
    stopped_out: 'negative',
    cancelled: 'grey',
    expired: 'grey-6',
  }
  return colors[status] ?? 'grey'
}

function formatDate(date: string): string {
  return new Date(date).toLocaleString('es-CO', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

watch(signalFilter, () => void loadSignals())

onMounted(() => {
  buildPairOptions()
  void loadSignals()
})
</script>

<style scoped>
.signals-page {
  max-width: 1200px;
  margin: 0 auto;
}

.analysis-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
}

.signal-card {
  border-radius: 12px;
  transition: box-shadow 0.2s;
}
.signal-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}

.analysis-output {
  max-height: 400px;
  overflow-y: auto;
}
.analysis-output pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Roboto Mono', monospace;
  font-size: 13px;
  line-height: 1.6;
  margin: 0;
}
</style>
