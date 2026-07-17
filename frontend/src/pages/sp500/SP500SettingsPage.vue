<template>
  <q-page padding>
    <div class="row items-center q-mb-lg">
      <q-icon name="tune" size="sm" color="primary" class="q-mr-sm" />
      <div class="text-h6 text-weight-bold">SP500 Settings</div>
    </div>

    <div class="row q-col-gutter-lg">
      <!-- Instrument & Killzones -->
      <div class="col-12 col-md-6">
        <q-card flat class="premium-card">
          <q-card-section>
            <div class="text-subtitle1 text-weight-medium q-mb-md">
              <q-icon name="show_chart" class="q-mr-sm" />Instrument & Sessions
            </div>
            <q-form class="q-gutter-sm">
              <q-input v-model="form.symbol" outlined dense label="Symbol" readonly />
              <q-input v-model.number="form.pointValue" outlined dense label="Point Value ($/pt/lot)" type="number" step="0.01" />

              <div class="text-caption text-grey q-mt-md">AM Killzone (UTC)</div>
              <div class="row q-gutter-sm">
                <q-input v-model="form.amKillzoneStart" outlined dense label="Start" class="col" mask="##:##" placeholder="13:30">
                  <template #prepend><q-icon name="schedule" /></template>
                </q-input>
                <q-input v-model="form.amKillzoneEnd" outlined dense label="End" class="col" mask="##:##" placeholder="15:30">
                  <template #prepend><q-icon name="schedule" /></template>
                </q-input>
              </div>

              <div class="text-caption text-grey q-mt-md">PM Killzone (UTC)</div>
              <div class="row q-gutter-sm">
                <q-input v-model="form.pmKillzoneStart" outlined dense label="Start" class="col" mask="##:##" placeholder="18:00">
                  <template #prepend><q-icon name="schedule" /></template>
                </q-input>
                <q-input v-model="form.pmKillzoneEnd" outlined dense label="End" class="col" mask="##:##" placeholder="20:00">
                  <template #prepend><q-icon name="schedule" /></template>
                </q-input>
              </div>

              <div class="text-caption text-grey q-mt-md">Regular Session (UTC)</div>
              <div class="row q-gutter-sm">
                <q-input v-model="form.premarketStart" outlined dense label="Pre-market" class="col" mask="##:##" />
                <q-input v-model="form.regularSessionStart" outlined dense label="Open" class="col" mask="##:##" />
                <q-input v-model="form.regularSessionEnd" outlined dense label="Close" class="col" mask="##:##" />
              </div>
            </q-form>
          </q-card-section>
        </q-card>
      </div>

      <!-- Risk & Targets -->
      <div class="col-12 col-md-6">
        <q-card flat class="premium-card">
          <q-card-section>
            <div class="text-subtitle1 text-weight-medium q-mb-md">
              <q-icon name="shield" class="q-mr-sm" />Risk & Targets
            </div>
            <q-form class="q-gutter-sm">
              <div class="text-caption text-grey">Position Sizing</div>
              <q-input v-model.number="form.maxRiskPerTradePct" outlined dense label="Risk per trade (%)" type="number" step="0.1" />
              <div class="row q-gutter-sm">
                <q-input v-model.number="form.minLot" outlined dense label="Min Lot" type="number" step="0.01" class="col" />
                <q-input v-model.number="form.maxLot" outlined dense label="Max Lot" type="number" step="0.1" class="col" />
              </div>
              <q-input v-model.number="form.maxOpenPositions" outlined dense label="Max open positions" type="number" />

              <div class="text-caption text-grey q-mt-md">Risk Limits</div>
              <q-input v-model.number="form.maxDailyLossPct" outlined dense label="Max daily loss (%)" type="number" step="0.5" />
              <q-input v-model.number="form.maxConsecutiveLosses" outlined dense label="Max consecutive losses" type="number" />
              <q-input v-model.number="form.minRrRatio" outlined dense label="Min R:R ratio" type="number" step="0.1" />

              <div class="text-caption text-grey q-mt-md">Targets</div>
              <q-input v-model.number="form.dailyTargetPct" outlined dense label="Daily target (%)" type="number" step="0.1" />
              <q-input v-model.number="form.dailyTargetPoints" outlined dense label="Daily target (points)" type="number" step="5" />

              <div class="text-caption text-grey q-mt-md">Analysis</div>
              <q-input v-model.number="form.minStructureScore" outlined dense label="Min MTF structure score" type="number" />
              <q-input v-model.number="form.newsBufferMinutes" outlined dense label="News buffer (minutes)" type="number" />

              <div class="text-caption text-grey q-mt-md">System</div>
              <q-toggle v-model="form.killSwitch" label="Kill Switch" color="red" />
              <q-toggle v-model="form.autoTradingEnabled" label="Auto Trading" color="green" />
            </q-form>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Save Button -->
    <div class="row justify-end q-mt-lg">
      <q-btn color="primary" label="Guardar Cambios" icon="save" :loading="saving" @click="save" />
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { useSP500Store } from '@/stores/sp500'
import { useQuasar } from 'quasar'

const sp500Store = useSP500Store()
const $q = useQuasar()
const saving = ref(false)

const form = reactive({
  symbol: 'US500Cash',
  pointValue: 1.0,
  minLot: 0.01,
  maxLot: 5.0,
  maxRiskPerTradePct: 1.0,
  maxDailyLossPct: 5.0,
  maxConsecutiveLosses: 5,
  minRrRatio: 1.5,
  maxOpenPositions: 5,
  amKillzoneStart: '13:30',
  amKillzoneEnd: '15:30',
  pmKillzoneStart: '18:00',
  pmKillzoneEnd: '20:00',
  premarketStart: '12:00',
  regularSessionStart: '13:30',
  regularSessionEnd: '20:00',
  newsBufferMinutes: 15,
  dailyTargetPct: 1.0,
  dailyTargetPoints: 30.0,
  minStructureScore: 2,
  minSweepDistancePoints: 5.0,
  killSwitch: false,
  autoTradingEnabled: true,
})

async function loadFromStore() {
  await sp500Store.loadSettings()
  if (sp500Store.settings) {
    Object.assign(form, sp500Store.settings)
  }
}

async function save() {
  saving.value = true
  try {
    await sp500Store.saveSettings(form)
    $q.notify({ type: 'positive', message: 'SP500 settings guardados' })
  } catch {
    $q.notify({ type: 'negative', message: 'Error guardando settings' })
  } finally {
    saving.value = false
  }
}

onMounted(() => void loadFromStore())
</script>
