<template>
  <div class="login-wrapper">
    <!-- Panel izquierdo: branding -->
    <div class="brand-panel">
      <div class="brand-content">
        <div class="brand-top">
          <div class="brand-icon-wrap">
            <q-icon name="rocket_launch" size="24px" color="white" />
          </div>
          <div>
            <div class="text-h5 text-white text-weight-bolder" style="letter-spacing: -0.5px">
              FX AutoTrader
            </div>
            <div class="brand-subtitle">AI-POWERED FOREX TRADING</div>
          </div>
        </div>

        <div class="brand-body">
          <div class="brand-headline">
            Trading automatizado<br />
            con <span class="text-primary">inteligencia</span><br />
            institucional
          </div>
          <p class="text-grey-5 text-body1 q-mt-lg" style="font-weight: 300; line-height: 1.8; max-width: 420px">
            Agente autónomo que analiza estructura de mercado, Order Blocks y liquidez
            institucional para ejecutar operaciones con gestión de riesgo integrada.
          </p>

          <div class="brand-features q-mt-xl">
            <div v-for="feat in features" :key="feat.text" class="brand-feature">
              <div class="brand-feature-icon">
                <q-icon :name="feat.icon" size="18px" color="primary" />
              </div>
              <span class="text-grey-3" style="font-weight: 400; font-size: 0.9rem">{{ feat.text }}</span>
            </div>
          </div>
        </div>

        <div class="brand-footer">
          <div class="brand-stats row q-gutter-lg q-mb-lg">
            <div>
              <div class="text-h5 text-white text-weight-bold number-display">24/5</div>
              <div class="text-caption text-grey-5">Monitoreo</div>
            </div>
            <div>
              <div class="text-h5 text-white text-weight-bold number-display">6+</div>
              <div class="text-caption text-grey-5">Pares Forex</div>
            </div>
            <div>
              <div class="text-h5 text-white text-weight-bold number-display">15min</div>
              <div class="text-caption text-grey-5">Ciclos de análisis</div>
            </div>
          </div>
          <p class="text-grey-7 text-caption q-ma-none">
            &copy; {{ year }} FX AutoTrader · No constituye asesoría financiera.
          </p>
        </div>
      </div>
    </div>

    <!-- Panel derecho: login -->
    <div class="form-panel">
      <div class="login-card">
        <div class="login-header">
          <div class="login-logo q-mb-md">
            <div class="login-logo-icon">
              <q-icon name="rocket_launch" size="20px" color="white" />
            </div>
          </div>
          <h5 class="q-ma-none text-weight-bold text-white">Iniciar Sesión</h5>
          <p class="text-grey-5 text-caption q-mt-xs">
            Accede a tu panel de trading automatizado
          </p>
        </div>

        <authenticator>
          <template #default="{ user }">
            <div class="text-center q-pa-lg" v-if="user">
              <q-spinner-dots size="40px" color="primary" />
              <p class="text-grey-5 q-mt-sm">Ingresando al dashboard...</p>
            </div>
          </template>
        </authenticator>

        <div class="login-footer">
          <q-separator dark class="q-my-lg" />
          <div class="text-caption text-grey-6 text-center" style="line-height: 1.6">
            <q-icon name="shield" size="14px" color="grey-6" class="q-mr-xs" />
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
  { text: 'Smart Money Concepts (OB, FVG, Liquidity)', icon: 'psychology' },
  { text: 'Multi-timeframe: D1 → H4 → H1 → M15', icon: 'timeline' },
  { text: 'Recovery Zone (Hedging) automático', icon: 'swap_vert' },
  { text: 'Gestión de riesgo 1% por operación', icon: 'shield' },
  { text: 'Reconciliación automática SL/TP', icon: 'sync' },
]

watch(
  () => auth.authStatus,
  async (status) => {
    if (status === 'authenticated') {
      await authStore.currentSession()
      void router.replace('/dashboard')
    }
  }
)

onMounted(() => {
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
  width: 55%;
  display: flex;
  background: linear-gradient(160deg, #070a0f 0%, #0d1117 40%, #0B1929 100%);
  position: relative;
  overflow: hidden;
}

.brand-panel::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -20%;
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(41, 98, 255, 0.08) 0%, transparent 70%);
  border-radius: 50%;
}

.brand-panel::after {
  content: '';
  position: absolute;
  bottom: -30%;
  left: -10%;
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(41, 98, 255, 0.05) 0%, transparent 70%);
  border-radius: 50%;
}

.brand-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  padding: 48px;
  width: 100%;
}

.brand-top {
  display: flex;
  align-items: center;
  gap: 14px;
}

.brand-icon-wrap {
  width: 42px;
  height: 42px;
  background: #2962FF;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 16px rgba(41, 98, 255, 0.3);
}

.brand-subtitle {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 2.5px;
  margin-top: 3px;
  color: #6B8AFF;
  text-transform: uppercase;
}

.brand-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.brand-headline {
  font-size: 2.6rem;
  font-weight: 900;
  line-height: 1.15;
  letter-spacing: -1px;
  color: white;
}

.brand-features {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.brand-feature {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-feature-icon {
  background: rgba(41, 98, 255, 0.1);
  border: 1px solid rgba(41, 98, 255, 0.2);
  border-radius: 8px;
  padding: 7px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.brand-footer {
  margin-top: auto;
}

.brand-stats {
  border-top: 1px solid #222834;
  padding-top: 24px;
}

/* ── Panel derecho ── */
.form-panel {
  width: 45%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0B0E14;
  padding: 32px;
}

.login-card {
  background: #151A22;
  border-radius: 16px;
  padding: 40px 36px;
  width: 100%;
  max-width: 440px;
  border: 1px solid #222834;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.login-header {
  text-align: center;
  margin-bottom: 28px;
}

.login-logo-icon {
  width: 44px;
  height: 44px;
  background: #2962FF;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto;
  box-shadow: 0 4px 20px rgba(41, 98, 255, 0.25);
}

.login-footer {
  margin-top: 16px;
}

.number-display {
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.5px;
}

/* ── Amplify overrides (dark theme) ── */
:deep([data-amplify-authenticator]) {
  --amplify-components-authenticator-router-box-shadow: none;
  --amplify-components-authenticator-router-border-width: 0;
  --amplify-components-authenticator-form-padding: 0;
  --amplify-colors-brand-primary-10: rgba(41, 98, 255, 0.1);
  --amplify-colors-brand-primary-80: #2962FF;
  --amplify-colors-brand-primary-90: #1E50E0;
  --amplify-colors-brand-primary-100: #1540C0;
  --amplify-colors-background-primary: #151A22;
  --amplify-colors-background-secondary: #1C2230;
  --amplify-colors-font-primary: #E0E0E0;
  --amplify-colors-font-secondary: #8B949E;
  --amplify-colors-border-primary: #222834;
  --amplify-colors-border-secondary: #2D3545;
  --amplify-colors-border-focus: #2962FF;
  --amplify-components-fieldcontrol-border-color: #222834;
  --amplify-components-fieldcontrol-color: #E0E0E0;
  --amplify-components-tabs-item-color: #8B949E;
  --amplify-components-tabs-item-active-color: #2962FF;
  --amplify-components-tabs-item-active-border-color: #2962FF;
  --amplify-components-button-primary-background-color: #2962FF;
  --amplify-components-button-primary-hover-background-color: #1E50E0;
  --amplify-components-button-link-color: #6B8AFF;
  width: 100%;
  max-width: 100%;
}

:deep([data-amplify-router]) {
  box-shadow: none;
  border: none;
  padding: 0;
  max-width: 100%;
  background: transparent;
}

:deep([data-amplify-form]) {
  padding: 0;
}

:deep([data-amplify-authenticator] [data-amplify-container]) {
  width: 100%;
  max-width: 100%;
}

:deep(.amplify-tabs) {
  margin: 0 0 16px 0;
}

:deep(.amplify-input) {
  background-color: #1C2230 !important;
  border-color: #222834 !important;
  color: #E0E0E0 !important;
  border-radius: 8px !important;
}

:deep(.amplify-input:focus) {
  border-color: #2962FF !important;
  box-shadow: 0 0 0 2px rgba(41, 98, 255, 0.2) !important;
}

:deep(.amplify-label) {
  color: #8B949E !important;
}

:deep(.amplify-button--primary) {
  border-radius: 8px !important;
  font-weight: 600 !important;
  padding: 12px !important;
}

:deep(.amplify-button--link) {
  color: #6B8AFF !important;
}

:deep(.amplify-heading) {
  display: none;
}

/* ── Responsive ── */
@media (max-width: 1024px) {
  .brand-panel {
    display: none;
  }
  .form-panel {
    width: 100%;
  }
}
</style>
