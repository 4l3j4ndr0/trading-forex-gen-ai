<template>
  <q-page padding>
    <div class="row items-center q-mb-lg">
      <q-icon name="receipt_long" size="sm" color="primary" class="q-mr-sm" />
      <div class="text-h6 text-weight-bold">SP500 Trades</div>
    </div>

    <q-table
      :rows="sp500Store.tradeHistory"
      :columns="columns"
      row-key="id"
      flat
      dark
      dense
      :loading="loading"
      :pagination="pagination"
      @request="onRequest"
    >
      <template #body-cell-side="props">
        <q-td :props="props">
          <q-badge :color="props.value === 'BUY' ? 'positive' : 'negative'" :label="props.value" />
        </q-td>
      </template>
      <template #body-cell-pnlUsd="props">
        <q-td :props="props">
          <span :class="(props.value ?? 0) >= 0 ? 'text-positive' : 'text-negative'" class="text-weight-bold">
            {{ props.value != null ? `$${props.value.toFixed(2)}` : '-' }}
          </span>
        </q-td>
      </template>
      <template #body-cell-closeReason="props">
        <q-td :props="props">
          <q-badge
            v-if="props.value"
            :color="props.value === 'tp_hit' ? 'positive' : props.value === 'sl_hit' ? 'negative' : 'grey'"
            :label="props.value"
            outline
          />
          <span v-else class="text-grey-5">-</span>
        </q-td>
      </template>
      <template #body-cell-duration="props">
        <q-td :props="props">
          {{ formatDuration(props.row) }}
        </q-td>
      </template>
    </q-table>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useSP500Store } from '@/stores/sp500'

const sp500Store = useSP500Store()
const loading = ref(false)
const pagination = ref({ page: 1, rowsPerPage: 25, rowsNumber: 0 })

const columns = [
  { name: 'ticket', label: 'Ticket', field: 'ticket', align: 'left' as const },
  { name: 'side', label: 'Side', field: 'side', align: 'center' as const },
  { name: 'lotSize', label: 'Lots', field: 'lotSize', align: 'center' as const },
  { name: 'entryPrice', label: 'Entry', field: 'entryPrice', align: 'right' as const, format: (v: number) => v.toFixed(2) },
  { name: 'exitPrice', label: 'Exit', field: 'exitPrice', align: 'right' as const, format: (v: number | null) => v?.toFixed(2) ?? '-' },
  { name: 'pnlUsd', label: 'PnL USD', field: 'pnlUsd', align: 'right' as const },
  { name: 'pnlPoints', label: 'Points', field: 'pnlPoints', align: 'right' as const, format: (v: number | null) => v?.toFixed(1) ?? '-' },
  { name: 'closeReason', label: 'Reason', field: 'closeReason', align: 'center' as const },
  { name: 'duration', label: 'Duration', field: 'holdingMinutes', align: 'right' as const },
  { name: 'openedAt', label: 'Date', field: 'openedAt', align: 'right' as const, format: (v: string) => new Date(v).toLocaleDateString() },
]

function formatDuration(row: { holdingMinutes: number | null; openedAt: string; closedAt: string | null }) {
  let mins = row.holdingMinutes
  if (!mins && row.openedAt && row.closedAt) {
    mins = Math.round((new Date(row.closedAt).getTime() - new Date(row.openedAt).getTime()) / 60000)
  }
  if (!mins) return '-'
  if (mins < 60) return `${mins}m`
  return `${Math.floor(mins / 60)}h ${mins % 60}m`
}

async function onRequest(props: { pagination: { page: number; rowsPerPage: number } }) {
  loading.value = true
  const res = await sp500Store.loadTrades({ page: props.pagination.page, limit: props.pagination.rowsPerPage })
  pagination.value.page = res.meta.page
  pagination.value.rowsNumber = res.meta.total
  loading.value = false
}

onMounted(async () => {
  loading.value = true
  const res = await sp500Store.loadTrades({ page: 1, limit: 25 })
  pagination.value.rowsNumber = res.meta.total
  loading.value = false
})
</script>
