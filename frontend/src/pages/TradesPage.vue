<template>
  <q-page class="q-pa-lg">
    <!-- Header -->
    <div class="row items-center justify-between q-mb-lg">
      <div>
        <div class="text-h5 text-weight-bold text-white">Historial de Trades</div>
        <div class="text-caption text-grey-5">Registro de todas las operaciones ejecutadas por el agente</div>
      </div>
      <q-btn-toggle
        v-model="period"
        toggle-color="primary"
        text-color="grey-5"
        :options="[
          { label: 'Hoy', value: 'today' },
          { label: '7d', value: '7d' },
          { label: '30d', value: '30d' },
          { label: 'Todo', value: 'all' },
        ]"
        dense
        flat
        no-caps
        class="premium-card"
      />
    </div>

    <!-- Table -->
    <q-card flat class="premium-card">
      <q-table
        flat
        dark
        class="bg-transparent"
        :rows="store.tradeHistory"
        :columns="columns"
        row-key="id"
        :loading="loading"
        :pagination="pagination"
        @request="onRequest"
      >
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
            :class="(props.value || 0) >= 0 ? 'text-positive' : 'text-negative'"
          >
            {{ props.value ? (props.value > 0 ? '+' : '') + '$' + Number(props.value).toFixed(2) : '-' }}
          </q-td>
        </template>

        <template #body-cell-close_reason="props">
          <q-td :props="props">
            <q-chip
              dense
              size="sm"
              :color="reasonColor(props.value)"
              text-color="white"
              class="text-weight-medium"
            >
              {{ reasonLabel(props.value) }}
            </q-chip>
          </q-td>
        </template>

        <template #body-cell-holding_minutes="props">
          <q-td :props="props" class="text-grey-4 number-display">
            {{ formatDuration(props.value) }}
          </q-td>
        </template>

        <template #no-data>
          <div class="full-width text-center q-py-xl">
            <q-icon name="history" size="48px" color="grey-7" />
            <div class="text-grey-5 q-mt-sm">No hay trades en este período</div>
          </div>
        </template>
      </q-table>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useTradingStore } from '@/stores/trading'

const store = useTradingStore()
const period = ref('today')
const loading = ref(false)
const pagination = ref({ page: 1, rowsPerPage: 20, rowsNumber: 0 })

const columns = [
  {
    name: 'opened_at',
    label: 'Fecha',
    field: 'opened_at',
    align: 'left' as const,
    format: (v: string) => new Date(v).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' }),
    classes: 'text-grey-4',
  },
  { name: 'symbol', label: 'Par', field: 'symbol', align: 'left' as const, sortable: true },
  { name: 'side', label: 'Side', field: 'side', align: 'center' as const },
  { name: 'lot_size', label: 'Lotes', field: 'lot_size', align: 'center' as const, classes: 'number-display' },
  { name: 'entry_price', label: 'Entry', field: 'entry_price', align: 'right' as const, classes: 'text-grey-4 number-display' },
  { name: 'exit_price', label: 'Exit', field: 'exit_price', align: 'right' as const, format: (v: number) => v || '-', classes: 'number-display' },
  { name: 'pnl_usd', label: 'PnL', field: 'pnl_usd', align: 'right' as const },
  { name: 'holding_minutes', label: 'Duración', field: (row: Record<string, unknown>) => {
    if (row.holding_minutes) return row.holding_minutes as number
    if (row.opened_at && row.closed_at) {
      return (new Date(row.closed_at as string).getTime() - new Date(row.opened_at as string).getTime()) / 60000
    }
    if (row.opened_at && row.status === 'open') {
      return (Date.now() - new Date(row.opened_at as string).getTime()) / 60000
    }
    return null
  }, align: 'right' as const },
  { name: 'close_reason', label: 'Razón', field: 'close_reason', align: 'center' as const },
]

function reasonColor(reason: string | null) {
  if (!reason) return 'grey-8'
  if (reason === 'tp_hit') return 'positive'
  if (reason === 'sl_hit') return 'negative'
  if (reason === 'manual') return 'info'
  if (reason === 'expired') return 'warning'
  return 'grey-7'
}

function reasonLabel(reason: string | null) {
  if (!reason) return 'OPEN'
  const labels: Record<string, string> = {
    tp_hit: 'TP',
    sl_hit: 'SL',
    manual: 'Manual',
    expired: 'Expired',
    breakeven: 'BE',
  }
  return labels[reason] || reason.toUpperCase()
}

function formatDuration(minutes: number | null) {
  if (!minutes) return '-'
  if (minutes < 60) return `${Math.round(minutes)}m`
  const h = Math.floor(minutes / 60)
  const m = Math.round(minutes % 60)
  return m > 0 ? `${h}h ${m}m` : `${h}h`
}

async function loadTrades() {
  loading.value = true
  await store.loadTrades({
    period: period.value,
    page: pagination.value.page,
    limit: pagination.value.rowsPerPage,
  })
  loading.value = false
}

function onRequest(props: { pagination: { page: number; rowsPerPage: number } }) {
  pagination.value.page = props.pagination.page
  pagination.value.rowsPerPage = props.pagination.rowsPerPage
  void loadTrades()
}

watch(period, () => {
  pagination.value.page = 1
  void loadTrades()
})

onMounted(() => void loadTrades())
</script>
