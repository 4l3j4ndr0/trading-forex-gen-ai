<template>
  <q-layout view="lHh Lpr lFf">
    <!-- HEADER -->
    <q-header class="text-white" style="box-shadow: none">
      <q-toolbar class="q-px-lg q-py-xs">
        <q-btn flat dense round icon="menu" aria-label="Menu" @click="toggleLeftDrawer" />

        <q-space />

        <!-- Status Badges -->
        <div class="row items-center q-gutter-sm">
          <q-chip
            v-if="tradingStore.accountType === 'demo'"
            outline
            color="warning"
            text-color="warning"
            size="sm"
            class="text-weight-bold"
          >
            <q-icon name="science" size="xs" class="q-mr-xs" />
            DEMO
          </q-chip>
          <q-chip
            v-else-if="tradingStore.accountType === 'live'"
            outline
            color="positive"
            text-color="positive"
            size="sm"
            class="text-weight-bold"
          >
            <q-icon name="account_balance" size="xs" class="q-mr-xs" />
            LIVE
          </q-chip>

          <q-chip size="sm" class="premium-card" text-color="white">
            <div :class="['pulse-dot q-mr-sm', { 'pulse-dot--warning': tradingStore.killSwitch }]"></div>
            <span class="text-weight-bold">{{ systemStatus }}</span>
          </q-chip>

          <q-separator vertical dark class="q-mx-xs" />

          <q-btn flat no-caps class="q-pl-sm" @click="logout">
            <q-avatar size="32px" color="primary" text-color="white">
              {{ userInitial }}
            </q-avatar>
            <q-icon name="logout" size="xs" color="grey-5" class="q-ml-sm" />
            <q-tooltip>Cerrar sesión</q-tooltip>
          </q-btn>
        </div>
      </q-toolbar>
    </q-header>

    <!-- SIDEBAR -->
    <q-drawer v-model="leftDrawerOpen" show-if-above :width="250">
      <!-- Logo -->
      <div class="q-pa-lg flex items-center q-gutter-md border-bottom" style="height: 80px">
        <img src="/icons/favicon-128x128.png" style="width: 34px; height: 34px; border-radius: 8px" />
        <div class="text-h6 text-weight-bolder text-white" style="letter-spacing: -0.5px">
          AutoTrader AI
        </div>
      </div>

      <!-- Navigation -->
      <q-scroll-area style="height: calc(100% - 80px)">
        <q-list padding class="q-px-sm text-grey-5">
          <q-item-label header class="label-mini q-pt-md">Trading</q-item-label>

          <q-item
            v-for="item in navItems"
            :key="item.path"
            clickable
            v-ripple
            :to="item.path"
            class="nav-item"
            active-class="nav-item--active"
          >
            <q-item-section avatar style="min-width: 40px">
              <q-icon :name="item.icon" />
            </q-item-section>
            <q-item-section class="text-weight-medium">{{ item.label }}</q-item-section>
            <q-item-section v-if="item.badge" side>
              <q-badge color="warning" text-color="dark" rounded>{{ item.badge }}</q-badge>
            </q-item-section>
          </q-item>

          <q-item-label header class="label-mini q-mt-lg">SP500</q-item-label>

          <q-item
            v-for="item in sp500NavItems"
            :key="item.path"
            clickable
            v-ripple
            :to="item.path"
            class="nav-item"
            active-class="nav-item--active"
          >
            <q-item-section avatar style="min-width: 40px">
              <q-icon :name="item.icon" />
            </q-item-section>
            <q-item-section class="text-weight-medium">{{ item.label }}</q-item-section>
            <q-item-section v-if="item.badge" side>
              <q-badge color="warning" text-color="dark" rounded>{{ item.badge }}</q-badge>
            </q-item-section>
          </q-item>

          <q-item-label header class="label-mini q-mt-lg">Cuenta</q-item-label>

          <!-- Balance info in sidebar -->
          <div class="q-px-md q-py-md">
            <div class="label-mini q-mb-xs">Balance</div>
            <div class="text-white text-h6 text-weight-bold number-display">
              ${{ tradingStore.balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
            </div>
            <div
              class="text-caption q-mt-xs number-display"
              :class="tradingStore.dailyPnl >= 0 ? 'text-positive' : 'text-negative'"
            >
              {{ tradingStore.dailyPnl >= 0 ? '+' : '' }}${{ tradingStore.dailyPnl.toFixed(2) }} hoy
            </div>
          </div>
        </q-list>
      </q-scroll-area>
    </q-drawer>

    <!-- CONTENT -->
    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTradingStore } from '@/stores/trading'
import { Dark } from 'quasar'

const authStore = useAuthStore()
const tradingStore = useTradingStore()
const router = useRouter()
const leftDrawerOpen = ref(false)

const systemStatus = computed(() => tradingStore.killSwitch ? 'PAUSED' : 'ACTIVE')
const userInitial = computed(() => authStore.initials?.[0] || 'U')

const navItems = computed(() => [
  { path: '/dashboard', icon: 'space_dashboard', label: 'Dashboard', badge: null },
  {
    path: '/trades',
    icon: 'candlestick_chart',
    label: 'Trades',
    badge: tradingStore.openPositions > 0 ? tradingStore.openPositions : null,
  },
  { path: '/logs', icon: 'terminal', label: 'Agent Logs', badge: null },
  { path: '/settings', icon: 'tune', label: 'Configuracion', badge: null },
])

const sp500NavItems = computed(() => [
  { path: '/sp500', icon: 'show_chart', label: 'Dashboard', badge: null },
  { path: '/sp500/trades', icon: 'receipt_long', label: 'Trades', badge: null },
  { path: '/sp500/logs', icon: 'terminal', label: 'Agent Logs', badge: null },
  { path: '/sp500/settings', icon: 'tune', label: 'Configuracion', badge: null },
])

function toggleLeftDrawer() {
  leftDrawerOpen.value = !leftDrawerOpen.value
}

async function logout() {
  await authStore.logOut()
  await router.push('/login')
}

async function loadGlobalData() {
  if (authStore.isAuthenticated) {
    await tradingStore.loadDashboard()
  }
}

onMounted(() => {
  Dark.set(true)
  void loadGlobalData()
})

watch(
  () => authStore.profileLoaded,
  (loaded) => {
    if (loaded) void loadGlobalData()
  }
)
</script>
