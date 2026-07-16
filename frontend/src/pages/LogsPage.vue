<template>
  <q-page class="q-pa-lg">
    <!-- Header -->
    <div class="row items-center justify-between q-mb-lg">
      <div>
        <div class="text-h5 text-weight-bold text-white">Agent Logs</div>
        <div class="text-caption text-grey-5">Decisiones del agente cada 15 minutos</div>
      </div>
      <div class="row items-center q-gutter-sm">
        <!-- Date filter with Quasar native -->
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

        <!-- Quick date buttons -->
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
    <q-card v-if="store.hourlyLogs.length > 0" flat class="premium-card q-pa-sm q-mb-lg">
      <div class="row items-center justify-around text-center">
        <div>
          <div class="text-white text-weight-bold number-display">{{ totalOpened }}</div>
          <div class="text-caption text-grey-5">Trades Abiertos</div>
        </div>
        <q-separator vertical dark />
        <div>
          <div class="text-white text-weight-bold number-display">{{ totalClosed }}</div>
          <div class="text-caption text-grey-5">Trades Cerrados</div>
        </div>
        <q-separator vertical dark />
        <div>
          <div
            class="text-weight-bold number-display"
            :class="totalPnl >= 0 ? 'text-positive' : 'text-negative'"
          >
            {{ totalPnl >= 0 ? '+' : '' }}${{ totalPnl.toFixed(2) }}
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

    <!-- Empty State -->
    <div v-if="!loading && store.hourlyLogs.length === 0" class="text-center q-py-xl">
      <q-icon name="smart_toy" size="64px" color="grey-7" />
      <div class="text-grey-5 q-mt-md text-subtitle1">No hay logs para esta fecha</div>
      <div class="text-caption text-grey-6">El agente registra decisiones entre 06:00 y 21:00 UTC</div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center q-py-xl">
      <q-spinner-dots size="40px" color="primary" />
    </div>

    <!-- Timeline -->
    <q-timeline v-if="!loading && store.hourlyLogs.length > 0" color="primary" dark>
      <q-timeline-entry
        v-for="log in store.hourlyLogs"
        :key="log.id"
        :subtitle="`${formatTime(log.timestamp)} UTC — ${sessionLabel(log.session)}`"
        :icon="logIcon(log)"
        :color="logColor(log)"
      >
        <template #title>
          <div class="row items-center q-gutter-sm">
            <q-chip
              v-if="log.trades_opened > 0"
              size="sm"
              dense
              class="chip-side-buy"
            >
              +{{ log.trades_opened }} opened
            </q-chip>
            <q-chip
              v-if="log.trades_closed > 0"
              size="sm"
              dense
              color="blue-8"
              text-color="white"
            >
              {{ log.trades_closed }} closed
            </q-chip>
            <q-chip
              v-if="log.trades_skipped > 0"
              size="sm"
              dense
              color="grey-8"
              text-color="grey-4"
            >
              {{ log.trades_skipped }} skipped
            </q-chip>
            <span
              v-if="log.pnl_this_hour"
              class="text-weight-bold number-display q-ml-sm"
              :class="log.pnl_this_hour >= 0 ? 'text-positive' : 'text-negative'"
            >
              {{ log.pnl_this_hour >= 0 ? '+' : '' }}${{ Number(log.pnl_this_hour).toFixed(2) }}
            </span>
          </div>
        </template>

        <div v-if="log.decision_summary" class="text-body2 text-grey-4 q-mt-sm">
          {{ log.decision_summary }}
        </div>
        <div v-if="log.market_context" class="text-caption text-grey-6 q-mt-xs" style="font-style: italic">
          {{ log.market_context }}
        </div>
      </q-timeline-entry>
    </q-timeline>

    <!-- Pagination -->
    <div v-if="meta.totalPages > 1" class="row justify-center q-mt-lg">
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
import { ref, computed, onMounted } from 'vue'
import { useTradingStore } from '@/stores/trading'

const store = useTradingStore()
const dateFilter = ref(new Date().toISOString().split('T')[0])
const quickDate = ref('today')
const currentPage = ref(1)
const loading = ref(false)
const meta = ref({ total: 0, page: 1, totalPages: 1, totals: { opened: 0, closed: 0, realizedPnl: 0 } })

const totalOpened = computed(() => meta.value.totals.opened)
const totalClosed = computed(() => meta.value.totals.closed)
const totalPnl = computed(() => meta.value.totals.realizedPnl)

function formatTime(timestamp: string) {
  const d = new Date(timestamp)
  return `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`
}

function sessionLabel(session: string | null) {
  if (!session) return 'off-hours'
  const labels: Record<string, string> = {
    london: '🇬🇧 London',
    new_york: '🇺🇸 New York',
    tokyo: '🇯🇵 Tokyo',
    overlap: '🔥 Overlap',
  }
  return labels[session] || session
}

function logIcon(log: { trades_opened: number; trades_closed: number }) {
  if (log.trades_opened > 0) return 'trending_up'
  if (log.trades_closed > 0) return 'check_circle'
  return 'remove_circle_outline'
}

function logColor(log: { trades_opened: number; pnl_this_hour: number | null }) {
  if (log.trades_opened > 0) return 'positive'
  if (log.pnl_this_hour && log.pnl_this_hour < 0) return 'negative'
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
    const result = await store.loadLogs(dateFilter.value || undefined, currentPage.value, 25)
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
