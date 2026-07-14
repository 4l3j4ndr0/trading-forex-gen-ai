<template>
  <q-layout view="lHh Lpr lFf">
    <q-header elevated class="bg-dark">
      <q-toolbar>
        <q-btn flat dense round icon="menu" aria-label="Menu" @click="toggleLeftDrawer" />

        <q-toolbar-title class="text-weight-bold">
          <q-icon name="currency_exchange" class="q-mr-sm" size="sm" />
          FX AutoTrader
        </q-toolbar-title>

        <q-chip dense color="green-9" text-color="white" icon="circle" class="q-mr-sm">
          {{ systemStatus }}
        </q-chip>

        <q-btn flat round icon="logout" @click="logout" />
      </q-toolbar>
    </q-header>

    <q-drawer v-model="leftDrawerOpen" show-if-above bordered class="bg-grey-10" :width="240">
      <q-list dark>
        <q-item-label header class="text-grey-5 text-caption q-mt-md">
          TRADING
        </q-item-label>

        <q-item v-for="item in navItems" :key="item.path" clickable :to="item.path"
          active-class="bg-grey-9 text-white" class="text-grey-3">
          <q-item-section avatar>
            <q-icon :name="item.icon" />
          </q-item-section>
          <q-item-section>{{ item.label }}</q-item-section>
          <q-item-section side v-if="item.badge">
            <q-badge color="orange" :label="item.badge" />
          </q-item-section>
        </q-item>

        <q-separator dark class="q-my-md" />

        <q-item-label header class="text-grey-5 text-caption">
          CUENTA
        </q-item-label>

        <div class="q-px-md q-py-sm">
          <div class="text-grey-5 text-caption">Balance</div>
          <div class="text-white text-h6">${{ balance.toFixed(2) }}</div>
          <div :class="dailyPnl >= 0 ? 'text-green' : 'text-red'" class="text-caption">
            {{ dailyPnl >= 0 ? '+' : '' }}${{ dailyPnl.toFixed(2) }} hoy
          </div>
        </div>
      </q-list>
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTradingStore } from '@/stores/trading'

const authStore = useAuthStore()
const tradingStore = useTradingStore()
const router = useRouter()
const leftDrawerOpen = ref(false)

const balance = computed(() => tradingStore.balance)
const dailyPnl = computed(() => tradingStore.dailyPnl)
const systemStatus = computed(() => tradingStore.killSwitch ? 'PAUSED' : 'ACTIVE')

const navItems = computed(() => [
  { path: '/dashboard', icon: 'dashboard', label: 'Dashboard', badge: null },
  { path: '/trades', icon: 'swap_vert', label: 'Trades', badge: tradingStore.openPositions > 0 ? tradingStore.openPositions : null },
  { path: '/logs', icon: 'history', label: 'Agent Logs', badge: null },
  { path: '/settings', icon: 'tune', label: 'Configuración', badge: null },
])

function toggleLeftDrawer() {
  leftDrawerOpen.value = !leftDrawerOpen.value
}

async function logout() {
  await authStore.logOut()
  await router.push('/login')
}
</script>
