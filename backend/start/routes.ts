/*
|--------------------------------------------------------------------------
| Routes file
|--------------------------------------------------------------------------
|
| The routes file is used for defining the HTTP routes.
|
*/

import router from '@adonisjs/core/services/router'
import { middleware } from '#start/kernel'

const MeController = () => import('#controllers/me_controller')

router.get('/', () => {
  return { status: 'ok', app: 'forex-trading-ai', version: '0.1.0' }
})

router.get('/api/v1/health', () => ({
  status: 'healthy',
  timestamp: new Date().toISOString(),
}))

// Protected routes
router.get('/api/v1/me', [MeController, 'show']).use(middleware.cognito())
router.put('/api/v1/me/settings', [MeController, 'updateSettings']).use(middleware.cognito())
