<template>
  <q-page padding>
    <div class="row items-center justify-between q-mb-md">
      <div class="text-h6 text-weight-bold">Agent Logs</div>
      <q-input v-model="dateFilter" type="date" dense outlined class="col-auto" @update:model-value="loadLogs" />
    </div>

    <div v-if="store.hourlyLogs.length === 0" class="text-grey text-center q-py-xl">
      <q-icon name="smart_toy" size="64px" class="q-mb-md" color="grey-5" />
      <div>No hay logs para esta fecha</div>
    </div>

    <q-timeline v-else color="primary">
      <q-timeline-entry
        v-for="log in store.hourlyLogs"
        :key="log.id"
        :subtitle="`${log.utc_hour}:00 UTC — ${log.session || 'off'}`"
        :icon="logIcon(log)"
        :color="logColor(log)"
      >
        <template #title>
          <div class="row items-center q-gutter-sm">
            <q-badge v-if="log.trades_opened > 0" color="green" :label="`+${log.trades_opened} opened`" />
            <q-badge v-if="log.trades_closed > 0" color="blue" :label="`${log.trades_closed} closed`" />
            <q-badge v-if="log.trades_skipped > 0" color="grey" :label="`${log.trades_skipped} skipped`" />
            <span v-if="log.pnl_this_hour" :class="log.pnl_this_hour >= 0 ? 'text-green' : 'text-red'">
              {{ log.pnl_this_hour >= 0 ? '+' : '' }}${{ Number(log.pnl_this_hour).toFixed(2) }}
            </span>
          </div>
        </template>

        <div v-if="log.decision_summary" class="text-body2 text-grey-8 q-mt-sm">
          {{ log.decision_summary }}
        </div>
        <div v-if="log.market_context" class="text-caption text-grey q-mt-xs">
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

function logIcon(log: { trades_opened: number; trades_closed: number }) {
  if (log.trades_opened > 0) return 'trending_up'
  if (log.trades_closed > 0) return 'check_circle'
  return 'pause_circle'
}

function logColor(log: { trades_opened: number; pnl_this_hour: number | null }) {
  if (log.trades_opened > 0) return 'green'
  if (log.pnl_this_hour && log.pnl_this_hour < 0) return 'red'
  return 'grey'
}

async function loadLogs() {
  await store.loadLogs(dateFilter.value)
}

onMounted(loadLogs)
</script>
