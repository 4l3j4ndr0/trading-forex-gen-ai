/*
|--------------------------------------------------------------------------
| Routes file
|--------------------------------------------------------------------------
*/

import router from '@adonisjs/core/services/router'
import { middleware } from '#start/kernel'

const MeController = () => import('#controllers/me_controller')
const BrokerController = () => import('#controllers/broker_controller')
const TradingSettingsController = () => import('#controllers/trading_settings_controller')
const TradesController = () => import('#controllers/trades_controller')
const DailyController = () => import('#controllers/daily_controller')
const LogsController = () => import('#controllers/logs_controller')
const SystemController = () => import('#controllers/system_controller')

// Health
router.get('/', () => {
  return { status: 'ok', app: 'forex-trading-ai', version: '2.0.0' }
})
router.get('/api/v1/health', () => ({
  status: 'healthy',
  timestamp: new Date().toISOString(),
}))

// ─── Auth (Cognito) ────────────────────────────────────────
router.get('/api/v1/me', [MeController, 'show']).use(middleware.cognito())

// ─── Broker Config ─────────────────────────────────────────
router
  .group(() => {
    router.get('/', [BrokerController, 'show'])
    router.post('/', [BrokerController, 'upsert'])
    router.post('/test', [BrokerController, 'testConnection'])
    router.delete('/', [BrokerController, 'destroy'])
  })
  .prefix('/api/v1/broker')
  .use(middleware.cognito())

// ─── Trading Settings ──────────────────────────────────────
router
  .group(() => {
    router.get('/', [TradingSettingsController, 'show'])
    router.put('/', [TradingSettingsController, 'update'])
    router.post('/reset', [TradingSettingsController, 'reset'])
  })
  .prefix('/api/v1/settings/trading')
  .use(middleware.cognito())

// ─── Trades ────────────────────────────────────────────────
router
  .group(() => {
    router.get('/', [TradesController, 'index'])
    router.get('/open', [TradesController, 'open'])
    router.get('/stats', [TradesController, 'stats'])
    router.get('/:id', [TradesController, 'show'])
  })
  .prefix('/api/v1/trades')
  .use(middleware.cognito())

// ─── Daily Summaries ───────────────────────────────────────
router
  .group(() => {
    router.get('/', [DailyController, 'index'])
    router.get('/today', [DailyController, 'today'])
    router.get('/:date', [DailyController, 'show'])
  })
  .prefix('/api/v1/daily')
  .use(middleware.cognito())

// ─── Hourly Logs ───────────────────────────────────────────
router
  .group(() => {
    router.get('/', [LogsController, 'index'])
    router.get('/:id', [LogsController, 'show'])
  })
  .prefix('/api/v1/logs/hourly')
  .use(middleware.cognito())

// ─── System ────────────────────────────────────────────────
router
  .group(() => {
    router.get('/health', [SystemController, 'health'])
    router.get('/status', [SystemController, 'status'])
    router.post('/kill-switch', [SystemController, 'killSwitch'])
  })
  .prefix('/api/v1/system')
  .use(middleware.cognito())
