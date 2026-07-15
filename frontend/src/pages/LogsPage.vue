<template>
  <q-page class="q-pa-lg">
    <!-- Header -->
    <div class="row items-center justify-between q-mb-lg">
      <div>
        <div class="text-h5 text-weight-bold text-white">Agent Logs</div>
        <div class="text-caption text-grey-5">Decisiones del agente cada 15 minutos</div>
      </div>
      <q-input
        v-model="dateFilter"
        type="date"
        dense
        outlined
        dark
        class="premium-card"
        style="width: 160px"
        @update:model-value="loadLogs"
      />
    </div>

    <!-- Empty State -->
    <div v-if="store.hourlyLogs.length === 0" class="text-center q-py-xl">
      <q-icon name="smart_toy" size="64px" color="grey-7" />
      <div class="text-grey-5 q-mt-md text-subtitle1">No hay logs para esta fecha</div>
      <div class="text-caption text-grey-6">El agente registra decisiones entre 06:00 y 21:00 UTC</div>
    </div>

    <!-- Timeline -->
    <q-timeline v-else color="primary" dark>
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
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useTradingStore } from '@/stores/trading'

const store = useTradingStore()
const dateFilter = ref(new Date().toISOString().split('T')[0])

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

async function loadLogs() {
  await store.loadLogs(dateFilter.value)
}

onMounted(loadLogs)
</script>
