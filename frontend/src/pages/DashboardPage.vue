<template>
  <q-page padding>
    <!-- Account Type Banner -->
    <q-banner v-if="store.accountType === 'demo'" class="bg-orange-1 text-orange-9 q-mb-md" rounded>
      <template #avatar><q-icon name="science" color="orange" /></template>
      <strong>Cuenta DEMO</strong> — Operando con dinero virtual. Los resultados no son reales.
    </q-banner>
    <q-banner v-else-if="store.accountType === 'live'" class="bg-green-1 text-green-9 q-mb-md" rounded>
      <template #avatar><q-icon name="account_balance" color="green" /></template>
      <strong>Cuenta REAL</strong> — Operando con dinero real. Ten precaución.
    </q-banner>
    <q-banner v-else-if="store.accountType === 'unknown'" class="bg-grey-2 text-grey-7 q-mb-md" rounded>
      <template #avatar><q-icon name="link_off" color="grey" /></template>
      <strong>Sin conexión al broker</strong> — Configura tu cuenta en Settings.
    </q-banner>

    <!-- Header Cards -->
    <div class="row q-col-gutter-md q-mb-lg">
      <div class="col-12 col-sm-6 col-md-3">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-caption text-grey">Balance</div>
            <div class="text-h5 text-weight-bold">${{ store.balance.toFixed(2) }}</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-sm-6 col-md-3">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-caption text-grey">PnL Hoy</div>
            <div class="text-h5 text-weight-bold" :class="store.dailyPnl >= 0 ? 'text-green' : 'text-red'">
              {{ store.dailyPnl >= 0 ? '+' : '' }}${{ store.dailyPnl.toFixed(2) }}
            </div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-sm-6 col-md-3">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-caption text-grey">Posiciones Abiertas</div>
            <div class="text-h5 text-weight-bold">{{ store.openPositions }}</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-sm-6 col-md-3">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-caption text-grey">Estado</div>
            <q-badge :color="store.killSwitch ? 'red' : 'green'" class="text-body1 q-pa-sm">
              {{ store.killSwitch ? '⏸ PAUSED' : '▶ ACTIVE' }}
            </q-badge>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Target Progress -->
    <q-card flat bordered class="q-mb-lg">
      <q-card-section>
        <div class="row items-center justify-between">
          <div class="text-subtitle1 text-weight-medium">Target Diario (1%)</div>
          <div class="text-caption text-grey">{{ targetPct.toFixed(1) }}%</div>
        </div>
        <q-linear-progress
          :value="targetPct / 100"
          :color="targetPct >= 100 ? 'green' : 'primary'"
          size="12px"
          rounded
          class="q-mt-sm"
        />
      </q-card-section>
    </q-card>

    <!-- Open Positions -->
    <q-card flat bordered class="q-mb-lg">
      <q-card-section class="q-pb-none">
        <div class="text-subtitle1 text-weight-medium">Posiciones Abiertas</div>
      </q-card-section>
      <q-card-section>
        <q-table
          v-if="store.openTrades.length > 0"
          :rows="store.openTrades"
          :columns="openColumns"
          row-key="id"
          flat
          dense
          hide-pagination
          :pagination="{ rowsPerPage: 0 }"
        />
        <div v-else class="text-grey text-center q-py-md">
          No hay posiciones abiertas
        </div>
      </q-card-section>
    </q-card>

    <!-- Today Stats -->
    <div class="row q-col-gutter-md">
      <div class="col-12 col-md-6">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle1 text-weight-medium q-mb-md">Hoy</div>
            <div class="row q-col-gutter-sm">
              <div class="col-4 text-center">
                <div class="text-h6">{{ store.dailySummary?.tradesTotal || 0 }}</div>
                <div class="text-caption text-grey">Trades</div>
              </div>
              <div class="col-4 text-center">
                <div class="text-h6 text-green">{{ store.dailySummary?.tradesWon || 0 }}</div>
                <div class="text-caption text-grey">Wins</div>
              </div>
              <div class="col-4 text-center">
                <div class="text-h6 text-red">{{ store.dailySummary?.tradesLost || 0 }}</div>
                <div class="text-caption text-grey">Losses</div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-md-6">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle1 text-weight-medium q-mb-md">Performance (30d)</div>
            <div class="row q-col-gutter-sm">
              <div class="col-4 text-center">
                <div class="text-h6">{{ store.stats?.winRate || 0 }}%</div>
                <div class="text-caption text-grey">Win Rate</div>
              </div>
              <div class="col-4 text-center">
                <div class="text-h6">{{ store.stats?.profitFactor || 0 }}</div>
                <div class="text-caption text-grey">Profit Factor</div>
              </div>
              <div class="col-4 text-center">
                <div class="text-h6">${{ store.stats?.totalPnl?.toFixed(2) || '0' }}</div>
                <div class="text-caption text-grey">Total PnL</div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useTradingStore } from '@/stores/trading'

const store = useTradingStore()

const targetPct = computed(() => {
  if (!store.dailySummary) return 0
  const target = store.balance * 0.01
  return target > 0 ? (store.dailyPnl / target) * 100 : 0
})

const openColumns = [
  { name: 'symbol', label: 'Par', field: 'symbol', align: 'left' as const },
  { name: 'side', label: 'Side', field: 'side', align: 'center' as const },
  { name: 'lot_size', label: 'Lots', field: 'lot_size', align: 'center' as const },
  { name: 'entry_price', label: 'Entry', field: 'entry_price', align: 'right' as const },
  { name: 'pnl_usd', label: 'PnL', field: 'pnl_usd', align: 'right' as const, format: (v: number) => v ? `$${v.toFixed(2)}` : '-' },
]

onMounted(async () => {
  await store.loadDashboard()
  await store.loadStats()
})
</script>
