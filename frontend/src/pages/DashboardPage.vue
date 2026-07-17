<template>
  <q-page class="q-pa-lg">
    <!-- Account Banner -->
    <q-banner
      v-if="store.accountType === 'demo'"
      class="banner-demo q-mb-lg"
      rounded
    >
      <template #avatar>
        <q-icon name="science" color="warning" />
      </template>
      <div class="text-weight-bold text-warning">Cuenta DEMO Activa</div>
      <div class="text-caption text-grey-5">
        El agente opera en un entorno simulado. Los resultados no afectan capital real.
      </div>
    </q-banner>

    <q-banner
      v-else-if="store.accountType === 'live'"
      class="banner-live q-mb-lg"
      rounded
    >
      <template #avatar>
        <q-icon name="account_balance" color="positive" />
      </template>
      <div class="text-weight-bold text-positive">Cuenta LIVE</div>
      <div class="text-caption text-grey-5">
        Operando con capital real. El agente gestiona el riesgo automáticamente.
      </div>
    </q-banner>

    <q-banner
      v-else-if="store.accountType === 'unknown'"
      class="premium-card q-mb-lg"
      rounded
    >
      <template #avatar>
        <q-icon name="link_off" color="grey" />
      </template>
      <div class="text-weight-bold text-grey-5">Sin conexión al broker</div>
      <div class="text-caption text-grey-6">
        Configura tu cuenta MT5 en Settings para empezar.
      </div>
    </q-banner>

    <!-- KPI Cards -->
    <div class="row q-col-gutter-lg q-mb-xl">
      <!-- Balance -->
      <div class="col-12 col-sm-6 col-lg-3">
        <q-card flat class="premium-card h-full q-pa-md kpi-accent-top kpi-accent-top--primary">
          <div class="row items-center justify-between q-mb-md">
            <div class="label-mini">Balance</div>
            <q-icon name="account_balance_wallet" color="grey-6" size="sm" />
          </div>
          <div class="text-h4 text-weight-bolder text-white number-display">
            ${{ store.balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
          </div>
          <div class="text-caption text-grey-5 q-mt-sm">
            Equity: <span class="text-white text-weight-medium">${{ store.equity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</span>
          </div>
        </q-card>
      </div>

      <!-- PnL Today -->
      <div class="col-12 col-sm-6 col-lg-3">
        <q-card flat class="premium-card h-full q-pa-md kpi-accent-top kpi-accent-top--positive">
          <div class="row items-center justify-between q-mb-md">
            <div class="label-mini">Net PnL (Hoy)</div>
            <q-icon
              :name="store.dailyPnl >= 0 ? 'trending_up' : 'trending_down'"
              :color="store.dailyPnl >= 0 ? 'positive' : 'negative'"
              size="sm"
            />
          </div>
          <div
            class="text-h4 text-weight-bolder number-display"
            :class="store.dailyPnl >= 0 ? 'text-positive' : 'text-negative'"
          >
            {{ store.dailyPnl >= 0 ? '+' : '' }}${{ store.dailyPnl.toFixed(2) }}
          </div>
          <div class="text-caption text-grey-5 q-mt-sm">
            Cestas cerradas: <span class="text-white text-weight-medium">{{ store.dailySummary?.tradesTotal || 0 }}</span>
          </div>
        </q-card>
      </div>

      <!-- Active Positions -->
      <div class="col-12 col-sm-6 col-lg-3">
        <q-card flat class="premium-card h-full q-pa-md">
          <div class="row items-center justify-between q-mb-md">
            <div class="label-mini">Posiciones Activas</div>
            <q-icon name="layers" color="grey-6" size="sm" />
          </div>
          <div class="text-h4 text-weight-bolder text-white number-display">
            {{ store.openPositions }}
          </div>
          <div class="text-caption text-grey-5 q-mt-sm">
            Lotes expuestos: <span class="text-white text-weight-medium">{{ totalLots.toFixed(2) }}</span>
          </div>
        </q-card>
      </div>

      <!-- Daily Target -->
      <div class="col-12 col-sm-6 col-lg-3">
        <q-card flat class="premium-card h-full q-pa-md kpi-accent-top kpi-accent-top--warning">
          <div class="row items-center justify-between q-mb-sm">
            <div class="label-mini">Objetivo Diario (1%)</div>
            <div class="text-caption text-white text-weight-bold number-display">
              {{ targetPct.toFixed(1) }}%
            </div>
          </div>
          <div class="text-caption text-grey-5 q-mb-lg">
            Meta: ${{ dailyTarget.toFixed(2) }} USD
          </div>
          <q-linear-progress
            :value="Math.min(targetPct / 100, 1)"
            :color="targetPct >= 100 ? 'positive' : 'primary'"
            track-color="grey-9"
            size="8px"
            rounded
          />
        </q-card>
      </div>
    </div>

    <!-- Main Content Grid -->
    <div class="row q-col-gutter-lg">
      <!-- Basket Monitor Table -->
      <div class="col-12 col-lg-8">
        <q-card flat class="premium-card">
          <q-table
            flat
            dark
            class="bg-transparent"
            :rows="store.openTrades"
            :columns="positionColumns"
            row-key="id"
            hide-pagination
            :pagination="{ rowsPerPage: 0 }"
            no-data-label="No hay posiciones abiertas"
          >
            <template #top>
              <div class="text-subtitle1 text-weight-bold text-white">Monitoreo de Cestas (Live)</div>
              <q-space />
              <q-btn flat round dense icon="refresh" color="grey-5" @click="refreshData">
                <q-tooltip>Actualizar MT5</q-tooltip>
              </q-btn>
            </template>

            <template #body-cell-symbol="props">
              <q-td :props="props" class="text-weight-bold text-white">
                {{ props.value }}
              </q-td>
            </template>

            <template #body-cell-side="props">
              <q-td :props="props">
                <q-chip
                  :class="props.value === 'BUY' ? 'chip-side-buy' : 'chip-side-sell'"
                  size="sm"
                  square
                  dense
                >
                  {{ props.value }}
                </q-chip>
              </q-td>
            </template>

            <template #body-cell-pnl_usd="props">
              <q-td
                :props="props"
                class="text-weight-bold number-display"
                :class="(props.value || 0) > 0 ? 'text-positive' : (props.value || 0) < 0 ? 'text-negative' : 'text-grey-5'"
              >
                {{ props.value ? (props.value > 0 ? '+' : '') + '$' + Number(props.value).toFixed(2) : '-' }}
              </q-td>
            </template>

            <template #no-data>
              <div class="full-width text-center q-py-xl">
                <q-icon name="inbox" size="48px" color="grey-7" />
                <div class="text-grey-5 q-mt-sm">No hay posiciones abiertas</div>
              </div>
            </template>
          </q-table>
        </q-card>
      </div>

      <!-- Right Column: Stats -->
      <div class="col-12 col-lg-4">
        <div class="column q-gutter-lg">
          <!-- Today Performance -->
          <q-card flat class="premium-card q-pa-md">
            <div class="label-mini q-mb-lg">Rendimiento Hoy</div>
            <div class="row text-center">
              <div class="col">
                <div class="text-h5 text-white text-weight-bold number-display">
                  {{ store.dailySummary?.tradesTotal || 0 }}
                </div>
                <div class="text-caption text-grey-5">Trades</div>
              </div>
              <div class="col" style="border-left: 1px solid var(--border-color); border-right: 1px solid var(--border-color)">
                <div class="text-h5 text-positive text-weight-bold number-display">
                  {{ store.dailySummary?.tradesWon || 0 }}
                </div>
                <div class="text-caption text-grey-5">Wins</div>
              </div>
              <div class="col">
                <div class="text-h5 text-negative text-weight-bold number-display">
                  {{ store.dailySummary?.tradesLost || 0 }}
                </div>
                <div class="text-caption text-grey-5">Losses</div>
              </div>
            </div>
          </q-card>

          <!-- 30d Metrics -->
          <q-card flat class="premium-card q-pa-md">
            <div class="label-mini q-mb-lg">Métricas Globales (30d)</div>
            <q-list dark separator>
              <q-item class="q-px-none">
                <q-item-section class="text-grey-5">Win Rate</q-item-section>
                <q-item-section side class="text-white text-weight-bold number-display">
                  {{ store.stats?.winRate || 0 }}%
                </q-item-section>
              </q-item>
              <q-item class="q-px-none">
                <q-item-section class="text-grey-5">Profit Factor</q-item-section>
                <q-item-section side class="text-white text-weight-bold number-display">
                  {{ store.stats?.profitFactor?.toFixed(2) || '0.00' }}
                </q-item-section>
              </q-item>
              <q-item class="q-px-none">
                <q-item-section class="text-grey-5">Max Drawdown</q-item-section>
                <q-item-section side class="text-white text-weight-bold number-display">
                  {{ store.stats?.maxDrawdown?.toFixed(1) || '0.0' }}%
                </q-item-section>
              </q-item>
              <q-item class="q-px-none">
                <q-item-section class="text-grey-5">Total PnL</q-item-section>
                <q-item-section
                  side
                  class="text-weight-bold number-display"
                  :class="(store.stats?.totalPnl || 0) >= 0 ? 'text-positive' : 'text-negative'"
                >
                  ${{ store.stats?.totalPnl?.toFixed(2) || '0.00' }}
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>
        </div>
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useTradingStore } from '@/stores/trading'

const store = useTradingStore()

const dailyTarget = computed(() => store.balance * 0.01)
const targetPct = computed(() => {
  const target = dailyTarget.value
  return target > 0 ? (store.dailyPnl / target) * 100 : 0
})

const totalLots = computed(() =>
  store.openTrades.reduce((sum, t) => sum + Number(t.lot_size || 0), 0)
)

const positionColumns = [
  { name: 'symbol', label: 'Símbolo', field: 'symbol', align: 'left' as const, sortable: true },
  { name: 'side', label: 'Side', field: 'side', align: 'center' as const },
  { name: 'lot_size', label: 'Lotes', field: 'lot_size', align: 'right' as const, format: (v: number | string) => Number(v).toFixed(2) },
  { name: 'entry_price', label: 'Entrada', field: 'entry_price', align: 'right' as const, classes: 'text-grey-4 number-display' },
  { name: 'current_price', label: 'Actual', field: 'current_price', align: 'right' as const, classes: 'text-white number-display', format: (v: number | string) => v || '-' },
  { name: 'pnl_usd', label: 'PnL', field: 'pnl_usd', align: 'right' as const },
]

async function refreshData() {
  await store.loadDashboard()
  await store.loadStats()
}

onMounted(async () => {
  await store.loadDashboard()
  await store.loadStats()
})
</script>
