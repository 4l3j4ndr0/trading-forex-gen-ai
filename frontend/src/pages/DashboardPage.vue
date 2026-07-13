<template>
  <q-page class="dashboard-page q-pa-md q-pa-md-lg">
    <!-- Header -->
    <div class="row items-center q-mb-lg">
      <div class="col">
        <div class="row items-center q-gutter-sm">
          <q-avatar size="42px" color="primary" text-color="white" class="text-weight-bold">
            {{ authStore.initials }}
          </q-avatar>
          <div>
            <div class="text-h6 text-weight-bold q-ma-none">
              Bienvenido{{ authStore.fullName ? ', ' + authStore.fullName : '' }}
            </div>
            <div class="text-caption text-grey-6">{{ authStore.email }}</div>
          </div>
        </div>
      </div>
      <q-btn flat round icon="logout" color="grey-7" @click="handleLogout">
        <q-tooltip>Cerrar sesión</q-tooltip>
      </q-btn>
    </div>

    <!-- Métricas rápidas -->
    <div class="row q-col-gutter-md q-mb-lg">
      <div class="col-6 col-md-3">
        <q-card flat class="metric-card">
          <q-card-section class="q-pa-md">
            <div class="row items-center no-wrap">
              <q-icon name="account_balance_wallet" size="28px" color="primary" class="q-mr-sm" />
              <div>
                <div class="text-caption text-grey-6">Balance</div>
                <div class="text-subtitle1 text-weight-bold">
                  {{ formatCurrency(authStore.accountBalance) }}
                </div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-6 col-md-3">
        <q-card flat class="metric-card">
          <q-card-section class="q-pa-md">
            <div class="row items-center no-wrap">
              <q-icon name="gps_fixed" size="28px" color="cyan-8" class="q-mr-sm" />
              <div>
                <div class="text-caption text-grey-6">Señales Activas</div>
                <div class="text-subtitle1 text-weight-bold">0</div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-6 col-md-3">
        <q-card flat class="metric-card">
          <q-card-section class="q-pa-md">
            <div class="row items-center no-wrap">
              <q-icon name="swap_vert" size="28px" color="positive" class="q-mr-sm" />
              <div>
                <div class="text-caption text-grey-6">Trades Abiertos</div>
                <div class="text-subtitle1 text-weight-bold">0</div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-6 col-md-3">
        <q-card flat class="metric-card">
          <q-card-section class="q-pa-md">
            <div class="row items-center no-wrap">
              <q-icon name="trending_up" size="28px" color="amber-8" class="q-mr-sm" />
              <div>
                <div class="text-caption text-grey-6">Win Rate</div>
                <div class="text-subtitle1 text-weight-bold">—</div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Configuración del Trader -->
    <div class="row q-col-gutter-md">
      <!-- Gestión de Riesgo -->
      <div class="col-12 col-md-6">
        <q-card flat class="settings-card full-height">
          <q-card-section class="q-pb-none">
            <div class="row items-center q-mb-sm">
              <q-icon name="shield" size="24px" color="red-8" class="q-mr-sm" />
              <div class="text-subtitle1 text-weight-bold">Gestión de Riesgo</div>
            </div>
            <q-separator />
          </q-card-section>

          <q-card-section class="q-gutter-md">
            <div>
              <div class="row items-center justify-between q-mb-xs">
                <span class="text-body2 text-grey-8">
                  Riesgo por operación
                  <q-icon name="help_outline" size="16px" color="grey-5" class="cursor-pointer">
                    <q-tooltip max-width="280px" class="text-body2">
                      Porcentaje de tu balance que arriesgas en cada trade. Si tu balance es $10,000 y configuras 1%, tu pérdida máxima por operación será $100. <br><br><strong>Recomendado:</strong> 1-2% para proteger tu capital a largo plazo.
                    </q-tooltip>
                  </q-icon>
                </span>
                <q-badge color="red-1" text-color="red-9" class="text-weight-bold">
                  {{ form.maxRiskPerTrade }}%
                </q-badge>
              </div>
              <q-slider
                v-model="form.maxRiskPerTrade"
                :min="0.25"
                :max="5"
                :step="0.25"
                color="red-8"
                label
                :label-value="form.maxRiskPerTrade + '%'"
              />
              <div class="text-caption text-grey-5">Recomendado: 1-2% máximo</div>
            </div>

            <div>
              <div class="row items-center justify-between q-mb-xs">
                <span class="text-body2 text-grey-8">
                  Drawdown diario máximo
                  <q-icon name="help_outline" size="16px" color="grey-5" class="cursor-pointer">
                    <q-tooltip max-width="280px" class="text-body2">
                      Pérdida máxima permitida en un día. Si la alcanzas, el sistema deja de enviarte señales hasta el día siguiente. <br><br>Protege contra el <em>revenge trading</em> y días de alta volatilidad.
                    </q-tooltip>
                  </q-icon>
                </span>
                <q-badge color="orange-1" text-color="orange-9" class="text-weight-bold">
                  {{ form.maxDailyDrawdown }}%
                </q-badge>
              </div>
              <q-slider
                v-model="form.maxDailyDrawdown"
                :min="2"
                :max="15"
                :step="1"
                color="orange-8"
                label
                :label-value="form.maxDailyDrawdown + '%'"
              />
            </div>

            <div>
              <div class="row items-center justify-between q-mb-xs">
                <span class="text-body2 text-grey-8">
                  Drawdown semanal máximo
                  <q-icon name="help_outline" size="16px" color="grey-5" class="cursor-pointer">
                    <q-tooltip max-width="280px" class="text-body2">
                      Pérdida máxima acumulada en 7 días. Si la alcanzas, el sistema reduce o detiene las señales el resto de la semana. <br><br>Te obliga a pausar cuando el mercado no te favorece.
                    </q-tooltip>
                  </q-icon>
                </span>
                <q-badge color="orange-1" text-color="orange-9" class="text-weight-bold">
                  {{ form.maxWeeklyDrawdown }}%
                </q-badge>
              </div>
              <q-slider
                v-model="form.maxWeeklyDrawdown"
                :min="5"
                :max="30"
                :step="1"
                color="orange-8"
                label
                :label-value="form.maxWeeklyDrawdown + '%'"
              />
            </div>

            <div>
              <div class="row items-center justify-between q-mb-xs">
                <span class="text-body2 text-grey-8">
                  Posiciones simultáneas
                  <q-icon name="help_outline" size="16px" color="grey-5" class="cursor-pointer">
                    <q-tooltip max-width="280px" class="text-body2">
                      Número máximo de trades que puedes tener abiertos al mismo tiempo. <br><br>Limita tu exposición total. Con 3 posiciones a 1% de riesgo, tu exposición máxima es 3% si todas tocan Stop Loss.
                    </q-tooltip>
                  </q-icon>
                </span>
                <q-badge color="blue-1" text-color="blue-9" class="text-weight-bold">
                  {{ form.maxOpenPositions }}
                </q-badge>
              </div>
              <q-slider
                v-model="form.maxOpenPositions"
                :min="1"
                :max="10"
                :step="1"
                color="blue-8"
                label
              />
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Cuenta y Señales -->
      <div class="col-12 col-md-6">
        <q-card flat class="settings-card full-height">
          <q-card-section class="q-pb-none">
            <div class="row items-center q-mb-sm">
              <q-icon name="tune" size="24px" color="primary" class="q-mr-sm" />
              <div class="text-subtitle1 text-weight-bold">Cuenta y Señales</div>
            </div>
            <q-separator />
          </q-card-section>

          <q-card-section class="q-gutter-md">
            <div class="row q-col-gutter-sm">
              <div class="col-8">
                <q-input
                  v-model.number="form.accountBalance"
                  type="number"
                  label="Balance de cuenta"
                  outlined
                  dense
                  prefix="$"
                  hint="Capital disponible para operar"
                >
                  <template #append>
                    <q-icon name="help_outline" size="18px" color="grey-5" class="cursor-pointer">
                      <q-tooltip max-width="260px" class="text-body2">
                        Tu capital total en la cuenta del broker. El sistema lo usa para calcular el tamaño de cada posición según tu % de riesgo.
                      </q-tooltip>
                    </q-icon>
                  </template>
                </q-input>
              </div>
              <div class="col-4">
                <q-select
                  v-model="form.accountCurrency"
                  :options="currencies"
                  label="Moneda"
                  outlined
                  dense
                />
              </div>
            </div>

            <div>
              <div class="text-body2 text-grey-8 q-mb-xs">
                Score mínimo para señales
                <q-icon name="help_outline" size="16px" color="grey-5" class="cursor-pointer">
                  <q-tooltip max-width="280px" class="text-body2">
                    Puntuación de 1 a 10 que la IA asigna según la cantidad y calidad de confluencias técnicas. <br><br>Con score 6 recibes más señales; con 8+ solo las de mayor probabilidad.
                  </q-tooltip>
                </q-icon>
              </div>
              <q-btn-toggle
                v-model="form.minSignalScore"
                toggle-color="primary"
                :options="scoreOptions"
                spread
                no-caps
                dense
                rounded
                unelevated
              />
              <div class="text-caption text-grey-5 q-mt-xs">
                Solo recibirás señales con score ≥ {{ form.minSignalScore }}
              </div>
            </div>

            <div>
              <div class="text-body2 text-grey-8 q-mb-xs">
                Clasificación mínima
                <q-icon name="help_outline" size="16px" color="grey-5" class="cursor-pointer">
                  <q-tooltip max-width="300px" class="text-body2">
                    <strong>Clase A (alta):</strong> 4+ confluencias, todos los timeframes alineados, R:R mínimo 1:3. Pocas señales pero alta probabilidad.<br><br>
                    <strong>Clase B (media):</strong> 3 confluencias, R:R mínimo 1:2. Más oportunidades con algo más de riesgo.
                  </q-tooltip>
                </q-icon>
              </div>
              <q-btn-toggle
                v-model="form.minSignalClass"
                toggle-color="primary"
                :options="classOptions"
                spread
                no-caps
                dense
                rounded
                unelevated
              />
            </div>

            <q-select
              v-model="form.timezone"
              :options="timezones"
              label="Zona horaria"
              outlined
              dense
              emit-value
              map-options
            />
          </q-card-section>
        </q-card>
      </div>

      <!-- Pares Preferidos -->
      <div class="col-12 col-md-6">
        <q-card flat class="settings-card">
          <q-card-section class="q-pb-none">
            <div class="row items-center q-mb-sm">
              <q-icon name="currency_exchange" size="24px" color="teal-8" class="q-mr-sm" />
              <div class="text-subtitle1 text-weight-bold">
                Pares Preferidos
                <q-icon name="help_outline" size="16px" color="grey-5" class="cursor-pointer">
                  <q-tooltip max-width="280px" class="text-body2">
                    El sistema solo analizará y generará señales para los pares que selecciones. <br><br>Menos pares = análisis más profundo. Se recomienda máximo 5 pares activos.
                  </q-tooltip>
                </q-icon>
              </div>
            </div>
            <q-separator />
          </q-card-section>

          <q-card-section>
            <div class="text-caption text-grey-6 q-mb-sm">
              Selecciona los pares sobre los cuales quieres recibir análisis y señales
            </div>
            <div class="row q-gutter-sm">
              <q-chip
                v-for="pair in availablePairs"
                :key="pair"
                :selected="form.preferredPairs.includes(pair)"
                clickable
                color="grey-2"
                text-color="grey-9"
                :class="{ 'selected-chip': form.preferredPairs.includes(pair) }"
                @click="togglePair(pair)"
              >
                <q-avatar
                  v-if="form.preferredPairs.includes(pair)"
                  icon="check"
                  color="primary"
                  text-color="white"
                  size="xs"
                />
                {{ pair }}
              </q-chip>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Sesiones y Alertas -->
      <div class="col-12 col-md-6">
        <q-card flat class="settings-card">
          <q-card-section class="q-pb-none">
            <div class="row items-center q-mb-sm">
              <q-icon name="schedule" size="24px" color="purple-8" class="q-mr-sm" />
              <div class="text-subtitle1 text-weight-bold">
                Sesiones y Alertas
                <q-icon name="help_outline" size="16px" color="grey-5" class="cursor-pointer">
                  <q-tooltip max-width="300px" class="text-body2">
                    El mercado Forex opera 24h pero cada sesión tiene características distintas. <br><br><strong>Tokyo:</strong> rangos, baja volatilidad (pares JPY). <br><strong>London:</strong> alta volatilidad, breakouts (EUR, GBP). <br><strong>New York:</strong> continuaciones (USD, CAD). <br><strong>Overlap London-NY:</strong> máxima liquidez.
                  </q-tooltip>
                </q-icon>
              </div>
            </div>
            <q-separator />
          </q-card-section>

          <q-card-section class="q-gutter-md">
            <div>
              <div class="text-body2 text-grey-8 q-mb-sm">Sesiones de mercado activas</div>
              <div class="row q-gutter-sm">
                <q-chip
                  v-for="session in availableSessions"
                  :key="session.value"
                  :selected="form.preferredSessions.includes(session.value)"
                  clickable
                  color="grey-2"
                  text-color="grey-9"
                  :class="{ 'selected-chip': form.preferredSessions.includes(session.value) }"
                  @click="toggleSession(session.value)"
                >
                  <q-avatar
                    v-if="form.preferredSessions.includes(session.value)"
                    icon="check"
                    color="purple"
                    text-color="white"
                    size="xs"
                  />
                  {{ session.label }}
                </q-chip>
              </div>
            </div>

            <q-separator />

            <div>
              <div class="text-body2 text-grey-8 q-mb-sm">Canales de alerta</div>
              <q-list dense>
                <q-item tag="label">
                  <q-item-section>
                    <q-item-label>WebSocket (tiempo real)</q-item-label>
                    <q-item-label caption>Alertas instantáneas en la app</q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <q-toggle v-model="form.alertChannels.websocket" color="primary" />
                  </q-item-section>
                </q-item>
                <q-item tag="label">
                  <q-item-section>
                    <q-item-label>Email</q-item-label>
                    <q-item-label caption>Resumen de señales por correo</q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <q-toggle v-model="form.alertChannels.email" color="primary" />
                  </q-item-section>
                </q-item>
              </q-list>
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Botón Guardar flotante -->
    <q-page-sticky position="bottom-right" :offset="[24, 24]">
      <q-btn
        fab
        icon="save"
        color="primary"
        :loading="saving"
        :disable="!hasChanges"
        @click="saveSettings"
      >
        <q-tooltip v-if="hasChanges">Guardar cambios</q-tooltip>
        <q-tooltip v-else>Sin cambios pendientes</q-tooltip>
      </q-btn>
    </q-page-sticky>
  </q-page>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { api } from '@/services/api'

const $q = useQuasar()
const authStore = useAuthStore()
const router = useRouter()
const saving = ref(false)

const availablePairs = [
  'EUR/USD', 'GBP/USD', 'USD/JPY', 'USD/CHF',
  'AUD/USD', 'USD/CAD', 'NZD/USD', 'EUR/GBP',
  'EUR/JPY', 'GBP/JPY',
]

const availableSessions = [
  { value: 'tokyo', label: '🇯🇵 Tokyo (00:00-09:00 UTC)' },
  { value: 'london', label: '🇬🇧 London (07:00-16:00 UTC)' },
  { value: 'new_york', label: '🇺🇸 New York (12:00-21:00 UTC)' },
]

const currencies = ['USD', 'EUR', 'GBP', 'COP']

const scoreOptions = [
  { label: '5', value: 5 },
  { label: '6', value: 6 },
  { label: '7', value: 7 },
  { label: '8', value: 8 },
  { label: '9', value: 9 },
]

const classOptions = [
  { label: 'Clase A (alta)', value: 'A' },
  { label: 'Clase B (media)', value: 'B' },
]

const timezones = [
  { label: 'América/Bogotá (UTC-5)', value: 'America/Bogota' },
  { label: 'América/New York (UTC-5/-4)', value: 'America/New_York' },
  { label: 'América/México (UTC-6)', value: 'America/Mexico_City' },
  { label: 'Europa/Londres (UTC+0/+1)', value: 'Europe/London' },
  { label: 'Europa/Madrid (UTC+1/+2)', value: 'Europe/Madrid' },
]

const form = reactive<{
  accountBalance: number
  accountCurrency: string
  maxRiskPerTrade: number
  maxDailyDrawdown: number
  maxWeeklyDrawdown: number
  maxOpenPositions: number
  preferredPairs: string[]
  preferredSessions: string[]
  minSignalScore: number
  minSignalClass: string
  alertChannels: Record<string, boolean>
  timezone: string
}>({
  accountBalance: 0,
  accountCurrency: 'USD',
  maxRiskPerTrade: 1.0,
  maxDailyDrawdown: 6,
  maxWeeklyDrawdown: 15,
  maxOpenPositions: 3,
  preferredPairs: ['EUR/USD', 'GBP/USD', 'USD/JPY'],
  preferredSessions: ['london', 'new_york'],
  minSignalScore: 6,
  minSignalClass: 'B',
  alertChannels: { websocket: true, email: false },
  timezone: 'America/Bogota',
})

const originalForm = ref('')

const hasChanges = computed(() => JSON.stringify(form) !== originalForm.value)

function syncFormFromStore() {
  form.accountBalance = authStore.accountBalance
  form.accountCurrency = authStore.accountCurrency
  if (authStore.settings) {
    const s = authStore.settings
    form.maxRiskPerTrade = s.maxRiskPerTrade
    form.maxDailyDrawdown = s.maxDailyDrawdown
    form.maxWeeklyDrawdown = s.maxWeeklyDrawdown
    form.maxOpenPositions = s.maxOpenPositions
    form.preferredPairs = Array.isArray(s.preferredPairs) ? [...s.preferredPairs] : []
    form.preferredSessions = Array.isArray(s.preferredSessions) ? [...s.preferredSessions] : []
    form.minSignalScore = s.minSignalScore
    form.minSignalClass = s.minSignalClass
    form.alertChannels = { ...s.alertChannels }
    form.timezone = s.timezone
  }
  originalForm.value = JSON.stringify(form)
}

function togglePair(pair: string) {
  const idx = form.preferredPairs.indexOf(pair)
  if (idx >= 0) form.preferredPairs.splice(idx, 1)
  else form.preferredPairs.push(pair)
}

function toggleSession(session: string) {
  const idx = form.preferredSessions.indexOf(session)
  if (idx >= 0) form.preferredSessions.splice(idx, 1)
  else form.preferredSessions.push(session)
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: form.accountCurrency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(value)
}

async function saveSettings() {
  saving.value = true
  try {
    await api.put('/me/settings', { ...form })
    await authStore.loadProfile()
    syncFormFromStore()
    $q.notify({ type: 'positive', message: 'Configuración guardada correctamente', icon: 'check_circle' })
  } catch {
    $q.notify({ type: 'negative', message: 'Error al guardar la configuración', icon: 'error' })
  } finally {
    saving.value = false
  }
}

async function handleLogout() {
  await authStore.logOut()
  void router.replace('/login')
}

onMounted(() => {
  if (authStore.profileLoaded) {
    syncFormFromStore()
  } else {
    void authStore.loadProfile().then(() => syncFormFromStore())
  }
})
</script>

<style scoped>
.dashboard-page {
  max-width: 1200px;
  margin: 0 auto;
}

.metric-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  transition: box-shadow 0.2s;
}
.metric-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.settings-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
}

.selected-chip {
  background-color: #e0f2fe !important;
  border: 1px solid #0ea5e9;
  color: #0369a1 !important;
  font-weight: 600;
}

.full-height {
  height: 100%;
}
</style>
