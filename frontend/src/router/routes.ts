import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    component: () => import('@/layouts/AuthLayout.vue'),
    children: [
      { path: '', component: () => import('@/pages/LoginPage.vue') },
    ],
    meta: { guest: true },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', component: () => import('@/pages/DashboardPage.vue') },
      { path: 'trades', component: () => import('@/pages/TradesPage.vue') },
      { path: 'logs', component: () => import('@/pages/LogsPage.vue') },
      { path: 'settings', component: () => import('@/pages/SettingsPage.vue') },
      // SP500
      { path: 'sp500', component: () => import('@/pages/sp500/SP500DashboardPage.vue') },
      { path: 'sp500/trades', component: () => import('@/pages/sp500/SP500TradesPage.vue') },
      { path: 'sp500/logs', component: () => import('@/pages/sp500/SP500LogsPage.vue') },
      { path: 'sp500/settings', component: () => import('@/pages/sp500/SP500SettingsPage.vue') },
    ],
  },
  {
    path: '/:catchAll(.*)*',
    component: () => import('@/pages/ErrorNotFound.vue'),
  },
]

export default routes
