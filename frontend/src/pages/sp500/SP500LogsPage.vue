<template>
  <q-page padding>
    <div class="row items-center q-mb-lg">
      <q-icon name="terminal" size="sm" color="primary" class="q-mr-sm" />
      <div class="text-h6 text-weight-bold">SP500 Agent Logs</div>
      <q-space />
      <q-input v-model="selectedDate" outlined dense type="date" style="max-width: 180px" @update:model-value="loadLogs" />
    </div>

    <!-- Summary Bar -->
    <div class="row q-col-gutter-sm q-mb-md" v-if="meta">
      <div class="col-auto">
        <q-chip outline color="positive" size="sm">Wins: {{ meta.totals.wins }}</q-chip>
      </div>
      <div class="col-auto">
        <q-chip outline color="negative" size="sm">Losses: {{ meta.totals.losses }}</q-chip>
      </div>
      <div class="col-auto">
        <q-chip outline :color="meta.totals.realizedPnl >= 0 ? 'positive' : 'negative'" size="sm">
          PnL: ${{ meta.totals.realizedPnl.toFixed(2) }}
        </q-chip>
      </div>
    </div>

    <!-- Logs Timeline -->
    <q-timeline color="primary" v-if="sp500Store.logs.length > 0">
      <q-timeline-entry
        v-for="log in sp500Store.logs"
        :key="log.id"
        :subtitle="formatTime(log.timestamp)"
        :icon="log.tradesOpened > 0 ? 'trending_up' : log.tradesClosed > 0 ? 'check_circle' : 'visibility'"
        :color="log.tradesOpened > 0 ? 'positive' : log.tradesClosed > 0 ? 'amber' : 'grey-6'"
      >
        <div class="text-body2 text-grey-3" style="white-space: pre-wrap">{{ log.decision }}</div>
        <div class="row q-gutter-xs q-mt-xs" v-if="log.tradesOpened > 0 || log.tradesClosed > 0">
          <q-badge v-if="log.tradesOpened > 0" color="positive" :label="`+${log.tradesOpened} opened`" />
          <q-badge v-if="log.tradesClosed > 0" color="amber" text-color="dark" :label="`${log.tradesClosed} closed`" />
          <q-badge v-if="log.floatingPnl !== 0" :color="log.floatingPnl >= 0 ? 'positive' : 'negative'" :label="`Float: $${log.floatingPnl.toFixed(2)}`" />
        </div>
      </q-timeline-entry>
    </q-timeline>

    <div v-else class="text-center text-grey-5 q-pa-xl">
      <q-icon name="inbox" size="xl" />
      <div class="q-mt-md">No hay logs para esta fecha</div>
    </div>

    <!-- Pagination -->
    <div class="row justify-center q-mt-md" v-if="meta && meta.totalPages > 1">
      <q-pagination v-model="page" :max="meta.totalPages" direction-links boundary-links @update:model-value="loadLogs" />
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useSP500Store } from '@/stores/sp500'

const sp500Store = useSP500Store()
const selectedDate = ref(new Date().toISOString().slice(0, 10))
const page = ref(1)
const meta = ref<{ total: number; page: number; totalPages: number; totals: { wins: number; losses: number; realizedPnl: number } } | null>(null)

function formatTime(ts: string) {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

async function loadLogs() {
  meta.value = await sp500Store.loadLogs(selectedDate.value, page.value, 25)
}

onMounted(() => void loadLogs())
</script>
