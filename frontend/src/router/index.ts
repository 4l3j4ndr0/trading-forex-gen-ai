import { defineRouter } from '#q-app'
import {
  createMemoryHistory,
  createRouter,
  createWebHashHistory,
  createWebHistory,
} from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import routes from './routes'

export default defineRouter(() => {
  const createHistory = import.meta.env.QUASAR_SERVER
    ? createMemoryHistory
    : import.meta.env.QUASAR_VUE_ROUTER_MODE === 'history'
      ? createWebHistory
      : createWebHashHistory

  const Router = createRouter({
    scrollBehavior: () => ({ left: 0, top: 0 }),
    routes,
    history: createHistory(import.meta.env.QUASAR_VUE_ROUTER_BASE),
  })

  Router.beforeEach(async (to) => {
    const auth = useAuthStore()

    if (to.meta.requiresAuth) {
      if (!auth.isAuthenticated) {
        try {
          await auth.currentSession()
        } catch {
          return '/login'
        }
        if (!auth.isAuthenticated) return '/login'
      }
    }

    if (to.meta.guest && auth.isAuthenticated) {
      return '/dashboard'
    }
  })

  return Router
})
