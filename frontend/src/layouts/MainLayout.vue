<template>
  <q-layout view="lHh Lpr lFf">
    <q-header elevated class="bg-dark">
      <q-toolbar>
        <q-btn flat dense round icon="menu" aria-label="Menu" @click="toggleLeftDrawer" />

        <q-toolbar-title class="text-weight-bold">
          <q-icon name="show_chart" class="q-mr-sm" />
          Forex Trading AI
        </q-toolbar-title>

        <q-chip
          v-if="authStore.isAuthenticated"
          dense
          color="grey-9"
          text-color="white"
          icon="person"
        >
          {{ authStore.email }}
        </q-chip>
      </q-toolbar>
    </q-header>

    <q-drawer v-model="leftDrawerOpen" show-if-above bordered class="bg-grey-1">
      <q-list>
        <q-item-label header class="text-grey-7 text-weight-medium">
          Navegación
        </q-item-label>

        <q-item clickable to="/dashboard" active-class="text-primary">
          <q-item-section avatar>
            <q-icon name="dashboard" />
          </q-item-section>
          <q-item-section>Dashboard</q-item-section>
        </q-item>

        <q-separator class="q-my-sm" />

        <q-item-label header class="text-grey-7 text-weight-medium">
          Próximamente
        </q-item-label>

        <q-item disable>
          <q-item-section avatar>
            <q-icon name="candlestick_chart" color="grey-5" />
          </q-item-section>
          <q-item-section>Mercado</q-item-section>
        </q-item>

        <q-item clickable to="/signals" active-class="text-primary">
          <q-item-section avatar>
            <q-icon name="gps_fixed" />
          </q-item-section>
          <q-item-section>Señales</q-item-section>
        </q-item>

        <q-item disable>
          <q-item-section avatar>
            <q-icon name="swap_vert" color="grey-5" />
          </q-item-section>
          <q-item-section>Trades</q-item-section>
        </q-item>

        <q-item disable>
          <q-item-section avatar>
            <q-icon name="analytics" color="grey-5" />
          </q-item-section>
          <q-item-section>Rendimiento</q-item-section>
        </q-item>
      </q-list>
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const leftDrawerOpen = ref(false)

function toggleLeftDrawer() {
  leftDrawerOpen.value = !leftDrawerOpen.value
}
</script>
