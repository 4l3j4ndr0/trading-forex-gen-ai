<template>
  <q-page class="q-pa-lg">
    <div class="row items-center q-mb-lg">
      <div class="col">
        <h4 class="q-ma-none text-weight-bold">Dashboard</h4>
        <p class="text-grey-6 q-ma-none q-mt-xs">
          Bienvenido, {{ authStore.email }}
        </p>
      </div>
      <q-btn
        flat
        color="negative"
        label="Cerrar Sesión"
        icon="logout"
        @click="handleLogout"
      />
    </div>

    <div class="row q-col-gutter-md">
      <div class="col-12 col-md-4">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-caption text-grey-6">Señales Activas</div>
            <div class="text-h4 text-weight-bold text-primary">0</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-md-4">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-caption text-grey-6">Trades Abiertos</div>
            <div class="text-h4 text-weight-bold text-positive">0</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-md-4">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-caption text-grey-6">Win Rate</div>
            <div class="text-h4 text-weight-bold">—</div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <q-card flat bordered class="q-mt-lg">
      <q-card-section>
        <div class="text-h6 q-mb-sm">🚧 En construcción</div>
        <p class="text-grey-7">
          El dashboard de trading se implementará en las próximas fases.
          Próximamente: visualización de mercado, señales en tiempo real y panel de análisis.
        </p>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()

async function handleLogout() {
  await authStore.logOut()
  void router.replace('/login')
}
</script>
