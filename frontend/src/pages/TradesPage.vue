<template>
  <q-page padding>
    <div class="row items-center justify-between q-mb-md">
      <div class="text-h6 text-weight-bold">Historial de Trades</div>
      <div class="row q-gutter-sm">
        <q-btn-toggle
          v-model="period"
          toggle-color="primary"
          :options="[
            { label: 'Hoy', value: 'today' },
            { label: '7d', value: '7d' },
            { label: '30d', value: '30d' },
          ]"
          dense
          flat
        />
      </div>
    </div>

    <q-card flat bordered>
      <q-table
        :rows="store.tradeHistory"
        :columns="columns"
        row-key="id"
        flat
        dense
        :loading="loading"
        :pagination="pagination"
        @request="onRequest"
      >
        <template #body-cell-side="props">
          <q-td :props="props">
            <q-badge :color="props.value === 'BUY' ? 'green' : 'red'">
              {{ props.value }}
            </q-badge>
          </q-td>
        </template>
        <template #body-cell-pnl_usd="props">
          <q-td :props="props">
            <span :class="(props.value || 0) >= 0 ? 'text-green' : 'text-red'" class="text-weight-medium">
              {{ props.value ? `$${Number(props.value).toFixed(2)}` : '-' }}
            </span>
          </q-td>
        </template>
        <template #body-cell-close_reason="props">
          <q-td :props="props">
            <q-chip dense size="sm" :color="reasonColor(props.value)" text-color="white">
              {{ props.value || 'open' }}
            </q-chip>
          </q-td>
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
  { name: 'opened_at', label: 'Fecha', field: 'opened_at', align: 'left' as const, format: (v: string) => new Date(v).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' }) },
  { name: 'symbol', label: 'Par', field: (row: Record<string, unknown>) => row.pair_id, align: 'left' as const },
  { name: 'side', label: 'Side', field: 'side', align: 'center' as const },
  { name: 'lot_size', label: 'Lots', field: 'lot_size', align: 'center' as const },
  { name: 'entry_price', label: 'Entry', field: 'entry_price', align: 'right' as const },
  { name: 'exit_price', label: 'Exit', field: 'exit_price', align: 'right' as const, format: (v: number) => v || '-' },
  { name: 'pnl_usd', label: 'PnL', field: 'pnl_usd', align: 'right' as const },
  { name: 'holding_minutes', label: 'Duración', field: 'holding_minutes', align: 'right' as const, format: (v: number) => v ? `${Math.round(v)}m` : '-' },
  { name: 'close_reason', label: 'Razón', field: 'close_reason', align: 'center' as const },
]

function reasonColor(reason: string | null) {
  if (!reason) return 'grey'
  if (reason === 'tp_hit') return 'green'
  if (reason === 'sl_hit') return 'red'
  if (reason === 'expired') return 'orange'
  return 'blue'
}

async function loadTrades() {
  loading.value = true
  await store.loadTrades({ period: period.value, page: pagination.value.page, limit: pagination.value.rowsPerPage })
  loading.value = false
}

function onRequest(props: { pagination: { page: number; rowsPerPage: number; rowsNumber?: number } }) {
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
