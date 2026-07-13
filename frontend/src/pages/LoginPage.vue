<template>
  <div class="login-wrapper">
    <!-- Panel izquierdo: branding -->
    <div class="brand-panel">
      <div class="brand-top">
        <div class="brand-icon-wrap">
          <q-icon name="show_chart" size="28px" color="white" />
        </div>
        <div>
          <div class="text-h5 text-white text-weight-bold" style="letter-spacing: -0.3px">
            Forex Trading AI
          </div>
          <div class="brand-subtitle">
            ANÁLISIS TÉCNICO CON INTELIGENCIA ARTIFICIAL
          </div>
        </div>
      </div>

      <div class="brand-body">
        <div class="brand-headline text-white">
          Señales inteligentes<br />
          para el mercado <span class="text-cyan">Forex</span>
        </div>
        <p class="text-grey-5 text-body1 q-mt-md q-mb-lg" style="font-weight: 300; line-height: 1.7">
          Sistema de análisis multi-temporalidad con IA. Recibe recomendaciones
          de entrada con puntos de Take Profit y Stop Loss calculados por confluencia técnica.
        </p>

        <div v-for="feat in features" :key="feat.text" class="brand-feature">
          <div class="brand-feature-icon">
            <q-icon :name="feat.icon" size="20px" color="cyan" />
          </div>
          <span class="text-grey-3" style="font-weight: 400">{{ feat.text }}</span>
        </div>
      </div>

      <p class="text-grey-7 text-caption">
        &copy; {{ year }} Forex Trading AI · No constituye asesoría financiera.
      </p>
    </div>

    <!-- Panel derecho: login card -->
    <div class="form-panel">
      <div class="login-card">
        <div class="login-header">
          <q-icon name="show_chart" size="36px" color="primary" class="q-mb-sm" />
          <h5 class="q-ma-none text-weight-bold text-grey-9">
            Iniciar Sesión
          </h5>
          <p class="text-grey-6 text-caption q-mt-xs">
            Ingresa con tu cuenta para acceder al sistema
          </p>
        </div>

        <authenticator>
          <template #default="{ user }">
            <div class="text-center q-pa-lg" v-if="user">
              <q-spinner-dots size="40px" color="primary" />
              <p class="text-grey-6 q-mt-sm">Ingresando al dashboard...</p>
            </div>
          </template>
        </authenticator>

        <div class="login-footer">
          <q-separator class="q-my-md" />
          <div class="text-caption text-grey-5 text-center">
            <q-icon name="warning" size="14px" color="amber" class="q-mr-xs" />
            El trading de Forex conlleva riesgo de pérdida de capital.
            Todas las decisiones son responsabilidad del usuario.
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Authenticator, useAuthenticator } from '@aws-amplify/ui-vue'
import '@aws-amplify/ui-vue/styles.css'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { watch, onMounted } from 'vue'

const router = useRouter()
const authStore = useAuthStore()
const year = new Date().getFullYear()
const auth = useAuthenticator()

const features = [
  { text: 'Análisis multi-temporalidad (M5 → D1)', icon: 'timeline' },
  { text: 'Señales con TP1, TP2, TP3 y Stop Loss', icon: 'gps_fixed' },
  { text: 'Gestión de riesgo automática (1-2% por trade)', icon: 'shield' },
  { text: 'Alertas en tiempo real por confluencia técnica', icon: 'notifications_active' },
]

watch(() => auth.authStatus, async (status) => {
  if (status === 'authenticated') {
    await authStore.currentSession()
    void router.replace('/dashboard')
  }
})

onMounted(async () => {
  if (authStore.isAuthenticated) {
    void router.replace('/dashboard')
  }
})
</script>

<style scoped>
.login-wrapper {
  min-height: 100vh;
  display: flex;
}

/* ── Panel izquierdo ── */
.brand-panel {
  width: 50%;
  display: flex;
  flex-direction: column;
  padding: 48px;
  background: linear-gradient(160deg, #0f172a 0%, #1e293b 60%, #0c4a6e 100%);
}
.brand-top {
  display: flex;
  align-items: center;
  gap: 16px;
}
.brand-icon-wrap {
  width: 52px;
  height: 52px;
  background: linear-gradient(135deg, #0ea5e9, #0284c7);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 16px rgba(14, 165, 233, 0.3);
}
.brand-subtitle {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 2.5px;
  margin-top: 4px;
  color: #67e8f9;
  text-transform: uppercase;
}
.brand-body {
  flex: 1;
  margin-top: 48px;
}
.brand-headline {
  font-size: 2.4rem;
  font-weight: 900;
  line-height: 1.15;
  letter-spacing: -0.5px;
}
.brand-feature {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 14px;
}
.brand-feature-icon {
  background: rgba(14, 165, 233, 0.12);
  border: 1px solid rgba(14, 165, 233, 0.25);
  border-radius: 8px;
  padding: 8px;
  flex-shrink: 0;
}

/* ── Panel derecho ── */
.form-panel {
  width: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8fafc;
  padding: 24px;
}
.login-card {
  background: white;
  border-radius: 16px;
  padding: 48px 40px;
  width: 100%;
  max-width: 440px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.08);
  border: 1px solid #e2e8f0;
}
.login-header {
  text-align: center;
  margin-bottom: 28px;
}
.login-footer {
  margin-top: 16px;
}

/* ── Amplify overrides ── */
:deep([data-amplify-authenticator]) {
  --amplify-components-authenticator-router-box-shadow: none;
  --amplify-components-authenticator-router-border-width: 0;
  --amplify-components-authenticator-form-padding: 0;
  --amplify-colors-brand-primary-10: #f0f9ff;
  --amplify-colors-brand-primary-80: #0ea5e9;
  --amplify-colors-brand-primary-90: #0284c7;
  --amplify-colors-brand-primary-100: #0369a1;
  width: 100%;
}
:deep([data-amplify-router]) {
  box-shadow: none;
  border: none;
  padding: 0;
}
:deep([data-amplify-form]) {
  padding: 0;
}

/* ── Responsive ── */
@media (max-width: 900px) {
  .brand-panel {
    display: none;
  }
  .form-panel {
    width: 100%;
  }
}
</style>
