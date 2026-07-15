<template>
  <q-page padding>
    <div class="text-h6 text-weight-bold q-mb-lg">Configuración</div>

    <div class="row q-col-gutter-lg">
      <!-- Broker Config -->
      <div class="col-12 col-md-6">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle1 text-weight-medium q-mb-md">
              <q-icon name="dns" class="q-mr-sm" />Broker (MT5)
            </div>

            <q-form @submit.prevent="saveBroker" class="q-gutter-sm">
              <q-select v-model="broker.brokerName" :options="['XM', 'ICMarkets', 'Pepperstone', 'Exness']" outlined dense label="Broker" />
              <q-input v-model="broker.mt5Login" outlined dense label="MT5 Login (número de cuenta)" type="number" />
              <q-input v-model="broker.mt5Password" outlined dense label="MT5 Password" type="password" />
              <q-input v-model="broker.mt5Server" outlined dense label="MT5 Server" placeholder="XMGlobal-MT5 6" />
              <q-input v-model="broker.symbolSuffix" outlined dense label="Symbol Suffix" placeholder="#" />
              <q-select v-model="broker.accountType" :options="['demo', 'live']" outlined dense label="Tipo de cuenta" />

              <div class="row q-gutter-sm q-mt-md">
                <q-btn type="submit" color="primary" label="Guardar" :loading="savingBroker" />
                <q-btn outline color="blue" label="Test Conexión" @click="testBroker" :loading="testingBroker" />
              </div>
            </q-form>

            <q-banner v-if="brokerStatus" :class="brokerStatus.connected ? 'bg-green-1' : 'bg-red-1'" class="q-mt-md" rounded>
              <template #avatar><q-icon :name="brokerStatus.connected ? 'check_circle' : 'error'" :color="brokerStatus.connected ? 'green' : 'red'" /></template>
              {{ brokerStatus.connected ? 'Conexión exitosa — MT5 conectado' : 'No se pudo conectar al bridge' }}
            </q-banner>
          </q-card-section>
        </q-card>
      </div>

      <!-- Trading Settings -->
      <div class="col-12 col-md-6">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle1 text-weight-medium q-mb-md">
              <q-icon name="tune" class="q-mr-sm" />Trading Settings
            </div>

            <q-form @submit.prevent="saveSettings" class="q-gutter-sm">
              <div class="text-caption text-grey q-mt-sm">Riesgo</div>
              <q-input v-model.number="settings.maxRiskPerTradePct" outlined dense label="Max riesgo por trade (%)" type="number" step="0.1" />
              <q-input v-model.number="settings.maxDailyLossPct" outlined dense label="Max pérdida diaria (%)" type="number" step="0.1" />
              <q-input v-model.number="settings.minRrRatio" outlined dense label="Min R:R ratio" type="number" step="0.1" />
              <q-input v-model.number="settings.maxConsecutiveLosses" outlined dense label="Max pérdidas consecutivas" type="number" />

              <div class="text-caption text-grey q-mt-md">Sizing</div>
              <q-input v-model.number="settings.maxLotSize" outlined dense label="Max lot size" type="number" step="0.01" />
              <q-input v-model.number="settings.maxOpenPositions" outlined dense label="Max posiciones abiertas" type="number" />

              <div class="text-caption text-grey q-mt-md">Target</div>
              <q-input v-model.number="settings.dailyTargetPct" outlined dense label="Target diario (%)" type="number" step="0.1" />

              <div class="text-caption text-grey q-mt-md">Sesión</div>
              <div class="row q-gutter-sm">
                <q-input
                  v-model="settings.tradingStartUtc"
                  outlined
                  dense
                  label="Inicio (UTC)"
                  class="col"
                  mask="##:##"
                  placeholder="07:00"
                  hint="Formato HH:mm"
                >
                  <template #prepend>
                    <q-icon name="schedule" />
                  </template>
                </q-input>
                <q-input
                  v-model="settings.tradingEndUtc"
                  outlined
                  dense
                  label="Fin (UTC)"
                  class="col"
                  mask="##:##"
                  placeholder="20:00"
                  hint="Formato HH:mm"
                >
                  <template #prepend>
                    <q-icon name="schedule" />
                  </template>
                </q-input>
              </div>

              <div class="text-caption text-grey q-mt-md">Pares a Operar</div>
              <q-select
                v-model="settings.allowedPairs"
                :options="availablePairs"
                multiple
                outlined
                dense
                use-chips
                label="Pares permitidos"
              />

              <div class="text-caption text-grey q-mt-md">Sistema</div>
              <q-toggle v-model="settings.killSwitch" label="Kill Switch (pausar trading)" color="red" />
              <q-toggle v-model="settings.autoTradingEnabled" label="Auto Trading habilitado" color="green" />

              <div class="row q-gutter-sm q-mt-md">
                <q-btn type="submit" color="primary" label="Guardar" :loading="savingSettings" />
                <q-btn outline color="orange" label="Reset Defaults" @click="resetSettings" />
              </div>
            </q-form>
          </q-card-section>
        </q-card>
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { api } from '@/services/api'
import { useQuasar } from 'quasar'

const $q = useQuasar()

const broker = reactive({
  brokerName: 'XM',
  mt5Login: '',
  mt5Password: '',
  mt5Server: '',
  symbolSuffix: '#',
  accountType: 'demo',
})

const settings = reactive({
  maxRiskPerTradePct: 1.0,
  maxDailyLossPct: 1.0,
  minRrRatio: 1.5,
  maxConsecutiveLosses: 5,
  maxLotSize: 0.5,
  maxOpenPositions: 3,
  dailyTargetPct: 1.0,
  tradingStartUtc: '07:00',
  tradingEndUtc: '21:00',
  allowedPairs: ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'EURGBP'] as string[],
  killSwitch: false,
  autoTradingEnabled: true,
})

const availablePairs = ref<string[]>([])

const savingBroker = ref(false)
const testingBroker = ref(false)
const savingSettings = ref(false)
const brokerStatus = ref<{ connected: boolean } | null>(null)

async function loadBroker() {
  try {
    const res = await api.get<{ data: Record<string, unknown> | null }>('/broker')
    if (res.data) {
      broker.brokerName = (res.data.brokerName as string) || 'XM'
      broker.mt5Login = res.data.mt5Login != null ? String(Number(res.data.mt5Login)) : ''
      broker.mt5Server = (res.data.mt5Server as string) || ''
      broker.symbolSuffix = (res.data.symbolSuffix as string) || '#'
      broker.accountType = (res.data.accountType as string) || 'demo'
    }
  } catch { /* no config yet */ }
}

async function loadSettings() {
  try {
    const res = await api.get<{ data: Record<string, Record<string, unknown>> }>('/settings/trading')
    const d = res.data
    if (d.risk) {
      settings.maxRiskPerTradePct = d.risk.maxRiskPerTradePct as number
      settings.maxDailyLossPct = d.risk.maxDailyLossPct as number
      settings.minRrRatio = d.risk.minRrRatio as number
      settings.maxConsecutiveLosses = d.risk.maxConsecutiveLosses as number
    }
    if (d.sizing) {
      settings.maxLotSize = d.sizing.maxLotSize as number
      settings.maxOpenPositions = d.sizing.maxOpenPositions as number
    }
    if (d.target) {
      settings.dailyTargetPct = d.target.dailyTargetPct as number
    }
    if (d.session) {
      settings.tradingStartUtc = d.session.tradingStartUtc as string
      settings.tradingEndUtc = d.session.tradingEndUtc as string
    }
    if (d.system) {
      settings.killSwitch = d.system.killSwitch as boolean
      settings.autoTradingEnabled = d.system.autoTradingEnabled as boolean
    }
    if (d.pairs) {
      settings.allowedPairs = (d.pairs.allowedPairs as string[]) || []
    }
  } catch { /* defaults */ }
}

async function saveBroker() {
  savingBroker.value = true
  try {
    await api.post('/broker', broker)
    $q.notify({ type: 'positive', message: 'Broker configurado' })
  } catch {
    $q.notify({ type: 'negative', message: 'Error guardando broker' })
  } finally {
    savingBroker.value = false
  }
}

async function testBroker() {
  testingBroker.value = true
  try {
    const res = await api.post<{ connected: boolean }>('/broker/test', {})
    brokerStatus.value = res
  } catch {
    brokerStatus.value = { connected: false }
  } finally {
    testingBroker.value = false
  }
}

async function saveSettings() {
  savingSettings.value = true
  try {
    await api.put('/settings/trading', settings)
    $q.notify({ type: 'positive', message: 'Settings actualizados' })
  } catch {
    $q.notify({ type: 'negative', message: 'Error guardando settings' })
  } finally {
    savingSettings.value = false
  }
}

async function resetSettings() {
  try {
    await api.post('/settings/trading/reset', {})
    await loadSettings()
    $q.notify({ type: 'info', message: 'Settings reseteados a defaults' })
  } catch { /* */ }
}

onMounted(async () => {
  await Promise.all([loadBroker(), loadSettings(), loadPairs()])
})

async function loadPairs() {
  try {
    const res = await api.get<{ data: { symbol: string }[] }>('/pairs')
    availablePairs.value = res.data.map((p) => p.symbol)
  } catch {
    availablePairs.value = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'EURGBP', 'GBPJPY', 'NZDUSD', 'USDCHF']
  }
}
</script>
