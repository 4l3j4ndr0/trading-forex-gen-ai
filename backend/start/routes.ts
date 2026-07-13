/*
|--------------------------------------------------------------------------
| Routes file
|--------------------------------------------------------------------------
|
| The routes file is used for defining the HTTP routes.
|
*/

import router from '@adonisjs/core/services/router'

router.get('/', () => {
  return { status: 'ok', app: 'forex-trading-ai', version: '0.1.0' }
})

router
  .group(() => {
    router.get('health', () => ({ status: 'healthy', timestamp: new Date().toISOString() }))
  })
  .prefix('/api/v1')
