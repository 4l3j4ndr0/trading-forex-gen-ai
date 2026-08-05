<template>
  <q-page class="q-pa-lg">
    <!-- Header -->
    <div class="row items-center justify-between q-mb-lg">
      <div>
        <div class="text-h5 text-weight-bold text-white">SP500 Agent Logs</div>
        <div class="text-caption text-grey-5">Decisiones del agente SP500 (Wyckoff)</div>
      </div>
      <div class="row items-center q-gutter-sm">
        <q-input
          v-model="dateFilter"
          dense
          outlined
          dark
          readonly
          class="premium-card"
          style="width: 160px"
          placeholder="Fecha"
        >
          <template #prepend>
            <q-icon name="event" size="xs" color="grey-5" class="cursor-pointer">
              <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                <q-date
                  v-model="dateFilter"
                  mask="YYYY-MM-DD"
                  dark
                  flat
                  @update:model-value="onFilterChange"
                />
              </q-popup-proxy>
            </q-icon>
          </template>
        </q-input>

        <q-btn-toggle
          v-model="quickDate"
          toggle-color="primary"
          text-color="grey-5"
          :options="[
            { label: 'Hoy', value: 'today' },
            { label: 'Ayer', value: 'yesterday' },
            { label: 'Todo', value: 'all' },
          ]"
          dense
          flat
          no-caps
          class="premium-card"
          @update:model-value="onQuickDateChange"
        />
      </div>
    </div>

    <!-- Summary bar -->
    <q-card v-if="meta" flat class="premium-card q-pa-sm q-mb-lg">
      <div class="row items-center justify-around text-center">
        <div>
          <div class="text-white text-weight-bold number-display">{{ meta.totals.wins }}</div>
          <div class="text-caption text-grey-5">Wins</div>
        </div>
        <q-separator vertical dark />
        <div>
          <div class="text-white text-weight-bold number-display">{{ meta.totals.losses }}</div>
          <div class="text-caption text-grey-5">Losses</div>
        </div>
        <q-separator vertical dark />
        <div>
          <div
            class="text-weight-bold number-display"
            :class="meta.totals.realizedPnl >= 0 ? 'text-positive' : 'text-negative'"
          >
            {{ meta.totals.realizedPnl >= 0 ? '+' : '' }}${{ meta.totals.realizedPnl.toFixed(2) }}
          </div>
          <div class="text-caption text-grey-5">PnL Realizado</div>
        </div>
        <q-separator vertical dark />
        <div>
          <div class="text-white text-weight-bold number-display">{{ meta.total }}</div>
          <div class="text-caption text-grey-5">Ciclos</div>
        </div>
      </div>
    </q-card>

    <!-- Loading -->
    <div v-if="loading" class="text-center q-py-xl">
      <q-spinner-dots size="40px" color="primary" />
    </div>

    <!-- Empty State -->
    <div v-if="!loading && sp500Store.logs.length === 0" class="text-center q-py-xl">
      <q-icon name="smart_toy" size="64px" color="grey-7" />
      <div class="text-grey-5 q-mt-md text-subtitle1">No hay logs para esta fecha</div>
      <div class="text-caption text-grey-6">El agente opera en AM (09:30-11:30 ET) y PM (14:00-16:00 ET) Killzones</div>
    </div>

    <!-- Timeline -->
    <q-timeline v-if="!loading && sp500Store.logs.length > 0" color="primary" dark>
      <q-timeline-entry
        v-for="log in sp500Store.logs"
        :key="log.id"
        :subtitle="formatTime(log.timestamp)"
        :icon="logIcon(log)"
        :color="logColor(log)"
      >
        <template #title>
          <div class="row items-center q-gutter-sm">
            <q-chip
              v-if="log.tradesOpened > 0"
              size="sm"
              dense
              class="chip-side-buy"
            >
              +{{ log.tradesOpened }} opened
            </q-chip>
            <q-chip
              v-if="log.tradesClosed > 0"
              size="sm"
              dense
              color="blue-8"
              text-color="white"
            >
              {{ log.tradesClosed }} closed
            </q-chip>
            <span
              v-if="log.floatingPnl !== 0"
              class="text-weight-bold number-display q-ml-sm"
              :class="log.floatingPnl >= 0 ? 'text-positive' : 'text-negative'"
            >
              Float: {{ log.floatingPnl >= 0 ? '+' : '' }}${{ log.floatingPnl.toFixed(2) }}
            </span>
          </div>
        </template>

        <div class="text-body2 text-grey-4 q-mt-sm" style="white-space: pre-wrap">
          {{ log.decision }}
        </div>
      </q-timeline-entry>
    </q-timeline>

    <!-- Pagination -->
    <div v-if="meta && meta.totalPages > 1" class="row justify-center q-mt-lg">
      <q-pagination
        v-model="currentPage"
        :max="meta.totalPages"
        direction-links
        boundary-links
        color="primary"
        active-color="primary"
        dark
        @update:model-value="onPageChange"
      />
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useSP500Store } from '@/stores/sp500'

const sp500Store = useSP500Store()
const dateFilter = ref(new Date().toISOString().split('T')[0])
const quickDate = ref('today')
const currentPage = ref(1)
const loading = ref(false)
const meta = ref<{
  total: number
  page: number
  totalPages: number
  totals: { wins: number; losses: number; realizedPnl: number }
} | null>(null)

function formatTime(ts: string) {
  const d = new Date(ts)
  const utc = `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`
  // Calculate ET (UTC-4 in summer, UTC-5 in winter)
  const et = new Date(d.getTime() - 4 * 3600000)
  const etStr = `${String(et.getUTCHours()).padStart(2, '0')}:${String(et.getUTCMinutes()).padStart(2, '0')}`
  return `${utc} UTC (${etStr} ET)`
}

function logIcon(log: { tradesOpened: number; tradesClosed: number }) {
  if (log.tradesOpened > 0) return 'trending_up'
  if (log.tradesClosed > 0) return 'check_circle'
  return 'remove_circle_outline'
}

function logColor(log: { tradesOpened: number; tradesClosed: number; floatingPnl: number }) {
  if (log.tradesOpened > 0) return 'positive'
  if (log.tradesClosed > 0) return 'amber'
  if (log.floatingPnl < 0) return 'negative'
  return 'grey-7'
}

function onQuickDateChange(value: string) {
  const today = new Date()
  if (value === 'today') {
    dateFilter.value = today.toISOString().split('T')[0]
  } else if (value === 'yesterday') {
    today.setDate(today.getDate() - 1)
    dateFilter.value = today.toISOString().split('T')[0]
  } else {
    dateFilter.value = ''
  }
  currentPage.value = 1
  void loadLogs()
}

function onFilterChange() {
  quickDate.value = ''
  currentPage.value = 1
  void loadLogs()
}

function onPageChange() {
  void loadLogs()
}

async function loadLogs() {
  loading.value = true
  try {
    const result = await sp500Store.loadLogs(dateFilter.value || undefined, currentPage.value, 25)
    if (result) {
      meta.value = result
    }
  } catch {
    // silent
  } finally {
    loading.value = false
  }
}

onMounted(loadLogs)
</script>
