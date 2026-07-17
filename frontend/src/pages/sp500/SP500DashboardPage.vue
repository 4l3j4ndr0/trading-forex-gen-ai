<template>
  <q-page padding>
    <div class="row items-center q-mb-lg">
      <q-icon name="show_chart" size="sm" color="primary" class="q-mr-sm" />
      <div class="text-h6 text-weight-bold">SP500 Dashboard</div>
      <q-space />
      <q-badge :color="sp500Store.settings?.autoTradingEnabled ? 'positive' : 'grey'" class="q-pa-sm">
        {{ sp500Store.settings?.autoTradingEnabled ? 'AUTO TRADING ON' : 'PAUSED' }}
      </q-badge>
    </div>

    <!-- KPI Cards -->
    <div class="row q-col-gutter-md q-mb-lg">
      <div class="col-6 col-md-3">
        <q-card flat class="premium-card q-pa-md">
          <div class="label-mini text-grey-5">Total Trades</div>
          <div class="text-h5 text-weight-bold text-white number-display">
            {{ sp500Store.stats?.totalTrades ?? 0 }}
          </div>
        </q-card>
      </div>
      <div class="col-6 col-md-3">
        <q-card flat class="premium-card q-pa-md">
          <div class="label-mini text-grey-5">Win Rate</div>
          <div class="text-h5 text-weight-bold number-display" :class="(sp500Store.stats?.winRate ?? 0) >= 50 ? 'text-positive' : 'text-negative'">
            {{ sp500Store.stats?.winRate ?? 0 }}%
          </div>
        </q-card>
      </div>
      <div class="col-6 col-md-3">
        <q-card flat class="premium-card q-pa-md">
          <div class="label-mini text-grey-5">Total PnL</div>
          <div class="text-h5 text-weight-bold number-display" :class="(sp500Store.stats?.totalPnl ?? 0) >= 0 ? 'text-positive' : 'text-negative'">
            ${{ (sp500Store.stats?.totalPnl ?? 0).toFixed(2) }}
          </div>
        </q-card>
      </div>
      <div class="col-6 col-md-3">
        <q-card flat class="premium-card q-pa-md">
          <div class="label-mini text-grey-5">Open Positions</div>
          <div class="text-h5 text-weight-bold text-white number-display">
            {{ sp500Store.openPositions }}
          </div>
        </q-card>
      </div>
    </div>

    <!-- Session Info -->
    <div class="row q-col-gutter-md q-mb-lg">
      <div class="col-12 col-md-6">
        <q-card flat class="premium-card q-pa-md">
          <div class="text-subtitle2 text-weight-bold text-white q-mb-sm">
            <q-icon name="schedule" class="q-mr-xs" /> Killzones (UTC)
          </div>
          <div class="row q-gutter-sm">
            <q-chip outline color="amber" size="sm">
              AM: {{ sp500Store.settings?.amKillzoneStart ?? '13:30' }} - {{ sp500Store.settings?.amKillzoneEnd ?? '15:30' }}
            </q-chip>
            <q-chip outline color="orange" size="sm">
              PM: {{ sp500Store.settings?.pmKillzoneStart ?? '18:00' }} - {{ sp500Store.settings?.pmKillzoneEnd ?? '20:00' }}
            </q-chip>
          </div>
          <div class="text-caption text-grey-5 q-mt-sm">
            Symbol: {{ sp500Store.settings?.symbol ?? 'US500Cash' }} | Point Value: ${{ sp500Store.settings?.pointValue ?? 1 }}/pt/lot
          </div>
        </q-card>
      </div>
      <div class="col-12 col-md-6">
        <q-card flat class="premium-card q-pa-md">
          <div class="text-subtitle2 text-weight-bold text-white q-mb-sm">
            <q-icon name="shield" class="q-mr-xs" /> Risk Config
          </div>
          <div class="row q-col-gutter-sm">
            <div class="col-6">
              <div class="label-mini text-grey-5">Risk/Trade</div>
              <div class="text-white">{{ sp500Store.settings?.maxRiskPerTradePct ?? 1 }}%</div>
            </div>
            <div class="col-6">
              <div class="label-mini text-grey-5">Max Daily Loss</div>
              <div class="text-white">{{ sp500Store.settings?.maxDailyLossPct ?? 5 }}%</div>
            </div>
            <div class="col-6">
              <div class="label-mini text-grey-5">Lot Range</div>
              <div class="text-white">{{ sp500Store.settings?.minLot ?? 0.01 }} - {{ sp500Store.settings?.maxLot ?? 5 }}</div>
            </div>
            <div class="col-6">
              <div class="label-mini text-grey-5">Min R:R</div>
              <div class="text-white">{{ sp500Store.settings?.minRrRatio ?? 1.5 }}:1</div>
            </div>
          </div>
        </q-card>
      </div>
    </div>

    <!-- Open Positions Table -->
    <q-card flat class="premium-card q-pa-md" v-if="sp500Store.openTrades.length > 0">
      <div class="text-subtitle2 text-weight-bold text-white q-mb-md">
        <q-icon name="pending" class="q-mr-xs" /> Open Positions
      </div>
      <q-table
        :rows="sp500Store.openTrades"
        :columns="openColumns"
        row-key="ticket"
        flat
        dark
        dense
        :pagination="{ rowsPerPage: 10 }"
      />
    </q-card>

    <!-- Empty state -->
    <q-card flat class="premium-card q-pa-lg text-center" v-if="!sp500Store.loading && sp500Store.openPositions === 0 && (sp500Store.stats?.totalTrades ?? 0) === 0">
      <q-icon name="show_chart" size="xl" color="grey-6" />
      <div class="text-grey-5 q-mt-md">No hay trades de SP500 todavia. El agente operara durante las killzones de NY.</div>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useSP500Store } from '@/stores/sp500'

const sp500Store = useSP500Store()

const openColumns = [
  { name: 'ticket', label: 'Ticket', field: 'ticket', align: 'left' as const },
  { name: 'side', label: 'Side', field: 'side', align: 'center' as const },
  { name: 'lotSize', label: 'Lots', field: 'lotSize', align: 'center' as const },
  { name: 'entryPrice', label: 'Entry', field: 'entryPrice', align: 'right' as const, format: (v: number) => v.toFixed(2) },
  { name: 'slPrice', label: 'SL', field: 'slPrice', align: 'right' as const, format: (v: number | null) => v?.toFixed(2) ?? '-' },
  { name: 'tpPrice', label: 'TP', field: 'tpPrice', align: 'right' as const, format: (v: number | null) => v?.toFixed(2) ?? '-' },
  { name: 'openedAt', label: 'Opened', field: 'openedAt', align: 'right' as const, format: (v: string) => new Date(v).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) },
]

onMounted(() => {
  void sp500Store.loadDashboard()
})
</script>
